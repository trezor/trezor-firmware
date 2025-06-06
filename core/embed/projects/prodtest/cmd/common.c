#include "common.h"

#include "buffer.h"
#include "der.h"
#include "ecdsa.h"
#include "memzero.h"
#include "nist256p1.h"
#include "sha2.h"
#include "string.h"

// Identifier of context-specific constructed tag 3, which is used for
// extensions in X.509.
#define DER_X509_EXTENSIONS 0xa3

// Identifier of context-specific primitive tag 0, which is used for
// keyIdentifier in authorityKeyIdentifier.
#define DER_X509_KEY_IDENTIFIER 0x80

// DER-encoded object identifier of the authority key identifier extension
// (id-ce-authorityKeyIdentifier).
const uint8_t OID_AUTHORITY_KEY_IDENTIFIER[] = {0x06, 0x03, 0x55, 0x1d, 0x23};

// clang-format off
static const uint8_t ECDSA_WITH_SHA256[] = {
  0x30, 0x0a, // a sequence of 10 bytes
    0x06, 0x08, // an OID of 8 bytes
      0x2a, 0x86, 0x48, 0xce, 0x3d, 0x04, 0x03, 0x02,
};

static const uint8_t OID_COMMON_NAME[] = {
  0x06, 0x03, // an OID of 3 bytes
    0x55, 0x04, 0x03, // corresponds to commonName in X.509
};

static const uint8_t SUBJECT_COMMON_NAME[] = {
#ifdef TREZOR_MODEL_T2B1
  'T', '2', 'B', '1', ' ', 'T', 'r', 'e', 'z', 'o', 'r', ' ', 'S', 'a', 'f', 'e', ' ', '3',
#endif
#ifdef TREZOR_MODEL_T3B1
  'T', '3', 'B', '1', ' ', 'T', 'r', 'e', 'z', 'o', 'r', ' ', 'S', 'a', 'f', 'e', ' ', '3',
#endif
#ifdef TREZOR_MODEL_T3T1
  'T', '3', 'T', '1', ' ', 'T', 'r', 'e', 'z', 'o', 'r', ' ', 'S', 'a', 'f', 'e', ' ', '5',
#endif
};
// clang-format on

static bool get_cert_extensions(DER_ITEM* tbs_cert, DER_ITEM* extensions) {
  // Find the certificate extensions in the tbsCertificate.
  DER_ITEM cert_item = {0};
  while (der_read_item(&tbs_cert->buf, &cert_item)) {
    if (cert_item.id == DER_X509_EXTENSIONS) {
      // Open the extensions sequence.
      return der_read_item(&cert_item.buf, extensions) &&
             extensions->id == DER_SEQUENCE;
    }
  }
  return false;
}

static bool get_extension_value(const uint8_t* extension_oid,
                                size_t extension_oid_size, DER_ITEM* extensions,
                                DER_ITEM* extension_value) {
  // Find the extension with the given OID.
  DER_ITEM extension = {0};
  while (der_read_item(&extensions->buf, &extension)) {
    DER_ITEM extension_id = {0};
    if (der_read_item(&extension.buf, &extension_id) &&
        extension_id.buf.size == extension_oid_size &&
        memcmp(extension_id.buf.data, extension_oid, extension_oid_size) == 0) {
      // Find the extension's extnValue, skipping the optional critical flag.
      while (der_read_item(&extension.buf, extension_value)) {
        if (extension_value->id == DER_OCTET_STRING) {
          return true;
        }
      }
      memzero(extension_value, sizeof(DER_ITEM));
      return false;
    }
  }
  return false;
}

static bool get_authority_key_digest(cli_t* cli, DER_ITEM* tbs_cert,
                                     const uint8_t** authority_key_digest) {
  DER_ITEM extensions = {0};
  if (!get_cert_extensions(tbs_cert, &extensions)) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, extensions not found.");
    return false;
  }

  // Find the authority key identifier extension's extnValue.
  DER_ITEM extension_value = {0};
  if (!get_extension_value(OID_AUTHORITY_KEY_IDENTIFIER,
                           sizeof(OID_AUTHORITY_KEY_IDENTIFIER), &extensions,
                           &extension_value)) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, authority key identifier extension "
              "not found.");
    return false;
  }

  // Open the AuthorityKeyIdentifier sequence.
  DER_ITEM auth_key_id = {0};
  if (!der_read_item(&extension_value.buf, &auth_key_id) ||
      auth_key_id.id != DER_SEQUENCE) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, failed to open authority key "
              "identifier extnValue.");
    return false;
  }

  // Find the keyIdentifier field.
  DER_ITEM key_id = {0};
  if (!der_read_item(&auth_key_id.buf, &key_id) ||
      key_id.id != DER_X509_KEY_IDENTIFIER) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, failed to find keyIdentifier field.");
    return false;
  }

  // Return the pointer to the keyIdentifier data.
  if (buffer_remaining(&key_id.buf) != SHA1_DIGEST_LENGTH ||
      !buffer_ptr(&key_id.buf, authority_key_digest)) {
    cli_error(cli, CLI_ERROR,
              "get_authority_key_digest, invalid length of keyIdentifier.");
    return false;
  }

  return true;
}

static bool get_common_name(DER_ITEM* name, const uint8_t** common_name,
                            size_t* common_name_size) {
  if (name->id != DER_SEQUENCE) {
    return false;
  }

  DER_ITEM distinguished_name = {0};
  if (!der_read_item(&name->buf, &distinguished_name) ||
      distinguished_name.id != DER_SET) {
    return false;
  }

  DER_ITEM attribute = {0};
  if (!der_read_item(&distinguished_name.buf, &attribute) ||
      attribute.id != DER_SEQUENCE) {
    return false;
  }

  DER_ITEM attribute_type = {0};
  if (!der_read_item(&attribute.buf, &attribute_type) ||
      attribute_type.buf.size != sizeof(OID_COMMON_NAME) ||
      memcmp(attribute_type.buf.data, OID_COMMON_NAME,
             sizeof(OID_COMMON_NAME)) != 0) {
    return false;
  }

  DER_ITEM attribute_value = {0};
  if (!der_read_item(&attribute.buf, &attribute_value) ||
      attribute_value.id != DER_UTF8_STRING) {
    return false;
  }

  if (!buffer_ptr(&attribute_value.buf, common_name)) {
    return false;
  }
  *common_name_size = buffer_remaining(&attribute_value.buf);

  return true;
}

static bool verify_signature(const uint8_t* pub_key, size_t pub_key_size,
                             const uint8_t* sig, size_t sig_size,
                             const uint8_t* msg, size_t msg_size) {
  // ECDSA (NIST P-256) with SHA-256
  if (pub_key_size != 65) {
    return false;
  }

  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  sha256_Raw(msg, msg_size, digest);

  uint8_t decoded_sig[64] = {0};
  if (ecdsa_sig_from_der(sig, sig_size, decoded_sig) != 0) {
    return false;
  }

  if (ecdsa_verify_digest(&nist256p1, pub_key, decoded_sig, digest) != 0) {
    return false;
  }

  return true;
}

bool check_cert_chain(cli_t* cli, const uint8_t* chain, size_t chain_size,
                      const uint8_t* sig, size_t sig_size,
                      const uint8_t challenge[CHALLENGE_SIZE]) {
  // Checks the integrity of the device certificate chain to ensure that the
  // certificate data was not corrupted in transport and that the device
  // certificate belongs to this device.
  // The certificate chain should contain two certificates:
  //   * the end-entity certificate (device certificate)
  //   * the intermediate CA certificate
  // THIS IS NOT A FULL VERIFICATION OF THE CERTIFICATE CHAIN.

  // This will be populated with a pointer to the key identifier data of the
  // AuthorityKeyIdentifier extension from the last certificate in the chain.
  const uint8_t* authority_key_digest = NULL;

  const uint8_t* message = challenge;
  size_t message_size = CHALLENGE_SIZE;

  const uint8_t* pub_key = NULL;
  size_t pub_key_size = 0;

  BUFFER_READER chain_reader = {0};
  buffer_reader_init(&chain_reader, chain, chain_size);
  int cert_count = 0;
  while (buffer_remaining(&chain_reader) > 0) {
    // Read the next certificate in the chain.
    cert_count += 1;
    DER_ITEM cert = {0};
    if (!der_read_item(&chain_reader, &cert) || cert.id != DER_SEQUENCE) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 1, cert %d.",
                cert_count);
      return false;
    }

    // Read the tbsCertificate.
    DER_ITEM tbs_cert = {0};
    if (!der_read_item(&cert.buf, &tbs_cert)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 2, cert %d.",
                cert_count);
      return false;
    }

    // Skip the version, serialNumber, signature, issuer and validity
    DER_ITEM der_item = {0};
    for (int i = 0; i < 5; ++i) {
      if (!der_read_item(&tbs_cert.buf, &der_item)) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, der_read_item 3, cert %d.",
                  cert_count);
        return false;
      }
    }

    // Read the subject.
    DER_ITEM subject = {0};
    if (!der_read_item(&tbs_cert.buf, &subject)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 4, cert %d.",
                cert_count);
      return false;
    }

    if (cert_count == 1) {
      // Check the common name of the subject of the device certificate.
      const uint8_t* common_name = NULL;
      size_t common_name_size = 0;
      if (!get_common_name(&subject, &common_name, &common_name_size) ||
          common_name_size != sizeof(SUBJECT_COMMON_NAME) ||
          memcmp(common_name, SUBJECT_COMMON_NAME,
                 sizeof(SUBJECT_COMMON_NAME)) != 0) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, invalid common name.");
        return false;
      }
    }

    // Read the Subject Public Key Info.
    DER_ITEM pub_key_info = {0};
    if (!der_read_item(&tbs_cert.buf, &pub_key_info)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, der_read_item 5, cert %d.",
                cert_count);
      return false;
    }

    // Read the public key.
    DER_ITEM pub_key_val = {0};
    uint8_t unused_bits = 0;
    for (int i = 0; i < 2; ++i) {
      if (!der_read_item(&pub_key_info.buf, &pub_key_val)) {
        cli_error(cli, CLI_ERROR,
                  "check_device_cert_chain, der_read_item 6, cert %d.",
                  cert_count);
        return false;
      }
    }

    if (!buffer_get(&pub_key_val.buf, &unused_bits) ||
        !buffer_ptr(&pub_key_val.buf, &pub_key)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, reading public key, cert %d.",
                cert_count);
      return false;
    }
    pub_key_size = buffer_remaining(&pub_key_val.buf);

    // Verify the previous signature.
    if (!verify_signature(pub_key, pub_key_size, sig, sig_size, message,
                          message_size)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, verify_signature, cert %d.",
                cert_count);
      return false;
    }

    // Get the authority key identifier from the last certificate.
    if (buffer_remaining(&chain_reader) == 0 &&
        !get_authority_key_digest(cli, &tbs_cert, &authority_key_digest)) {
      // Error returned by get_authority_key_digest().
      return false;
    }

    // Save tbsCertificate for the next signature verification.
    message = tbs_cert.buf.data;
    message_size = tbs_cert.buf.size;

    // Read the signatureAlgorithm and ensure it matches ECDSA_WITH_SHA256.
    DER_ITEM sig_alg = {0};
    if (!der_read_item(&cert.buf, &sig_alg) ||
        sig_alg.buf.size != sizeof(ECDSA_WITH_SHA256) ||
        memcmp(ECDSA_WITH_SHA256, sig_alg.buf.data,
               sizeof(ECDSA_WITH_SHA256)) != 0) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, checking signatureAlgorithm, cert "
                "%d.",
                cert_count);
      return false;
    }

    // Read the signature and save it for the next signature verification.
    DER_ITEM sig_val = {0};
    if (!der_read_item(&cert.buf, &sig_val) || sig_val.id != DER_BIT_STRING ||
        !buffer_get(&sig_val.buf, &unused_bits) || unused_bits != 0 ||
        !buffer_ptr(&sig_val.buf, &sig)) {
      cli_error(cli, CLI_ERROR,
                "check_device_cert_chain, reading signatureValue, cert %d.",
                cert_count);
      return false;
    }
    sig_size = buffer_remaining(&sig_val.buf);
  }

  // Verify that the signature of the last certificate in the chain matches
  // its own AuthorityKeyIdentifier to verify the integrity of the certificate
  // data.
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  sha256_Raw(message, message_size, digest);

  uint8_t decoded_sig[64] = {0};
  if (ecdsa_sig_from_der(sig, sig_size, decoded_sig) != 0) {
    cli_error(cli, CLI_ERROR,
              "check_device_cert_chain, ecdsa_sig_from_der root.");
    return false;
  }

  for (int recid = 0; recid < 4; ++recid) {
    uint8_t recovered_pub_key[65] = {0};
    if (ecdsa_recover_pub_from_sig(&nist256p1, recovered_pub_key, decoded_sig,
                                   digest, recid) == 0) {
      uint8_t pub_key_digest[SHA1_DIGEST_LENGTH] = {0};
      sha1_Raw(recovered_pub_key, sizeof(recovered_pub_key), pub_key_digest);
      if (memcmp(authority_key_digest, pub_key_digest,
                 sizeof(pub_key_digest)) == 0) {
        return true;
      }
    }
  }

  cli_error(cli, CLI_ERROR,
            "check_device_cert_chain, ecdsa_verify_digest root.");
  return false;
}
