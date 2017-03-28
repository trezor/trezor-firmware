#ifndef ED25519_H
#define ED25519_H

#if defined(__cplusplus)
extern "C" {
#endif

typedef unsigned char ed25519_signature[64];
typedef unsigned char ed25519_public_key[32];
typedef unsigned char ed25519_secret_key[32];

typedef unsigned char curve25519_key[32];

void ed25519_publickey(const ed25519_secret_key sk, ed25519_public_key pk);
int ed25519_sign_open(const unsigned char *m, size_t mlen, const ed25519_public_key pk, const ed25519_signature RS);
void ed25519_sign(const unsigned char *m, size_t mlen, const ed25519_secret_key sk, const ed25519_public_key pk, ed25519_signature RS);

void curve25519_scalarmult(curve25519_key mypublic, const curve25519_key secret, const curve25519_key basepoint);
void curve25519_scalarmult_basepoint(curve25519_key mypublic, const curve25519_key secret);

#if defined(__cplusplus)
}
#endif

#endif // ED25519_H
