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
#include <sys/rng.h>
#include <sys/sysevent.h>
#include <sys/systick.h>
#include <rtl/printf.h>

#include "prodtest_error_codes.h"

static noise_xxpsk3_initiator_t intr = {0};

typedef struct {
    uint8_t  version;                     // 0 = v1, 1 = v2, 2 = v3
    uint32_t serial_number;               // Certificate serial
    char     issuer_c[8];                 // Issuer Country
    char     issuer_o[64];                // Issuer Organization
    char     issuer_cn[64];               // Issuer Common Name
    char     not_before[16];              // UTCTime string (e.g. "260615154143Z")
    char     not_after[16];               // UTCTime string
    char     subject_cn[64];              // Subject Common Name
    char     subject_serial[32];          // Subject serialNumber attribute
    char     subject_dn_qualifier[32];    // Subject dnQualifier attribute
    uint8_t  public_key[32];              // Ed25519 Public Key (32 bytes)
    bool     is_ca;                       // BasicConstraints CA flag
    uint16_t key_usage;                   // KeyUsage bitmask
    uint8_t  auth_key_id[20];             // Authority Key Identifier
    uint8_t  signature[64];               // Ed25519 Signature (64 bytes)
} nfc_backup_certificate_t;


typedef ts_t (*on_tap_callback_t) (cli_t *cli);

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

  cli_trace(cli, "Tap NFC backup card.");

  sysevents_t awaited_events = {0};
  sysevents_t signalled_events = {0};
  nfc_event_t event_flag;
  
  awaited_events.read_ready = 1 << SYSHANDLE_NFC;
  
  while (true) {

    if (cli_aborted(cli)) {
      cli_trace(cli, "Aborted.");
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
      
      cli_trace(cli, "NFC card detected.");

      nfc_dev_info_t dev_info;
      nfc_get_device_info(&dev_info);

      if (dev_info.type != NFC_DEV_TYPE_A) {
        cli_error(cli, PRODTEST_ERR_NFC_BACKUP_UNEXPECTED_CARD_TYPE,
                  "Unexpected card type (%d)", dev_info.type);
        goto cleanup;
      }

      // Call ON-TAP callback function
      status = (callback)(cli);
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
    return  status;
  }

  status = nfc_wait_for_tap(cli, callback);
  if (ts_error(status)) {
    nfc_poll_stop();
    return status;
  }

  nfc_poll_stop();
  return TS_OK;
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
static void parse_dn(const uint8_t *p, size_t len, 
                     char *cn, size_t cn_max, 
                     char *c, size_t c_max, 
                     char *o, size_t o_max, 
                     char *serial, size_t serial_max, 
                     char *dn_qual, size_t dn_qual_max) {
    const uint8_t *end = p + len;
    uint8_t tag;
    size_t set_len, seq_len, oid_len, str_len;

    while (p < end) {
        p = asn1_parse_header(p, end, &tag, &set_len);    // SET
        if (!p || tag != 0x31) break;
        
        const uint8_t *set_end = p + set_len;
        const uint8_t *sp = p;
        sp = asn1_parse_header(sp, set_end, &tag, &seq_len); // SEQUENCE
        if (!sp || tag != 0x30) { p = set_end; continue; }

        const uint8_t *oid_ptr = asn1_parse_header(sp, set_end, &tag, &oid_len);
        if (!oid_ptr || tag != 0x06) { p = set_end; continue; }

        const uint8_t *val_ptr = asn1_parse_header(oid_ptr + oid_len, set_end, &tag, &str_len);
        if (!val_ptr) { p = set_end; continue; }

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
        else if (oid_len == 3 && memcmp(oid_ptr, "\x55\x04\x05", 3) == 0 && serial) {
            snprintf_(serial, serial_max, "%.*s", (int)str_len, val_ptr);
        }
        // OID 2.5.4.46 (dnQualifier)
        else if (oid_len == 3 && memcmp(oid_ptr, "\x55\x04\x2e", 3) == 0 && dn_qual) {
            snprintf_(dn_qual, dn_qual_max, "%.*s", (int)str_len, val_ptr);
        }

        p = set_end;
    }
}

// Main parser function
int parse_x509_certificate(const uint8_t *buffer, size_t buffer_len, nfc_backup_certificate_t *cert) {
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
      const uint8_t *ver_ptr = asn1_parse_header(outer_ptr, outer_end, &tag, &ver_len);
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
        parse_dn(p, len, cert->issuer_cn, sizeof(cert->issuer_cn),
                         cert->issuer_c,  sizeof(cert->issuer_c),
                         cert->issuer_o,  sizeof(cert->issuer_o),
                         NULL, 0, NULL, 0);
        p += len;
    }

    // Validity (SEQUENCE)
    p = asn1_parse_header(p, tbs_end, &tag, &len);
    if (p && tag == 0x30) {
        const uint8_t *val_end = p + len;
        const uint8_t *v = asn1_parse_header(p, val_end, &tag, &len); // Not Before
        if (v && tag == 0x17) {
            snprintf_(cert->not_before, sizeof(cert->not_before), "%.*s", (int)len, v);
            v += len;
            v = asn1_parse_header(v, val_end, &tag, &len);              // Not After
            if (v && tag == 0x17) {
                snprintf_(cert->not_after, sizeof(cert->not_after), "%.*s", (int)len, v);
            }
        }
        p = val_end;
    }

    // Subject (SEQUENCE)
    p = asn1_parse_header(p, tbs_end, &tag, &len);
    if (p && tag == 0x30) {
        parse_dn(p, len, cert->subject_cn, sizeof(cert->subject_cn),
                         NULL, 0, NULL, 0,
                         cert->subject_serial, sizeof(cert->subject_serial),
                         cert->subject_dn_qualifier, sizeof(cert->subject_dn_qualifier));
        p += len;
    }

    // SubjectPublicKeyInfo (SEQUENCE)
    p = asn1_parse_header(p, tbs_end, &tag, &len);
    if (p && tag == 0x30) {
        const uint8_t *spki_end = p + len;
        const uint8_t *sp = asn1_parse_header(p, spki_end, &tag, &len); // AlgId Sequence
        if (sp && tag == 0x30) {
            sp += len;
            sp = asn1_parse_header(sp, spki_end, &tag, &len);          // BIT STRING
            if (sp && tag == 0x03 && len == 33) {                      // 1 unused bit byte + 32 key bytes
                memcpy(cert->public_key, sp + 1, 32);
            }
        }
        p = spki_end;
    }

    // Extensions [3] EXPLICIT
    if (p < tbs_end && *p == 0xa3) {
        p = asn1_parse_header(p, tbs_end, &tag, &len);
        p = asn1_parse_header(p, tbs_end, &tag, &len); // Extensions SEQUENCE
        const uint8_t *exts_end = p + len;

        while (p < exts_end) {
            p = asn1_parse_header(p, exts_end, &tag, &len); // Extension SEQUENCE
            if (!p || tag != 0x30) break;

            const uint8_t *ext_end = p + len;
            const uint8_t *oid_ptr = asn1_parse_header(p, ext_end, &tag, &len);
            if (!oid_ptr || tag != 0x06) { p = ext_end; continue; }

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
                        cert->key_usage = ku[1]; // Store key usage bitmask
                    }
                }
                // Authority Key Identifier (OID 2.5.29.35 -> 55 1d 23)
                else if (memcmp(oid_ptr, "\x55\x1d\x23", 3) == 0) {
                    const uint8_t *aki = asn1_parse_header(curr, curr + len, &tag, &len);
                    if (aki && tag == 0x30) {
                        const uint8_t *key_id = asn1_parse_header(aki, aki + len, &tag, &len);
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
    p = asn1_parse_header(p, end, &tag, &len); // Signature Algorithm
    if (p && tag == 0x30) p += len;

    p = asn1_parse_header(p, end, &tag, &len); // Signature BIT STRING
    if (p && tag == 0x03 && len == 65) {      // 1 byte padding flags + 64 bytes Ed25519 sig
        memcpy(cert->signature, p + 1, 64);
    }

    return 0;
}

static void print_certificate(cli_t *cli, nfc_backup_certificate_t const* cert){

  char text[256];

  cli_trace(cli, "Certificate:");
  cli_trace(cli, "  Version: %u", cert->version);
  cli_trace(cli, "  Serial Number: %u", cert->serial_number);
  cli_trace(cli, "  Subject: %s (%s)", cert->subject_cn, cert->subject_serial);
  cli_trace(cli, "  Issuer: %s (%s)", cert->issuer_cn, cert->issuer_o);
  cli_trace(cli, "  Validity: Not Before=%s, Not After=%s", cert->not_before, cert->not_after);
  cstr_encode_hex(text, sizeof(text), cert->public_key, sizeof(cert->public_key));
  cli_trace(cli, "  Public Key: %s", text);
  cli_trace(cli, "  Is CA: %s", cert->is_ca ? "true" : "false");
  cli_trace(cli, "  Key Usage: 0x%02X", cert->key_usage);
  cstr_encode_hex(text, sizeof(text), cert->auth_key_id, sizeof(cert->auth_key_id));
  cli_trace(cli, "  Authority Key Identifier: %s", text);

}

static ts_t nfc_backup_compose_apdu(uint8_t cla, uint8_t ins, uint8_t p1,
                                    uint8_t p2, const uint8_t* data,
                                    size_t data_len, nfc_apdu_message_t* apdu) {
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

static ts_t nfc_backup_noise(cli_t* cli, uint8_t (*psk)[32]) {

  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(*psk != NULL);
  bool noise_status = false;

  // Generate static private key for initiator
  uint8_t static_private_key[NOISE_XXPSK3_DHLEN] = {0};
  rng_fill_buffer(static_private_key, sizeof(static_private_key));

  noise_status = noise_xxpsk3_initiator_init(&intr, *psk, static_private_key);
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

  status = nfc_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  uint8_t certificate[512] = {0};
  size_t certificate_size = 0;

  noise_status = noise_xxpsk3_initiator_handle_response1(
      &intr, rsp.data, rsp.data_len - 2, certificate, sizeof(certificate),
      &certificate_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  nfc_backup_certificate_t cert = {0};
  parse_x509_certificate(certificate, certificate_size, &cert);
  print_certificate(cli, &cert);

  noise_status = noise_xxpsk3_initiator_create_request2(
      &intr, NULL, 0, request, sizeof(request), &request_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  status = nfc_backup_compose_apdu(0x80, 0x01, 0x01, 0x00, request,
                                   request_size, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  uint8_t plain_text[256] = {0};
  size_t plain_text_size = 0;
  noise_status = noise_xxpsk3_receive_message(
      &intr.transport_state, rsp.data, rsp.data_len - 2, plain_text,
      sizeof(plain_text), &plain_text_size);
  TSH_CHECK(noise_status, TS_EINVAL);

  cli_trace(cli, "Card welcome message: %.*s", (int)plain_text_size,
            plain_text);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_backup_handshake(cli_t* cli) {

  TSH_DECLARE;
  ts_t status = TS_OK;

  // Clear the initiator structure
  memset(&intr, 0, sizeof(intr));

  cli_trace(cli, "++++++ NFC backup handshake start ++++++");

  nfc_apdu_message_t cmd = {.data = {0x00, 0xA4, 0x04, 0x00, 0x07, 0xA0, 0x00,
                                     0x00, 0x09, 0x59, 0x00, 0x01},
                            .data_len = 12};

  nfc_apdu_message_t resp = {0};

  status = nfc_transceive(&cmd, &resp);

  TSH_CHECK(resp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(resp.data[0] == 0x90U && resp.data[1] == 0x00U, TS_EINVAL);

  uint8_t pcd_psk[16] = {0};
  uint8_t picc_psk[16] = {0};
  uint16_t picc_psk_len = 0;

  rng_fill_buffer(pcd_psk, sizeof(pcd_psk));

  status = nfc_transceive_psk(pcd_psk, sizeof(pcd_psk), picc_psk,
                              sizeof(picc_psk), &picc_psk_len);

  if (ts_error(status) || picc_psk_len != sizeof(picc_psk)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_PSK_EXCHANGE_FAILED,
              "NFC PSK exchange failed");
    goto cleanup;
  }

  // Combine both share into PSK
  uint8_t psk[32] = {0};
  memcpy(psk, pcd_psk, 16);
  memcpy(psk + 16, picc_psk, 16);

  char text[256] = {0};
  cstr_encode_hex(text, sizeof(text), &psk, sizeof(psk));
  cli_trace(cli, "Exchanged PSK: %s", text);

  status = nfc_backup_noise(cli, &psk);
  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_NOISE_FAILED,
              "NFC noise handshake failed");
    goto cleanup;
  }

  cli_trace(cli, "++++++ NFC backup completed ++++++++++++");

cleanup:
  return status;
}



static ts_t nfc_backup_read_pin_counter(cli_t* cli) {
  
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {0};
  nfc_apdu_message_t rsp = {0};

  status = nfc_backup_compose_apdu(0x80, 0x02, 0x00, 0x00, NULL, 0, &cmd);
  TSH_CHECK_OK(status);

  status = nfc_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 3U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U && rsp.data[rsp.data_len - 1] == 0x00U, TS_EINVAL);

  uint8_t pin_counter = rsp.data[0];
  cli_trace(cli, "PIN counter: %u", pin_counter);

cleanup:
  TSH_RETURN;

}
 
static ts_t nfc_backup_activate_flashloader(cli_t* cli) {
  
  TSH_DECLARE;
  ts_t status;

  nfc_apdu_message_t cmd = {
    .data = {0xC2, 0xA0, 0x00, 0x00, 0x00},
    .data_len = 5
  };
  nfc_apdu_message_t rsp = {0};

  status = nfc_transceive(&cmd, &rsp);
  TSH_CHECK_OK(status);

  TSH_CHECK(rsp.data_len == 2U, TS_EINVAL);
  TSH_CHECK(rsp.data[rsp.data_len - 2] == 0x90U && rsp.data[rsp.data_len - 1] == 0x00U, TS_EINVAL);

cleanup:
  TSH_RETURN;
}

static void prodtest_nfc_backup_handshake(cli_t* cli) {
  
  ts_t status = nfc_backup_tap(cli, &nfc_backup_handshake);

  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_HANDSHAKE_FAILED,
              "NFC handshake failed");
  } else {
    cli_ok(cli, "");
  }

}

static void prodtest_nfc_backup_read_pin_counter(cli_t* cli) {
  
  ts_t status = nfc_backup_tap(cli, &nfc_backup_read_pin_counter);

  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_READ_PIN_COUNTER_FAILED,
              "NFC read PIN counter failed");
  } else {
    cli_ok(cli, "");
  }

}


static void prodtest_nfc_backup_activate_flashloader(cli_t* cli) {

  ts_t status = nfc_backup_tap(cli, &nfc_backup_activate_flashloader);

  if (ts_error(status)) {
    cli_error(cli, PRODTEST_ERR_NFC_BACKUP_ACTIVATE_FLASHLOADER_FAILED,
              "NFC activate flashloader failed");
  } else {
    cli_ok(cli, "");
  }

}


// clang-format off

PRODTEST_CLI_CMD(
  .name = "nfc-backup-handshake",
  .func = prodtest_nfc_backup_handshake,
  .info = "Run nfc-backup handshake test",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nfc-backup-read-pin-counter",
  .func = prodtest_nfc_backup_read_pin_counter,
  .info = "Run nfc-backup read pin counter",
  .args = ""
);

// PRODTEST_CLI_CMD(
//   .name = "nfc-backup-read-success-log",
//   .func = prodtest_nfc_backup_read_success_log,
//   .info = "Run nfc-backup read success log",
//   .args = ""
// );

// PRODTEST_CLI_CMD(
//   .name = "nfc-backup-read-failure-logs",
//   .func = prodtest_nfc_backup_read_failure_logs,
//   .info = "Run nfc-backup read failure logs",
//   .args = ""
// );

// PRODTEST_CLI_CMD(
//   .name = "nfc-backup-read-seed-metadata",
//   .func = prodtest_nfc_backup_read_seed_metadata,
//   .info = "Run nfc-backup read seed metadata",
//   .args = ""
// );

PRODTEST_CLI_CMD(
  .name = "nfc-backup-activate-flashloader",
  .func = prodtest_nfc_backup_activate_flashloader,
  .info = "Run nfc-backup activate flashloader test",
  .args = ""
);




#endif  // USE_NFC
