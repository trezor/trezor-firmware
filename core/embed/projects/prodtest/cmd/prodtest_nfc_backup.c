/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifdef USE_NFC

#include <trezor_rtl.h>

#include <io/nfc.h>
#include <noise_xxpsk3.h>
#include <rtl/cli.h>
#include <rtl/printf.h>
#include <rust_ui_prodtest.h>
#include <sys/rng.h>
#include <sys/sysevent.h>
#include <sys/systick.h>

#include "memzero.h"
#include "prodtest.h"
#include "prodtest_error_codes.h"

#define NFC_BACKUP_MAX_PIN_TRIALS 10
#define NFC_BACKUP_LOG_RECORD_SIZE 32
#define NFC_BACKUP_SEED_METADATA_SIZE 256
#define NFC_BACKUP_SEED_SIZE 256
#define NFC_BACKUP_VERBOSE_SECRETS false
#define NFC_BACKUP_MAX_PIN_LEN 32

static noise_xxpsk3_initiator_t intr = {0};
static bool handshake_completed = false;

typedef struct {
  uint8_t version;                // 0 = v1, 1 = v2, 2 = v3
  uint32_t serial_number;         // Certificate serial
  char issuer_c[8];               // Issuer Country
  char issuer_o[64];              // Issuer Organization
  char issuer_cn[64];             // Issuer Common Name
  char not_before[16];            // UTCTime string (e.g. "260615154143Z")
  char not_after[16];             // UTCTime string
  char subject_cn[64];            // Subject Common Name
  char subject_serial[32];        // Subject serialNumber attribute
  char subject_dn_qualifier[32];  // Subject dnQualifier attribute
  uint8_t public_key[32];         // Ed25519 Public Key (32 bytes)
  bool is_ca;                     // BasicConstraints CA flag
  uint16_t key_usage;             // KeyUsage bitmask
  uint8_t auth_key_id[20];        // Authority Key Identifier
  uint8_t signature[64];          // Ed25519 Signature (64 bytes)
} nfc_backup_certificate_t;

typedef ts_t (*on_tap_callback_t)(cli_t *cli);

static const char *nfc_backup_or_na(const char *text) {
  if (text == NULL || text[0] == '\0') {
    return "N/A";
  }
  return text;
}

static void nfc_backup_format_utc_time(const char *in, char *out,
                                       size_t out_size) {
  if (in == NULL || out == NULL || out_size == 0) {
    return;
  }

  // ASN.1 UTCTime in this path is expected as YYMMDDhhmmssZ.
  if (strlen(in) == 13 && in[12] == 'Z') {
    snprintf_(out, out_size, "%c%c-%c%c-%c%c %c%c:%c%c:%c%c UTC", in[0], in[1],
              in[2], in[3], in[4], in[5], in[6], in[7], in[8], in[9], in[10],
              in[11]);
    return;
  }

  snprintf_(out, out_size, "%s", in);
}

static void nfc_backup_trace_hex_preview(cli_t *cli, const char *label,
                                         const uint8_t *data, size_t len) {
  char full_hex[2 * 64 + 1] = {0};
  char head_hex[17] = {0};
  char tail_hex[17] = {0};

  if (data == NULL || len == 0) {
    cli_trace(cli, "  %s: N/A", label);
    return;
  }

  if (NFC_BACKUP_VERBOSE_SECRETS || len <= 16) {
    if (len > 64) {
      cstr_encode_hex(full_hex, sizeof(full_hex), data, 64);
      cli_trace(cli, "  %s: %s... (%u bytes)", label, full_hex, (unsigned)len);
    } else {
      cstr_encode_hex(full_hex, sizeof(full_hex), data, len);
      cli_trace(cli, "  %s: %s", label, full_hex);
    }
    return;
  }

  cstr_encode_hex(head_hex, sizeof(head_hex), data, 8);
  cstr_encode_hex(tail_hex, sizeof(tail_hex), &data[len - 8], 8);
  cli_trace(cli, "  %s: %s...%s (%u bytes)", label, head_hex, tail_hex,
            (unsigned)len);
}

static void nfc_backup_format_key_usage(uint16_t key_usage, char *out,
                                        size_t out_size) {
  bool first = true;
  size_t used = 0;

  if (out == NULL || out_size == 0) {
    return;
  }

  out[0] = '\0';

  struct {
    uint16_t bit;
    const char *label;
  } key_usage_map[] = {
      {0x80, "digitalSignature"}, {0x40, "contentCommitment"},
      {0x20, "keyEncipherment"},  {0x10, "dataEncipherment"},
      {0x08, "keyAgreement"},     {0x04, "keyCertSign"},
      {0x02, "cRLSign"},          {0x01, "encipherOnly"},
  };

  for (size_t i = 0; i < sizeof(key_usage_map) / sizeof(key_usage_map[0]);
       i++) {
    if ((key_usage & key_usage_map[i].bit) == 0) {
      continue;
    }

    used += snprintf_(out + used, out_size - used, "%s%s", first ? "" : ", ",
                      key_usage_map[i].label);
    first = false;

    if (used >= out_size) {
      out[out_size - 1] = '\0';
      return;
    }
  }

  if (first) {
    snprintf_(out, out_size, "none");
  }
}

// Sends `cmd` (CLA/INS/P1/P2/Lc/Data) over NFC. Once the Noise XXpsk3
// handshake is complete, the whole APDU is encrypted before transmission and
// the response payload is decrypted, with SW1/SW2 (the last two bytes)
// always left in plaintext. Prior to the handshake, `cmd`/`rsp` pass through
// unmodified.
static ts_t nfc_backup_secure_transceive(const nfc_apdu_message_t *cmd,
                                         nfc_apdu_message_t *rsp) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(cmd != NULL);
  TSH_CHECK_ARG(rsp != NULL);

  if (!handshake_completed) {
    status = nfc_transceive(cmd, rsp);
    TSH_CHECK_OK(status);
    goto cleanup;
  }

  nfc_apdu_message_t enc_cmd = {0};
  size_t enc_cmd_len = 0;
  bool ok = noise_xxpsk3_send_message(&intr.transport_state, cmd->data,
                                      cmd->data_len, enc_cmd.data,
                                      sizeof(enc_cmd.data), &enc_cmd_len);
  TSH_CHECK(ok, TS_EINVAL);
  enc_cmd.data_len = (uint16_t)enc_cmd_len;

  nfc_apdu_message_t enc_rsp = {0};
  status = nfc_transceive(&enc_cmd, &enc_rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(enc_rsp.data_len >= 2U, TS_EINVAL);
  size_t enc_payload_len = enc_rsp.data_len - 2U;
  uint8_t sw1 = enc_rsp.data[enc_rsp.data_len - 2];
  uint8_t sw2 = enc_rsp.data[enc_rsp.data_len - 1];

  size_t dec_len = 0;
  if (enc_payload_len > 0) {
    ok = noise_xxpsk3_receive_message(&intr.transport_state, enc_rsp.data,
                                      enc_payload_len, rsp->data,
                                      sizeof(rsp->data) - 2U, &dec_len);
    TSH_CHECK(ok, TS_EINVAL);
  }

  rsp->data[dec_len] = sw1;
  rsp->data[dec_len + 1] = sw2;
  rsp->data_len = (uint16_t)(dec_len + 2U);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_transceive_logged(cli_t *cli, const char *api_name,
                                         uint8_t ins,
                                         const nfc_apdu_message_t *cmd,
                                         nfc_apdu_message_t *rsp) {
  ts_t status = TS_OK;

  cli_trace(cli, "APDU %s: TX INS=0x%02X (%u bytes)", api_name, ins,
            (unsigned)cmd->data_len);

  status = nfc_backup_secure_transceive(cmd, rsp);
  if (ts_error(status)) {
    cli_trace(cli, "APDU %s: transceive failed (%s/%d)", api_name,
              ts_string(status), ts_code(status));
    return status;
  }

  if (rsp->data_len >= 2) {
    uint8_t sw1 = rsp->data[rsp->data_len - 2];
    uint8_t sw2 = rsp->data[rsp->data_len - 1];
    cli_trace(cli, "APDU %s: RX SW=0x%02X%02X (%u bytes)", api_name, sw1, sw2,
              (unsigned)rsp->data_len);
  } else {
    cli_trace(cli, "APDU %s: RX malformed (%u bytes)", api_name,
              (unsigned)rsp->data_len);
  }

  return TS_OK;
}

static ts_t nfc_poll_start(cli_t *cli) {
  ts_t status;

  status = nfc_init();
  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_INIT, "NFC initialization failed");
    return status;
  }

  status = nfc_start_discovery();
  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_DISCOVERY,
              "NFC start discovery failed");
    return status;
  }

  // Clear leftover events
  nfc_event_t event_flag;
  sysevents_t awaited_events = {0};
  sysevents_t signalled_events = {0};

  nfc_get_event(&event_flag);
  awaited_events.read_ready = 1 << SYSHANDLE_NFC;
  sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

  return TS_OK;
}

static ts_t nfc_wait_for_tap(cli_t *cli, on_tap_callback_t callback) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(cli != NULL);
  TSH_CHECK_ARG(callback != NULL);

  cli_trace(cli, "STEP 1/3: Waiting for NFC backup card tap.");
  cli_trace(cli,
            "Instruction: place card flat on antenna and hold still. Press "
            "Ctrl+C to abort.");

  sysevents_t awaited_events = {0};
  sysevents_t signalled_events = {0};
  nfc_event_t event_flag;

  awaited_events.read_ready = 1 << SYSHANDLE_NFC;

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted by operator.");
      goto cleanup;
    }

    sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

    if ((signalled_events.read_ready & 1 << SYSHANDLE_NFC) == 0) {
      continue;
    }

    if (!nfc_get_event(&event_flag)) {
      continue;
    }

    if (event_flag == NFC_EVENT_CONNECTED) {
      cli_trace(cli, "STEP 2/3: NFC card detected.");

      nfc_dev_info_t dev_info;
      nfc_get_device_info(&dev_info);

      if (dev_info.type != NFC_DEV_TYPE_A) {
        cli_error(cli, PRODTEST_ERR_NFC_BACKUP_UNEXPECTED_CARD_TYPE,
                  "Unexpected card type (%d). Expected Type A NFC backup card.",
                  dev_info.type);
        TSH_CHECK(false, TS_EINVAL);
      }

      // Call ON-TAP callback function
      uint32_t tic = systick_ms();
      status = (callback)(cli);
      cli_trace(cli, "STEP 3/3: Command finished in %lu ms.",
                (unsigned long)(systick_ms() - tic));
      TSH_CHECK_OK(status);
      break;
    }
  }

cleanup:
  TSH_RETURN;
}

static void nfc_poll_stop(void) {
  nfc_stop_discovery();
  nfc_deinit();
}

static ts_t nfc_backup_tap(cli_t *cli, on_tap_callback_t callback) {
  ts_t status;

  status = nfc_poll_start(cli);
  if (ts_error(status)) {
    return status;
  }

  handshake_completed = false;

  status = nfc_wait_for_tap(cli, callback);
  memzero(&intr, sizeof(intr));

  nfc_poll_stop();
  return status;
}

#define REGISTER_NFC_BACKUP_CMD(handler_name, tap_fn, err_code, err_msg) \
  static void handler_name(cli_t *cli) {                                 \
    ts_t status = nfc_backup_tap(cli, tap_fn);                           \
    if (ts_error(status)) {                                              \
      cli_error(cli, err_code, err_msg);                                 \
    } else {                                                             \
      cli_ok(cli, "");                                                   \
    }                                                                    \
  }

// Helper to parse ASN.1 Tag-Length-Value (TLV) headers
static const uint8_t *asn1_parse_header(const uint8_t *p, const uint8_t *end,
                                        uint8_t *tag, size_t *len) {
  if (p >= end) return NULL;
  *tag = *p++;

  if (p >= end) return NULL;
  uint8_t len_byte = *p++;

  if ((len_byte & 0x80) == 0) {
    *len = len_byte;
  } else {
    size_t num_bytes = len_byte & 0x7F;
    if (num_bytes > sizeof(size_t) || p + num_bytes > end) return NULL;
    *len = 0;
    while (num_bytes--) {
      *len = (*len << 8) | *p++;
    }
  }

  if (p + *len > end) return NULL;
  return p;
}

// Parse X.501 Distinguished Name (Issuer / Subject RDNSequence)
static void parse_dn(const uint8_t *p, size_t len, char *cn, size_t cn_max,
                     char *c, size_t c_max, char *o, size_t o_max, char *serial,
                     size_t serial_max, char *dn_qual, size_t dn_qual_max) {
  const uint8_t *end = p + len;
  uint8_t tag;
  size_t set_len, seq_len, oid_len, str_len;

  while (p < end) {
    p = asn1_parse_header(p, end, &tag, &set_len);  // SET
    if (!p || tag != 0x31) break;

    const uint8_t *set_end = p + set_len;
    const uint8_t *sp = p;
    sp = asn1_parse_header(sp, set_end, &tag, &seq_len);  // SEQUENCE
    if (!sp || tag != 0x30) {
      p = set_end;
      continue;
    }

    const uint8_t *oid_ptr = asn1_parse_header(sp, set_end, &tag, &oid_len);
    if (!oid_ptr || tag != 0x06) {
      p = set_end;
      continue;
    }

    const uint8_t *val_ptr =
        asn1_parse_header(oid_ptr + oid_len, set_end, &tag, &str_len);
    if (!val_ptr) {
      p = set_end;
      continue;
    }

    // OID 2.5.4.3 (Common Name)
    if (oid_len == 3 && memcmp(oid_ptr, "\x55\x04\x03", 3) == 0 && cn) {
      snprintf_(cn, cn_max, "%.*s", (int)str_len, val_ptr);
    }
    // OID 2.5.4.6 (Country)
    else if (oid_len == 3 && memcmp(oid_ptr, "\x55\x04\x06", 3) == 0 && c) {
      snprintf_(c, c_max, "%.*s", (int)str_len, val_ptr);
    }
    // OID 2.5.4.10 (Organization)
    else if (oid_len == 3 && memcmp(oid_ptr, "\x55\x04\x0a", 3) == 0 && o) {
      snprintf_(o, o_max, "%.*s", (int)str_len, val_ptr);
    }
    // OID 2.5.4.5 (serialNumber)
    else if (oid_len == 3 && memcmp(oid_ptr, "\x55\x04\x05", 3) == 0 &&
             serial) {
      snprintf_(serial, serial_max, "%.*s", (int)str_len, val_ptr);
    }
    // OID 2.5.4.46 (dnQualifier)
    else if (oid_len == 3 && memcmp(oid_ptr, "\x55\x04\x2e", 3) == 0 &&
             dn_qual) {
      snprintf_(dn_qual, dn_qual_max, "%.*s", (int)str_len, val_ptr);
    }

    p = set_end;
  }
}

// Main parser function
int parse_x509_certificate(const uint8_t *buffer, size_t buffer_len,
                           nfc_backup_certificate_t *cert) {
  if (!buffer || !cert || buffer_len == 0) return -1;
  memset(cert, 0, sizeof(nfc_backup_certificate_t));

  const uint8_t *p = buffer;
  const uint8_t *end = buffer + buffer_len;
  uint8_t tag;
  size_t len;

  // 1. Root SEQUENCE
  p = asn1_parse_header(p, end, &tag, &len);
  if (!p || tag != 0x30) return -1;

  // 2. tbsCertificate (SEQUENCE)
  const uint8_t *tbs_ptr = asn1_parse_header(p, end, &tag, &len);
  if (!tbs_ptr || tag != 0x30) return -1;
  const uint8_t *tbs_end = tbs_ptr + len;
  p = tbs_ptr;

  // Version [0] EXPLICIT
  if (p < tbs_end && *p == 0xa0) {
    size_t outer_len = 0;
    const uint8_t *outer_ptr = asn1_parse_header(p, tbs_end, &tag, &outer_len);
    if (!outer_ptr || tag != 0xa0) return -1;

    const uint8_t *outer_end = outer_ptr + outer_len;
    size_t ver_len = 0;
    const uint8_t *ver_ptr =
        asn1_parse_header(outer_ptr, outer_end, &tag, &ver_len);
    if (ver_ptr && tag == 0x02 && ver_len == 1) {
      cert->version = *ver_ptr;
    }

    // Advance by full [0] EXPLICIT field length, not by inner INTEGER length.
    p = outer_end;
  }

  // Serial Number (INTEGER)
  p = asn1_parse_header(p, tbs_end, &tag, &len);
  if (p && tag == 0x02) {
    cert->serial_number = 0;
    for (size_t i = 0; i < len; i++) {
      cert->serial_number = (cert->serial_number << 8) | p[i];
    }
    p += len;
  }

  // Sig Alg Identifier inside TBS (SEQUENCE) -> skip
  p = asn1_parse_header(p, tbs_end, &tag, &len);
  if (p && tag == 0x30) p += len;

  // Issuer (SEQUENCE)
  p = asn1_parse_header(p, tbs_end, &tag, &len);
  if (p && tag == 0x30) {
    parse_dn(p, len, cert->issuer_cn, sizeof(cert->issuer_cn), cert->issuer_c,
             sizeof(cert->issuer_c), cert->issuer_o, sizeof(cert->issuer_o),
             NULL, 0, NULL, 0);
    p += len;
  }

  // Validity (SEQUENCE)
  p = asn1_parse_header(p, tbs_end, &tag, &len);
  if (p && tag == 0x30) {
    const uint8_t *val_end = p + len;
    const uint8_t *v = asn1_parse_header(p, val_end, &tag, &len);  // Not Before
    if (v && tag == 0x17) {
      snprintf_(cert->not_before, sizeof(cert->not_before), "%.*s", (int)len,
                v);
      v += len;
      v = asn1_parse_header(v, val_end, &tag, &len);  // Not After
      if (v && tag == 0x17) {
        snprintf_(cert->not_after, sizeof(cert->not_after), "%.*s", (int)len,
                  v);
      }
    }
    p = val_end;
  }

  // Subject (SEQUENCE)
  p = asn1_parse_header(p, tbs_end, &tag, &len);
  if (p && tag == 0x30) {
    parse_dn(p, len, cert->subject_cn, sizeof(cert->subject_cn), NULL, 0, NULL,
             0, cert->subject_serial, sizeof(cert->subject_serial),
             cert->subject_dn_qualifier, sizeof(cert->subject_dn_qualifier));
    p += len;
  }

  // SubjectPublicKeyInfo (SEQUENCE)
  p = asn1_parse_header(p, tbs_end, &tag, &len);
  if (p && tag == 0x30) {
    const uint8_t *spki_end = p + len;
    const uint8_t *sp =
        asn1_parse_header(p, spki_end, &tag, &len);  // AlgId Sequence
    if (sp && tag == 0x30) {
      sp += len;
      sp = asn1_parse_header(sp, spki_end, &tag, &len);  // BIT STRING
      if (sp && tag == 0x03 && len == 33) {  // 1 unused bit byte + 32 key bytes
        memcpy(cert->public_key, sp + 1, 32);
      }
    }
    p = spki_end;
  }

  // Extensions [3] EXPLICIT
  if (p < tbs_end && *p == 0xa3) {
    p = asn1_parse_header(p, tbs_end, &tag, &len);
    p = asn1_parse_header(p, tbs_end, &tag, &len);  // Extensions SEQUENCE
    const uint8_t *exts_end = p + len;

    while (p < exts_end) {
      p = asn1_parse_header(p, exts_end, &tag, &len);  // Extension SEQUENCE
      if (!p || tag != 0x30) break;

      const uint8_t *ext_end = p + len;
      const uint8_t *oid_ptr = asn1_parse_header(p, ext_end, &tag, &len);
      if (!oid_ptr || tag != 0x06) {
        p = ext_end;
        continue;
      }

      const uint8_t *curr = oid_ptr + len;

      // Skip BOOLEAN critical if present
      if (curr < ext_end && *curr == 0x01) {
        curr = asn1_parse_header(curr, ext_end, &tag, &len);
        curr += len;
      }

      // OCTET STRING wrapper
      curr = asn1_parse_header(curr, ext_end, &tag, &len);
      if (curr && tag == 0x04) {
        // Basic Constraints (OID 2.5.29.19 -> 55 1d 13)
        if (memcmp(oid_ptr, "\x55\x1d\x13", 3) == 0) {
          const uint8_t *bc = asn1_parse_header(curr, curr + len, &tag, &len);
          if (bc && tag == 0x30 && len > 0) {
            const uint8_t *b_val = asn1_parse_header(bc, bc + len, &tag, &len);
            if (b_val && tag == 0x01) cert->is_ca = (*b_val != 0);
          }
        }
        // Key Usage (OID 2.5.29.15 -> 55 1d 0f)
        else if (memcmp(oid_ptr, "\x55\x1d\x0f", 3) == 0) {
          const uint8_t *ku = asn1_parse_header(curr, curr + len, &tag, &len);
          if (ku && tag == 0x03 && len >= 2) {
            cert->key_usage = ku[1];  // Store key usage bitmask
          }
        }
        // Authority Key Identifier (OID 2.5.29.35 -> 55 1d 23)
        else if (memcmp(oid_ptr, "\x55\x1d\x23", 3) == 0) {
          const uint8_t *aki = asn1_parse_header(curr, curr + len, &tag, &len);
          if (aki && tag == 0x30) {
            const uint8_t *key_id =
                asn1_parse_header(aki, aki + len, &tag, &len);
            if (key_id && tag == 0x80 && len == 20) {
              memcpy(cert->auth_key_id, key_id, 20);
            }
          }
        }
      }
      p = ext_end;
    }
  }

  // Skip to top-level Signature Value BIT STRING
  p = tbs_end;
  p = asn1_parse_header(p, end, &tag, &len);  // Signature Algorithm
  if (p && tag == 0x30) p += len;

  p = asn1_parse_header(p, end, &tag, &len);  // Signature BIT STRING
  if (p && tag == 0x03 &&
      len == 65) {  // 1 byte padding flags + 64 bytes Ed25519 sig
    memcpy(cert->signature, p + 1, 64);
  }

  return 0;
}

static void print_certificate(cli_t *cli,
                              nfc_backup_certificate_t const *cert) {
  char not_before_text[32] = {0};
  char not_after_text[32] = {0};
  char key_usage_text[128] = {0};

  nfc_backup_format_utc_time(cert->not_before, not_before_text,
                             sizeof(not_before_text));
  nfc_backup_format_utc_time(cert->not_after, not_after_text,
                             sizeof(not_after_text));
  nfc_backup_format_key_usage(cert->key_usage, key_usage_text,
                              sizeof(key_usage_text));

  cli_trace(cli, "Certificate details:");
  cli_trace(cli, "  Version: v%u", (unsigned)(cert->version + 1));
  cli_trace(cli, "  Serial: 0x%08lX (%lu)", (unsigned long)cert->serial_number,
            (unsigned long)cert->serial_number);
  cli_trace(cli, "  Subject CN: %s", nfc_backup_or_na(cert->subject_cn));
  cli_trace(cli, "  Subject serial: %s",
            nfc_backup_or_na(cert->subject_serial));
  cli_trace(cli, "  Subject dnQualifier: %s",
            nfc_backup_or_na(cert->subject_dn_qualifier));
  cli_trace(cli, "  Issuer CN: %s", nfc_backup_or_na(cert->issuer_cn));
  cli_trace(cli, "  Issuer O: %s", nfc_backup_or_na(cert->issuer_o));
  cli_trace(cli, "  Issuer C: %s", nfc_backup_or_na(cert->issuer_c));
  cli_trace(cli, "  Valid from: %s", nfc_backup_or_na(not_before_text));
  cli_trace(cli, "  Valid to: %s", nfc_backup_or_na(not_after_text));
  cli_trace(cli, "  Basic constraints: CA=%s", cert->is_ca ? "true" : "false");
  cli_trace(cli, "  Key usage: 0x%02X (%s)", cert->key_usage, key_usage_text);
  nfc_backup_trace_hex_preview(cli, "Public key", cert->public_key,
                               sizeof(cert->public_key));
  nfc_backup_trace_hex_preview(cli, "Authority key id", cert->auth_key_id,
                               sizeof(cert->auth_key_id));
  nfc_backup_trace_hex_preview(cli, "Signature", cert->signature,
                               sizeof(cert->signature));
}

static ts_t nfc_backup_compose_apdu(uint8_t cla, uint8_t ins, uint8_t p1,
                                    uint8_t p2, const uint8_t *data,
                                    size_t data_len, nfc_apdu_message_t *apdu) {
  TSH_DECLARE;

  TSH_CHECK_ARG(apdu != NULL);
  TSH_CHECK_ARG(data != NULL || data_len == 0);

  apdu->data[0] = cla;
  apdu->data[1] = ins;
  apdu->data[2] = p1;
  apdu->data[3] = p2;

  if (data_len <= 0xFFU) {
    // Short APDU Lc encoding: [CLA INS P1 P2 Lc Data]
    TSH_CHECK_ARG((5U + data_len) <= sizeof(apdu->data));
    apdu->data[4] = (uint8_t)data_len;
    memcpy(&apdu->data[5], data, data_len);
    apdu->data_len = (uint16_t)(5U + data_len);
  } else {
    // Extended APDU Lc encoding: [CLA INS P1 P2 00 LcHi LcLo Data]
    TSH_CHECK_ARG(data_len <= 0xFFFFU);
    TSH_CHECK_ARG((7U + data_len) <= sizeof(apdu->data));
    apdu->data[4] = 0x00U;
    apdu->data[5] = (uint8_t)((data_len >> 8U) & 0xFFU);
    apdu->data[6] = (uint8_t)(data_len & 0xFFU);
    memcpy(&apdu->data[7], data, data_len);
    apdu->data_len = (uint16_t)(7U + data_len);
  }

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_noise(cli_t *cli, uint8_t (*psk)[32]) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(*psk != NULL);
  bool noise_status = false;

  // Test static keypair for Noise XXPSK3 handshake.
  uint8_t static_private_key[NOISE_XXPSK3_DHLEN] = {
      0x43, 0xa1, 0x7e, 0x8a, 0xad, 0x8b, 0xf5, 0xb0, 0x26, 0x12, 0xfe,
      0x6d, 0xeb, 0x77, 0xcd, 0xc0, 0x84, 0x59, 0xad, 0x05, 0xf4, 0xd6,
      0xb7, 0x32, 0xc5, 0xb4, 0xa2, 0xe1, 0xbf, 0xec, 0x99, 0x7b};

  uint8_t static_public_key[NOISE_XXPSK3_DHLEN] = {
      0x8a, 0xd7, 0x10, 0xc4, 0xcd, 0xa6, 0x35, 0xf7, 0x3f, 0x06, 0x04,
      0x99, 0x4f, 0x79, 0xbd, 0x19, 0xe9, 0xba, 0xfa, 0x10, 0x9c, 0xef,
      0xe4, 0x22, 0xdd, 0x60, 0x86, 0x63, 0xc2, 0xe1, 0xa4, 0x58};

  noise_status = noise_xxpsk3_initiator_init(&intr, *psk, static_private_key,
                                             static_public_key);
  TSH_CHECK(noise_status, TS_EINVAL);

  uint8_t request[256] = {0};
  size_t request_size = 0;

  noise_status = noise_xxpsk3_initiator_create_request1(
      &intr, NULL, 0, request, sizeof(request), &request_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};
  status = nfc_backup_compose_apdu(0x80, 0x01, 0x00, 0x00, request,
                                   request_size, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_secure_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len >= 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

  uint8_t card_public_key[NOISE_XXPSK3_DHLEN] = {0};

  uint8_t certificate[512] = {0};
  size_t certificate_size = 0;

  noise_status = noise_xxpsk3_initiator_handle_response1(
      &intr, rsp.data, rsp.data_len - 2, card_public_key, certificate,
      sizeof(certificate), &certificate_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  nfc_backup_certificate_t cert = {0};
  parse_x509_certificate(certificate, certificate_size, &cert);

  if (cli != NULL) {
    print_certificate(cli, &cert);
  }

  if (memcmp(cert.public_key, card_public_key, NOISE_XXPSK3_DHLEN) != 0) {
    if (cli != NULL) {
      cli_trace(cli, "Card public key does not match certificate public key.");
    }
    TSH_CHECK(false, TS_EINVAL);
  }

  noise_status = noise_xxpsk3_initiator_create_request2(
      &intr, NULL, 0, request, sizeof(request), &request_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  status = nfc_backup_compose_apdu(0x80, 0x01, 0x01, 0x00, request,
                                   request_size, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_secure_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len >= 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

  uint8_t plain_text[256] = {0};
  size_t plain_text_size = 0;
  noise_status = noise_xxpsk3_receive_message(
      &intr.transport_state, rsp.data, rsp.data_len - 2, plain_text,
      sizeof(plain_text), &plain_text_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  if (cli != NULL) {
    cli_trace(cli, "Card welcome message: %.*s", (int)plain_text_size,
              plain_text);
  }

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_handshake(cli_t *cli) {
  TSH_DECLARE;
  ts_t status = TS_OK;

  // Clear the initiator structure
  memzero(&intr, sizeof(intr));

  if (cli != NULL) {
    cli_trace(cli, "Handshake: start");
    cli_trace(cli, "Handshake step 1/4: selecting backup applet.");
  }
  nfc_apdu_message_t cmd = {.data = {0x00, 0xA4, 0x04, 0x00, 0x07, 0xA0, 0x00,
                                     0x00, 0x09, 0x59, 0x00, 0x01},
                            .data_len = 12};

  nfc_apdu_message_t resp = {0};

  status = nfc_backup_secure_transceive(&cmd, &resp);
  TSH_CHECK_OK(status);

  TSH_CHECK(resp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(resp.data[0] == 0x90U && resp.data[1] == 0x00U, TS_EINVAL);

  if (cli != NULL) {
    cli_trace(cli, "Handshake step 2/4: exchanging PSK.");
  }
  uint8_t pcd_psk[16] = {0};
  uint8_t picc_psk[16] = {0};
  uint16_t picc_psk_len = 0;

  rng_fill_buffer(pcd_psk, sizeof(pcd_psk));

  status = nfc_transceive_psk(pcd_psk, sizeof(pcd_psk), picc_psk,
                              sizeof(picc_psk), &picc_psk_len);

  if (ts_error(status) || picc_psk_len != sizeof(picc_psk)) {
    if (cli != NULL) {
      cli_error(cli, PRODTEST_ERR_NFC_BACKUP_PSK_EXCHANGE_FAILED,
                "NFC PSK exchange failed");
    }
  }
  TSH_CHECK_OK(status);

  // Combine both share into PSK
  uint8_t psk[32] = {0};
  memcpy(psk, pcd_psk, 16);
  memcpy(psk + 16, picc_psk, 16);

  nfc_backup_trace_hex_preview(cli, "Exchanged PSK", psk, sizeof(psk));

  if (cli != NULL) {
    cli_trace(cli, "Handshake step 3/4: running Noise XXpsk3.");
  }
  status = nfc_backup_noise(cli, &psk);
  if (ts_error(status)) {
    if (cli != NULL) {
      cli_error(cli, PRODTEST_ERR_NFC_BACKUP_NOISE_FAILED,
                "NFC noise handshake failed");
    }
  }
  TSH_CHECK_OK(status);

  if (cli != NULL) {
    cli_trace(cli, "Handshake step 4/4: secure channel established.");
    cli_trace(cli, "Handshake: completed");
  }

  handshake_completed = true;

cleanup:
  TSH_RETURN;
}

static ts_t api_authenticate(cli_t *cli, const char *pin, size_t pin_len) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  TSH_CHECK_ARG(pin_len <= NFC_BACKUP_MAX_PIN_LEN);

  // Pad pin with 0xFF
  char pin_padded[NFC_BACKUP_MAX_PIN_LEN] = {0};
  memcpy(pin_padded, pin, pin_len);
  for (size_t i = pin_len; i < NFC_BACKUP_MAX_PIN_LEN; i++) {
    pin_padded[i] = 0xFFU;
  }

  status = nfc_backup_compose_apdu(0x80, 0x03, 0x00, 0x00,
                                   (const uint8_t *)pin_padded,
                                   NFC_BACKUP_MAX_PIN_LEN, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_transceive_logged(cli, "authenticate", 0x03, &cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

cleanup:
  TSH_RETURN;
}

static ts_t api_set_pin(cli_t *cli, const char *new_pin, size_t new_pin_len) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  TSH_CHECK_ARG(new_pin_len <= NFC_BACKUP_MAX_PIN_LEN);

  // Pad pin with 0xFF
  uint8_t pin_padded[NFC_BACKUP_MAX_PIN_LEN] = {0};
  memcpy(pin_padded, new_pin, new_pin_len);
  for (size_t i = new_pin_len; i < NFC_BACKUP_MAX_PIN_LEN; i++) {
    pin_padded[i] = 0xFFU;
  }

  status = nfc_backup_compose_apdu(0x80, 0x04, 0x00, 0x00,
                                   (const uint8_t *)pin_padded,
                                   NFC_BACKUP_MAX_PIN_LEN, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_transceive_logged(cli, "set-pin", 0x04, &cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

cleanup:
  TSH_RETURN;
}

static ts_t api_wipe(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_compose_apdu(0x80, 0x05, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_transceive_logged(cli, "wipe", 0x05, &cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

cleanup:
  TSH_RETURN;
}

static ts_t api_read_pin_counter(cli_t *cli, uint8_t *pin_counter) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(pin_counter != NULL);

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_compose_apdu(0x80, 0x08, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status =
      nfc_backup_transceive_logged(cli, "read-pin-counter", 0x08, &cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 3U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

  *pin_counter = rsp.data[0];

cleanup:
  TSH_RETURN;
}

static ts_t api_read_success_log(cli_t *cli, uint8_t *success_log,
                                 size_t success_log_buf_size,
                                 size_t *success_log_len) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  TSH_CHECK_ARG(success_log != NULL);
  TSH_CHECK_ARG(success_log_len != NULL);

  status = nfc_backup_compose_apdu(0x80, 0x09, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status =
      nfc_backup_transceive_logged(cli, "read-success-log", 0x09, &cmd, &rsp);
  TSH_CHECK_OK(status);

  if (rsp.data_len == 2) {
    TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                  rsp.data[rsp.data_len - 1] == 0x00U,
              TS_EINVAL);
    *success_log_len = 0;
    goto cleanup;
  }

  TSH_CHECK(rsp.data_len > 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);
  TSH_CHECK(rsp.data_len - 2 <= NFC_BACKUP_LOG_RECORD_SIZE, TS_EINVAL);
  TSH_CHECK(success_log_buf_size >= (rsp.data_len - 2), TS_EINVAL);

  *success_log_len = rsp.data_len - 2;

  memcpy(success_log, rsp.data, *success_log_len);

cleanup:
  TSH_RETURN;
}

static ts_t api_read_failure_logs(cli_t *cli, uint8_t *failure_log,
                                  size_t failure_log_buf_size,
                                  size_t *failure_log_len) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(failure_log != NULL);
  TSH_CHECK_ARG(failure_log_len != NULL);

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_compose_apdu(0x80, 0x0A, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status =
      nfc_backup_transceive_logged(cli, "read-failure-logs", 0x0A, &cmd, &rsp);
  TSH_CHECK_OK(status);

  if (rsp.data_len == 2) {
    TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                  rsp.data[rsp.data_len - 1] == 0x00U,
              TS_EINVAL);
    *failure_log_len = 0;
    goto cleanup;
  }

  TSH_CHECK(rsp.data_len > 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);
  TSH_CHECK(failure_log_buf_size >= (rsp.data_len - 2), TS_EINVAL);
  TSH_CHECK((rsp.data_len - 2) % NFC_BACKUP_LOG_RECORD_SIZE == 0, TS_EINVAL);

  *failure_log_len = rsp.data_len - 2;

  memcpy(failure_log, rsp.data, *failure_log_len);

cleanup:
  TSH_RETURN;
}

static ts_t api_read_seed_metadata(cli_t *cli, uint8_t *seed_metadata,
                                   size_t seed_metadata_buf_size,
                                   size_t *seed_metadata_len) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(seed_metadata != NULL);
  TSH_CHECK_ARG(seed_metadata_len != NULL);

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_compose_apdu(0x80, 0x0B, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status =
      nfc_backup_transceive_logged(cli, "read-seed-metadata", 0x0B, &cmd, &rsp);
  TSH_CHECK_OK(status);

  if (rsp.data_len == 2) {
    TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                  rsp.data[rsp.data_len - 1] == 0x00U,
              TS_EINVAL);
    *seed_metadata_len = 0;
    goto cleanup;
  }

  TSH_CHECK(rsp.data_len > 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);
  TSH_CHECK(seed_metadata_buf_size >= (rsp.data_len - 2), TS_EINVAL);

  *seed_metadata_len = rsp.data_len - 2;

  memcpy(seed_metadata, rsp.data, *seed_metadata_len);

cleanup:
  TSH_RETURN;
}

static ts_t api_write_seed_metadata(cli_t *cli, const uint8_t *seed_metadata,
                                    size_t seed_metadata_len) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(seed_metadata != NULL);

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_compose_apdu(0x80, 0x0C, 0x00, 0x00, seed_metadata,
                                   seed_metadata_len, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_transceive_logged(cli, "write-seed-metadata", 0x0C, &cmd,
                                        &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

cleanup:
  TSH_RETURN;
}

static ts_t api_read_seed(cli_t *cli, uint8_t *seed, size_t seed_buf_size,
                          size_t *seed_len) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  TSH_CHECK_ARG(seed != NULL);
  TSH_CHECK_ARG(seed_len != NULL);

  status = nfc_backup_compose_apdu(0x80, 0x0D, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_transceive_logged(cli, "read-seed", 0x0D, &cmd, &rsp);
  TSH_CHECK_OK(status);

  if (rsp.data_len == 2) {
    TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                  rsp.data[rsp.data_len - 1] == 0x00U,
              TS_EINVAL);
    *seed_len = 0;
    goto cleanup;
  }

  TSH_CHECK(rsp.data_len > 2U, TS_EINVAL);
  TSH_CHECK(rsp.data_len == (NFC_BACKUP_SEED_SIZE + 2U), TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);
  TSH_CHECK(seed_buf_size >= NFC_BACKUP_SEED_SIZE, TS_EINVAL);

  memcpy(seed, rsp.data, NFC_BACKUP_SEED_SIZE);
  *seed_len = NFC_BACKUP_SEED_SIZE;

cleanup:
  TSH_RETURN;
}

static ts_t api_write_seed(cli_t *cli, const uint8_t *seed, size_t seed_len) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  TSH_CHECK_ARG(seed != NULL);
  TSH_CHECK_ARG(seed_len == NFC_BACKUP_SEED_SIZE);

  status =
      nfc_backup_compose_apdu(0x80, 0x0E, 0x00, 0x00, seed, seed_len, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_backup_transceive_logged(cli, "write-seed", 0x0E, &cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

cleanup:
  TSH_RETURN;
}

// The card reports the oscillation frequency (kHz) of its MCU, which shifts
// with how well the card is powered by the reader's field: a closely and
// steadily tapped card runs its MCU near NFC_BACKUP_FREQ_BEST_KHZ (its
// maximal frequency), while a barely-coupled card starves for power and its
// MCU frequency drops down towards NFC_BACKUP_FREQ_WORST_KHZ (its minimal
// frequency).
#define NFC_BACKUP_FREQ_BEST_KHZ 100000u
#define NFC_BACKUP_FREQ_WORST_KHZ 3000u

static uint8_t nfc_backup_measure_quality_percent(uint32_t frequency_khz) {
  uint32_t clamped = frequency_khz;
  if (clamped > NFC_BACKUP_FREQ_BEST_KHZ) {
    clamped = NFC_BACKUP_FREQ_BEST_KHZ;
  }
  if (clamped < NFC_BACKUP_FREQ_WORST_KHZ) {
    clamped = NFC_BACKUP_FREQ_WORST_KHZ;
  }

  uint32_t range = NFC_BACKUP_FREQ_BEST_KHZ - NFC_BACKUP_FREQ_WORST_KHZ;
  uint32_t offset = clamped - NFC_BACKUP_FREQ_WORST_KHZ;
  return (uint8_t)((offset * 100u) / range);
}

static const char *nfc_backup_measure_quality_label(uint8_t percent) {
  if (percent >= 80) {
    return "EXCELLENT";
  }
  if (percent >= 60) {
    return "GOOD";
  }
  if (percent >= 40) {
    return "FAIR";
  }
  if (percent >= 20) {
    return "POOR";
  }
  return "BAD";
}

static ts_t system_measure(cli_t *cli, uint32_t *frequency_khz) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_compose_apdu(0x20, 0x01, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status =
      nfc_backup_transceive_logged(cli, "system-measure", 0x01, &cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == (2 + sizeof(uint32_t)), TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

  *frequency_khz = (rsp.data[0] << 24) | (rsp.data[1] << 16) |
                   (rsp.data[2] << 8) | (rsp.data[3]);
  cli_trace(cli, "NFC card MCU frequency: %lu.%02lu MHz",
            (unsigned long)(*frequency_khz / 1000U),
            (unsigned long)((*frequency_khz % 1000U) / 10U));

  goto cleanup;

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_activate_flashloader(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {.data = {0xC2, 0xA0, 0x00, 0x00, 0x00},
                            .data_len = 5};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_secure_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U &&
                rsp.data[rsp.data_len - 1] == 0x00U,
            TS_EINVAL);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_authenticate(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    TSH_CHECK(false, TS_EINVAL);
  }

  const char *pin = NULL;
  size_t pin_len = 0;

  if (cli_has_arg(cli, "pin")) {
    pin = cli_arg(cli, "pin");
    pin_len = strlen(pin);
  }

  status = nfc_backup_handshake(cli);
  TSH_CHECK_OK(status);

  status = api_authenticate(cli, pin, pin_len);
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_set_pin(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    TSH_CHECK(false, TS_EINVAL);
  }

  const char *new_pin = NULL;
  uint32_t new_pin_len = 0;
  const char *old_pin = NULL;
  uint32_t old_pin_len = 0;

  if (cli_has_arg(cli, "new_pin")) {
    new_pin = cli_arg(cli, "new_pin");
    new_pin_len = strlen(new_pin);
  }

  if (cli_has_arg(cli, "old_pin")) {
    old_pin = cli_arg(cli, "old_pin");
    old_pin_len = strlen(old_pin);
  }

  status = nfc_backup_handshake(cli);
  TSH_CHECK_OK(status);

  status = api_authenticate(cli, old_pin, old_pin_len);
  TSH_CHECK_OK(status);

  status = api_set_pin(cli, new_pin, new_pin_len);
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_read_pin_counter(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  uint8_t pin_counter = 0;
  status = api_read_pin_counter(cli, &pin_counter);
  TSH_CHECK_OK(status);

  cli_trace(cli, "PIN counter: %u", pin_counter);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_read_success_log(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  uint8_t success_log[32] = {0};
  size_t success_log_len = 0;
  status = api_read_success_log(cli, success_log, sizeof(success_log),
                                &success_log_len);
  TSH_CHECK_OK(status);

  if (success_log_len == 0) {
    cli_trace(cli, "Success log: empty");
    goto cleanup;
  }

  char text[65] = {0};
  cstr_encode_hex(text, sizeof(text), success_log, success_log_len);
  cli_trace(cli, "Success log (%u bytes): %s", (unsigned)success_log_len, text);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_read_failure_logs(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  uint8_t failure_log[NFC_BACKUP_LOG_RECORD_SIZE * NFC_BACKUP_MAX_PIN_TRIALS] =
      {0};
  size_t failure_log_len = 0;
  status = api_read_failure_logs(cli, failure_log, sizeof(failure_log),
                                 &failure_log_len);
  TSH_CHECK_OK(status);

  size_t record_count = failure_log_len / NFC_BACKUP_LOG_RECORD_SIZE;
  if (record_count == 0) {
    cli_trace(cli, "Failure log: empty");
    goto cleanup;
  }

  cli_trace(cli, "Failure log entries: %u", (unsigned)record_count);
  char text[65] = {0};
  for (size_t i = 0; i < record_count; i++) {
    cstr_encode_hex(text, sizeof(text),
                    &failure_log[i * NFC_BACKUP_LOG_RECORD_SIZE],
                    NFC_BACKUP_LOG_RECORD_SIZE);
    cli_trace(cli, "  Entry %u/%u: %s", (unsigned)(i + 1),
              (unsigned)record_count, text);
  }

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_wipe(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  status = nfc_backup_handshake(cli);
  TSH_CHECK_OK(status);

  status = api_wipe(cli);
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_read_seed_metadata(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  uint8_t seed_metadata[NFC_BACKUP_SEED_METADATA_SIZE] = {0};
  size_t seed_metadata_len = 0;
  status = api_read_seed_metadata(cli, seed_metadata, sizeof(seed_metadata),
                                  &seed_metadata_len);
  TSH_CHECK_OK(status);

  if (seed_metadata_len == 0) {
    cli_trace(cli, "Seed metadata: empty");
    goto cleanup;
  }

  nfc_backup_trace_hex_preview(cli, "Seed metadata", seed_metadata,
                               seed_metadata_len);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_write_seed_metadata(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    TSH_CHECK(false, TS_EINVAL);
  }

  const char *pin = NULL;
  size_t pin_len = 0;

  if (cli_has_arg(cli, "pin")) {
    pin = cli_arg(cli, "pin");
    pin_len = strlen(pin);
  }

  status = nfc_backup_handshake(cli);
  TSH_CHECK_OK(status);

  status = api_authenticate(cli, pin, pin_len);
  TSH_CHECK_OK(status);

  uint8_t metadata[NFC_BACKUP_SEED_METADATA_SIZE] = {0};
  for (size_t i = 0; i < NFC_BACKUP_SEED_METADATA_SIZE; i++) {
    metadata[i] = (uint8_t)i;
  }

  status = api_write_seed_metadata(cli, metadata, sizeof(metadata));
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_read_seed(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    TSH_CHECK(false, TS_EINVAL);
  }

  const char *pin = NULL;
  size_t pin_len = 0;

  if (cli_has_arg(cli, "pin")) {
    pin = cli_arg(cli, "pin");
    pin_len = strlen(pin);
  }

  status = nfc_backup_handshake(cli);
  TSH_CHECK_OK(status);

  status = api_authenticate(cli, pin, pin_len);
  TSH_CHECK_OK(status);

  uint8_t seed[NFC_BACKUP_SEED_SIZE] = {0};
  size_t seed_size = 0;
  status = api_read_seed(cli, seed, sizeof(seed), &seed_size);
  TSH_CHECK_OK(status);

  if (seed_size == 0) {
    cli_trace(cli, "Seed: empty");
    goto cleanup;
  }

  nfc_backup_trace_hex_preview(cli, "Seed", seed, seed_size);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_write_seed(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    TSH_CHECK(false, TS_EINVAL);
  }

  const char *pin = NULL;
  size_t pin_len = 0;

  if (cli_has_arg(cli, "pin")) {
    pin = cli_arg(cli, "pin");
    pin_len = strlen(pin);
  }

  status = nfc_backup_handshake(cli);
  TSH_CHECK_OK(status);

  status = api_authenticate(cli, pin, pin_len);
  TSH_CHECK_OK(status);

  uint8_t seed[NFC_BACKUP_SEED_SIZE] = {0};
  for (size_t i = 0; i < NFC_BACKUP_SEED_SIZE; i++) {
    seed[i] = 0xAA;
  }

  status = api_write_seed(cli, seed, sizeof(seed));
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_measure(cli_t *cli) {
  TSH_DECLARE;
  ts_t status;

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    TSH_CHECK(false, TS_EINVAL);
  }

  uint32_t frequency_khz = 0;
  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted by operator.");
      break;
    }

    status = system_measure(cli, &frequency_khz);
    TSH_CHECK_OK(status);

    uint8_t percent = nfc_backup_measure_quality_percent(frequency_khz);
    const char *quality = nfc_backup_measure_quality_label(percent);
    unsigned long freq_mhz_int = frequency_khz / 1000U;
    unsigned long freq_mhz_frac = (frequency_khz % 1000U) / 10U;

    char label[32] = {0};
    snprintf_(label, sizeof(label), "%s / %lu.%02lu MHz", quality, freq_mhz_int,
              freq_mhz_frac);

    cli_progress(cli, "frequency=%lu.%02luMHz quality=%u%% (%s)", freq_mhz_int,
                 freq_mhz_frac, (unsigned)percent, quality);

    screen_prodtest_signal_meter(percent, label, strlen(label));

    // systick_delay_ms(100);
  }

cleanup:
  prodtest_show_homescreen();
  TSH_RETURN;
}

// Transparent mode CLI: buffers incoming characters into a line and, once a
// termination character (or a full buffer) is seen, dispatches it to one of
// the registered command handlers below.

typedef const char *(*nfc_backup_tm_cmd_fn_t)(cli_t *cli, const char *arg);

// Tracks whether the NFC field is powered and whether a card is tapped.
static bool nfc_tm_running = false;
static bool nfc_tm_connected = false;

static const char *nfc_backup_tm_cmd_on(cli_t *cli, const char *arg) {
  if (nfc_tm_running) {
    return "ERROR: already on";
  }

  if (ts_error(nfc_init()) || ts_error(nfc_start_discovery())) {
    return "ERROR";
  }

  nfc_tm_running = true;
  nfc_tm_connected = false;
  return "OK";
}

static const char *nfc_backup_tm_cmd_off(cli_t *cli, const char *arg) {
  if (!nfc_tm_running) {
    return "ERROR: already off";
  }

  nfc_stop_discovery();
  nfc_deinit();
  nfc_tm_running = false;
  nfc_tm_connected = false;
  return "OK";
}

static const char *nfc_backup_tm_cmd_reset(cli_t *cli, const char *arg) {
  // Example: power-cycle the NFC field and restart discovery.
  nfc_stop_discovery();
  nfc_deinit();
  nfc_tm_connected = false;

  if (ts_error(nfc_init()) || ts_error(nfc_start_discovery())) {
    nfc_tm_running = false;
    return "ERROR";
  }

  nfc_tm_running = true;
  return "OK";
}

static const char *nfc_backup_tm_cmd_noise(cli_t *cli, const char *arg) {
  if (!nfc_tm_connected) {
    return "ERROR: no card connected";
  }

  ts_t status = nfc_backup_handshake(cli);
  if (ts_ok(status)) {
    return "OK";
  }

  return "ERROR: handshake failed";
}

static const char *nfc_backup_tm_cmd_transceive(cli_t *cli, const char *arg) {
  // Example: decode `arg` as hex, transceive it, and return the response
  // encoded back as hex. The buffer is static so it outlives this call.
  static char resp_text[2 * NFC_MAX_APDU_LEN + 1];

  if (!nfc_tm_connected) {
    return "ERROR: no card connected";
  }

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};
  size_t cmd_len = 0;

  if (!cstr_decode_hex(arg, cmd.data, sizeof(cmd.data), &cmd_len) ||
      cmd_len == 0) {
    return "ERROR: invalid hex argument";
  }
  cmd.data_len = (uint16_t)cmd_len;

  if (ts_error(nfc_backup_secure_transceive(&cmd, &rsp))) {
    return "ERROR: transceive failed";
  }

  cstr_encode_hex(resp_text, sizeof(resp_text), rsp.data, rsp.data_len);
  return resp_text;
}

// Command table: add new entries here to extend the transparent mode CLI.
static const struct {
  const char *name;
  nfc_backup_tm_cmd_fn_t handler;
} nfc_backup_tm_cmds[] = {
    {"on", nfc_backup_tm_cmd_on},
    {"off", nfc_backup_tm_cmd_off},
    {"reset", nfc_backup_tm_cmd_reset},
    {"noise", nfc_backup_tm_cmd_noise},
    {"transceive", nfc_backup_tm_cmd_transceive},
};

// Splits `line` into a command name and its (possibly empty) argument, and
// invokes the matching handler from nfc_backup_tm_cmds.
static void nfc_backup_tm_dispatch(cli_t *cli, char *line) {
  char *arg = strchr(line, ' ');
  if (arg != NULL) {
    *arg++ = '\0';
    while (*arg == ' ') {
      arg++;
    }
  } else {
    arg = "";
  }

  for (size_t i = 0;
       i < sizeof(nfc_backup_tm_cmds) / sizeof(nfc_backup_tm_cmds[0]); i++) {
    if (strcmp(line, nfc_backup_tm_cmds[i].name) == 0) {
      const char *resp = nfc_backup_tm_cmds[i].handler(cli, arg);
      if (resp != NULL) {
        cli->write(cli, resp, strlen(resp));
        cli->write(cli, "\r\n", 2);
      }
      return;
    }
  }

  cli_trace(cli, "Unknown command: %s", line);
}

static void prodtest_nfc_backup_transparent_mode(cli_t *cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli,
            "Entering transparent mode. Commands: on, off, reset, noise, "
            "transceive <hex>.");

  char line_buf[1024] = {0};
  size_t line_len = 0;

  sysevents_t awaited_events = {0};
  sysevents_t signalled_events = {0};
  awaited_events.read_ready = 1 << SYSHANDLE_NFC;

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted by operator.");
      break;
    }

    if (nfc_tm_running) {
      sysevents_poll(&awaited_events, &signalled_events, ticks_timeout(0));

      if (signalled_events.read_ready & (1 << SYSHANDLE_NFC)) {
        nfc_event_t event_flag;
        if (nfc_get_event(&event_flag)) {
          if (event_flag == NFC_EVENT_CONNECTED) {
            nfc_tm_connected = true;
            cli_trace(cli, "NFC card connected.");
          } else if (event_flag == NFC_EVENT_DISCONNECTED) {
            nfc_tm_connected = false;
            cli_trace(cli, "NFC card removed.");
          }
        }
      }
    }

    uint8_t c;
    ssize_t len = syshandle_read(SYSHANDLE_USB_VCP, &c, 1);
    if (len != 1) {
      continue;
    }

    if (c == '\n' || c == '\r') {
      if (line_len > 0) {
        line_buf[line_len] = '\0';
        nfc_backup_tm_dispatch(cli, line_buf);
        line_len = 0;
      }
      continue;
    }

    if (line_len >= sizeof(line_buf) - 1) {
      // Buffer full: process what has been collected so far.
      line_buf[line_len] = '\0';
      nfc_backup_tm_dispatch(cli, line_buf);
      line_len = 0;
    }

    line_buf[line_len++] = (char)c;
  }

  if (nfc_tm_running) {
    nfc_stop_discovery();
    nfc_deinit();
    nfc_tm_running = false;
    nfc_tm_connected = false;
  }
}

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_handshake, &nfc_backup_handshake,
                        PRODTEST_ERR_NFC_BACKUP_HANDSHAKE_FAILED,
                        "NFC handshake failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_authenticate,
                        &nfc_backup_authenticate,
                        PRODTEST_ERR_NFC_BACKUP_AUTHENTICATE_FAILED,
                        "NFC authenticate failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_set_pin, &nfc_backup_set_pin,
                        PRODTEST_ERR_NFC_BACKUP_SET_PIN_FAILED,
                        "NFC set PIN failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_wipe, &nfc_backup_wipe,
                        PRODTEST_ERR_NFC_BACKUP_WIPE_FAILED, "NFC wipe failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_read_pin_counter,
                        &nfc_backup_read_pin_counter,
                        PRODTEST_ERR_NFC_BACKUP_READ_PIN_COUNTER_FAILED,
                        "NFC read PIN counter failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_read_success_log,
                        &nfc_backup_read_success_log,
                        PRODTEST_ERR_NFC_BACKUP_READ_SUCCESS_LOG_FAILED,
                        "NFC read success log failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_read_failure_logs,
                        &nfc_backup_read_failure_logs,
                        PRODTEST_ERR_NFC_BACKUP_READ_FAILURE_LOGS_FAILED,
                        "NFC read failure logs failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_read_seed_metadata,
                        &nfc_backup_read_seed_metadata,
                        PRODTEST_ERR_NFC_BACKUP_READ_SEED_METADATA_FAILED,
                        "NFC read seed metadata failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_write_seed_metadata,
                        &nfc_backup_write_seed_metadata,
                        PRODTEST_ERR_NFC_BACKUP_WRITE_SEED_METADATA_FAILED,
                        "NFC write seed metadata failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_read_seed, &nfc_backup_read_seed,
                        PRODTEST_ERR_NFC_BACKUP_READ_SEED_FAILED,
                        "NFC read seed failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_write_seed, &nfc_backup_write_seed,
                        PRODTEST_ERR_NFC_BACKUP_WRITE_SEED_FAILED,
                        "NFC write seed failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_activate_flashloader,
                        &nfc_backup_activate_flashloader,
                        PRODTEST_ERR_NFC_BACKUP_ACTIVATE_FLASHLOADER_FAILED,
                        "NFC activate flashloader failed");

REGISTER_NFC_BACKUP_CMD(prodtest_nfc_backup_measure, &nfc_backup_measure,
                        PRODTEST_ERR_NFC_BACKUP_MEASURE_FAILED,
                        "NFC measure failed");

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-backup-handshake",
  .func = prodtest_nfc_backup_handshake,
  .info = "Run nfc-backup handshake test",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-authenticate",
  .func = prodtest_nfc_backup_authenticate,
  .info = "Run nfc-backup authenticate test",
  .args = "[pin]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-set-pin",
  .func = prodtest_nfc_backup_set_pin,
  .info = "Run nfc-backup set pin test",
  .args = "[new_pin][old_pin]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-wipe",
  .func = prodtest_nfc_backup_wipe,
  .info = "Run nfc-backup wipe test",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-pin-counter",
  .func = prodtest_nfc_backup_read_pin_counter,
  .info = "Run nfc-backup read pin counter",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-success-log",
  .func = prodtest_nfc_backup_read_success_log,
  .info = "Run nfc-backup read success log",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-failure-logs",
  .func = prodtest_nfc_backup_read_failure_logs,
  .info = "Run nfc-backup read failure logs",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-seed-metadata",
  .func = prodtest_nfc_backup_read_seed_metadata,
  .info = "Run nfc-backup read seed metadata",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-write-seed-metadata",
  .func = prodtest_nfc_backup_write_seed_metadata,
  .info = "Run nfc-backup write seed metadata",
  .args = "[pin]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-seed",
  .func = prodtest_nfc_backup_read_seed,
  .info = "Run nfc-backup read seed",
  .args = "[pin]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-write-seed",
  .func = prodtest_nfc_backup_write_seed,
  .info = "Run nfc-backup write seed",
  .args = "[pin]"
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-activate-flashloader",
  .func = prodtest_nfc_backup_activate_flashloader,
  .info = "Run nfc-backup activate flashloader test",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-transparent-mode",
  .func = prodtest_nfc_backup_transparent_mode,
  .info = "Run nfc-backup tests",
  .args = ""
);  

PRODTEST_CLI_CMD(
  .name = "nfc-backup-measure",
  .func = prodtest_nfc_backup_measure,
  .info = "Run nfc-backup measure test",
  .args = ""
);

#endif  // USE_NFC
