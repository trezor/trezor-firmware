// Copyright 2014 Google Inc. All rights reserved.
//
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file or at
// https://developers.google.com/open-source/licenses/bsd

// U2F register / sign compliance test.

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <iostream>
#include <iomanip>

#ifdef __OS_WIN
#include <winsock2.h>  // ntohl, htonl
#else
#include <arpa/inet.h>  // ntohl, htonl
#endif

#include "u2f.h"
#include "u2f_util.h"

#include "dsa_sig.h"
#include "p256.h"
#include "p256_ecdsa.h"
#include "sha256.h"

using namespace std;

int arg_Verbose = 0;  // default
bool arg_Pause = false;  // default
bool arg_Abort = true;  // default

static
void pause(const string& prompt) {
  printf("\n%s", prompt.c_str());
  getchar();
  printf("\n");
}

static
void checkPause(const string& prompt) {
  if (arg_Pause) pause(prompt);
}

static
void AbortOrNot() {
  checkPause("Hit enter to continue..");
  if (arg_Abort) exit(3);
  cerr << "(continuing -a)" << endl;
}

void WaitForUserPresence(struct U2Fob* device, bool hasButton) {
  int touched = DEV_touch(device);
  U2Fob_close(device);
  if (!touched) {
    pause(string(hasButton ? "Touch" : "Re-insert") + " device and hit enter..");
  }
  CHECK_EQ(0, U2Fob_reopen(device));
  CHECK_EQ(0, U2Fob_init(device));
}

struct U2Fob* device;

U2F_REGISTER_REQ regReq;
U2F_REGISTER_RESP regRsp;
U2F_AUTHENTICATE_REQ authReq;

void test_Version() {
  string rsp;
  int res = U2Fob_apdu(device, 0, U2F_INS_VERSION, 0, 0, "", &rsp);
  if (res == 0x9000) {
    CHECK_EQ(rsp, "U2F_V2");
    return;
  }

  // Non-ISO 7816-4 compliant U2F_INS_VERSION "APDU" that includes Lc value 0,
  // for compatibility with older devices.
  uint8_t buf[4 + 3 + 2];
  buf[0] = 0;  // CLA
  buf[1] = U2F_INS_VERSION;  // INS
  buf[2] = 0;  // P1
  buf[3] = 0;  // P2
  buf[4] = 0;  // extended length
  buf[5] = 0;  // Lc = 0 (Not ISO 7816-4 compliant)
  buf[6] = 0;  // Lc = 0 (Not ISO 7816-4 compliant)
  buf[7] = 0;  // Le = 0
  buf[8] = 0;  // Le = 0
  CHECK_EQ(0x9000, U2Fob_exchange_apdu_buffer(device, buf, sizeof(buf), &rsp));
  CHECK_EQ(rsp, "U2F_V2");
}

void test_UnknownINS() {
  string rsp;
  CHECK_EQ(0x6D00, U2Fob_apdu(device, 0, 0 /* not U2F INS */,
                              0, 0, "", &rsp));
  CHECK_EQ(rsp.empty(), true);
}

void test_BadCLA() {
  string rsp;
  CHECK_EQ(0x6E00, U2Fob_apdu(device, 1 /* not U2F CLA, 0x00 */,
                              U2F_INS_VERSION, 0, 0, "abc", &rsp));
  CHECK_EQ(rsp.empty(), true);
}

void test_WrongLength_U2F_VERSION() {
  string rsp;
  // U2F_VERSION does not take any input.
  CHECK_EQ(0x6700, U2Fob_apdu(device, 0, U2F_INS_VERSION, 0, 0, "abc", &rsp));
  CHECK_EQ(rsp.empty(), true);
}

void test_WrongLength_U2F_REGISTER() {
  string rsp;
  // U2F_REGISTER does expect input.
  CHECK_EQ(0x6700, U2Fob_apdu(device, 0, U2F_INS_REGISTER, 0, 0, "abc", &rsp));
  CHECK_EQ(rsp.empty(), true);
}

void test_Enroll(int expectedSW12 = 0x9000) {
  uint64_t t = 0; U2Fob_deltaTime(&t);

  string rsp;
  CHECK_EQ(expectedSW12,
           U2Fob_apdu(device, 0, U2F_INS_REGISTER, U2F_AUTH_ENFORCE, 0,
                      string(reinterpret_cast<char*>(&regReq),
                             sizeof(regReq)),
                      &rsp));

  if (expectedSW12 != 0x9000) {
    CHECK_EQ(true, rsp.empty());
    return;
  }

  CHECK_NE(rsp.empty(), true);
  CHECK_LE(rsp.size(), sizeof(U2F_REGISTER_RESP));

  memcpy(&regRsp, rsp.data(), rsp.size());

  CHECK_EQ(regRsp.registerId, U2F_REGISTER_ID);
  CHECK_EQ(regRsp.pubKey.format, UNCOMPRESSED_POINT);

  INFO << "Enroll: " << rsp.size() << " bytes in "
       << U2Fob_deltaTime(&t) << "s";

  // Check crypto of enroll response.
  string cert;
  CHECK_EQ(getCertificate(regRsp, &cert), true);
  INFO << "cert: " << b2a(cert);

  string pk;
  CHECK_EQ(getSubjectPublicKey(cert, &pk), true);
  INFO << "pk  : " << b2a(pk);

  string sig;
  CHECK_EQ(getSignature(regRsp, &sig), true);
  INFO << "sig : " << b2a(sig);

  // Parse signature into two integers.
  p256_int sig_r, sig_s;
  CHECK_EQ(1, dsa_sig_unpack((uint8_t*) (sig.data()), sig.size(),
                             &sig_r, &sig_s));

  // Compute hash as integer.
  p256_int h;
  SHA256_CTX sha;
  SHA256_init(&sha);
  uint8_t rfu = 0;
  SHA256_update(&sha, &rfu, sizeof(rfu));  // 0x00
  SHA256_update(&sha, regReq.appId, sizeof(regReq.appId));  // O
  SHA256_update(&sha, regReq.nonce, sizeof(regReq.nonce));  // d
  SHA256_update(&sha, regRsp.keyHandleCertSig, regRsp.keyHandleLen);  // hk
  SHA256_update(&sha, &regRsp.pubKey, sizeof(regRsp.pubKey));  // pk
  p256_from_bin(SHA256_final(&sha), &h);

  // Parse subject public key into two integers.
  CHECK_EQ(pk.size(), P256_POINT_SIZE);
  p256_int pk_x, pk_y;
  p256_from_bin((uint8_t*) pk.data() + 1, &pk_x);
  p256_from_bin((uint8_t*) pk.data() + 1 + P256_SCALAR_SIZE, &pk_y);

  // Verify signature.
  CHECK_EQ(1, p256_ecdsa_verify(&pk_x, &pk_y, &h, &sig_r, &sig_s));

#if 0
  // Check for standard U2F self-signed certificate.
  // Implementations without batch attestation should use this minimalist
  // self-signed certificate for enroll.
  // Conforming to a standard self-signed certficate format and attributes
  // bins all such fobs into a single large batch, which helps privacy.
  string selfSigned = a2b(
      "3081B3A003020102020101300A06082A8648CE3D040302300E310C300A060355040A0C035532463022180F32303030303130313030303030305A180F32303939313233313233353935395A300E310C300A060355040313035532463059301306072A8648CE3D020106082A8648CE3D030107034200") + pk;

  SHA256_init(&sha);
  SHA256_update(&sha, selfSigned.data(), selfSigned.size());
  p256_from_bin(SHA256_final(&sha), &h);

  string certSig;
  CHECK_EQ(getCertSignature(cert, &certSig), true);
  INFO << "certSig : " << b2a(certSig);

  CHECK_EQ(1, dsa_sig_unpack((uint8_t*) (certSig.data()), certSig.size(),
                             &sig_r, &sig_s));
  // Verify cert signature.
  CHECK_EQ(1, p256_ecdsa_verify(&pk_x, &pk_y, &h, &sig_r, &sig_s));
#endif
}

// returns ctr
uint32_t test_Sign(int expectedSW12 = 0x9000, bool checkOnly = false) {
  memcpy(authReq.appId, regReq.appId, sizeof(authReq.appId));
  authReq.keyHandleLen = regRsp.keyHandleLen;
  memcpy(authReq.keyHandle, regRsp.keyHandleCertSig, authReq.keyHandleLen);

  uint64_t t = 0; U2Fob_deltaTime(&t);

  string rsp;
  CHECK_EQ(expectedSW12,
           U2Fob_apdu(device, 0, U2F_INS_AUTHENTICATE,
                      checkOnly ? U2F_AUTH_CHECK_ONLY : U2F_AUTH_ENFORCE, 0,
                      string(reinterpret_cast<char*>(&authReq),
                             U2F_NONCE_SIZE + U2F_APPID_SIZE + 1 +
                             authReq.keyHandleLen),
                      &rsp));

  if (expectedSW12 != 0x9000) {
    CHECK_EQ(true, rsp.empty());
    return 0;
  }

  CHECK_NE(rsp.empty(), true);
  CHECK_LE(rsp.size(), sizeof(U2F_AUTHENTICATE_RESP));

  U2F_AUTHENTICATE_RESP resp;
  memcpy(&resp, rsp.data(), rsp.size());

  CHECK_EQ(resp.flags, 0x01);

  INFO << "Sign: " << rsp.size() << " bytes in "
       << U2Fob_deltaTime(&t) << "s";

  // Parse signature from authenticate response.
  p256_int sig_r, sig_s;
  CHECK_EQ(1, dsa_sig_unpack(resp.sig,
                             rsp.size() - sizeof(resp.flags) - sizeof(resp.ctr),
                             &sig_r, &sig_s));

  // Compute hash as integer.
  p256_int h;
  SHA256_CTX sha;
  SHA256_init(&sha);
  SHA256_update(&sha, regReq.appId, sizeof(regReq.appId));  // O
  SHA256_update(&sha, &resp.flags, sizeof(resp.flags));  // T
  SHA256_update(&sha, &resp.ctr, sizeof(resp.ctr));  // CTR
  SHA256_update(&sha, authReq.nonce, sizeof(authReq.nonce));  // d
  p256_from_bin(SHA256_final(&sha), &h);

  // Parse public key from registration response.
  p256_int pk_x, pk_y;
  p256_from_bin(regRsp.pubKey.x, &pk_x);
  p256_from_bin(regRsp.pubKey.y, &pk_y);

  // Verify signature.
  CHECK_EQ(1, p256_ecdsa_verify(&pk_x, &pk_y, &h, &sig_r, &sig_s));

  return ntohl(resp.ctr);
}

void check_Compilation() {
  // Couple of sanity checks.
  CHECK_EQ(sizeof(P256_POINT), 65);
  CHECK_EQ(sizeof(U2F_REGISTER_REQ), 64);
}


int main(int argc, char* argv[]) {
  if (argc < 2) {
    cerr << "Usage: " << argv[0]
         << " <device-path> [-a] [-v] [-V] [-p] [-b]" << endl;
    return -1;
  }

  device = U2Fob_create();

  char* arg_DeviceName = argv[1];
  bool arg_hasButton = true;  // fob has button

  while (--argc > 1) {
    if (!strncmp(argv[argc], "-v", 2)) {
      // Log INFO.
      arg_Verbose |= 1;
    }
    if (!strncmp(argv[argc], "-V", 2)) {
      // Log everything.
      arg_Verbose |= 2;
      U2Fob_setLog(device, stdout, -1);
    }
    if (!strncmp(argv[argc], "-a", 2)) {
      // Don't abort, try continue;
      arg_Abort = false;
    }
    if (!strncmp(argv[argc], "-p", 2)) {
      // Pause at abort
      arg_Pause = true;
    }
    if (!strncmp(argv[argc], "-b", 2)) {
      // Fob does not have button
      arg_hasButton = false;
    }
  }

  srand((unsigned int) time(NULL));

  CHECK_EQ(0, U2Fob_open(device, arg_DeviceName));
  CHECK_EQ(0, U2Fob_init(device));

  PASS(check_Compilation());

  PASS(test_Version());
  PASS(test_UnknownINS());
  PASS(test_WrongLength_U2F_VERSION());
  PASS(test_WrongLength_U2F_REGISTER());
  PASS(test_BadCLA());

  // pick random origin and challenge.
  for (size_t i = 0; i < sizeof(regReq.nonce); ++i)
      regReq.nonce[i] = rand();
  for (size_t i = 0; i < sizeof(regReq.appId); ++i)
      regReq.appId[i] = rand();

  // Fob with button should need touch.
  if (arg_hasButton) PASS(test_Enroll(0x6985));

  WaitForUserPresence(device, arg_hasButton);

  PASS(test_Enroll(0x9000));

  // pick random challenge and use registered appId.
  for (size_t i = 0; i < sizeof(authReq.nonce); ++i)
      authReq.nonce[i] = rand();

  // Fob with button should have consumed touch.
  if (arg_hasButton) PASS(test_Sign(0x6985));

  // Sign with check only should not produce signature.
  PASS(test_Sign(0x6985, true));

  // Sign with wrong hk.
  regRsp.keyHandleCertSig[0] ^= 0x55;
  PASS(test_Sign(0x6a80));
  regRsp.keyHandleCertSig[0] ^= 0x55;

  // Sign with wrong appid.
  regReq.appId[0] ^= 0xaa;
  PASS(test_Sign(0x6a80));
  regReq.appId[0] ^= 0xaa;

  WaitForUserPresence(device, arg_hasButton);

  // Sign with check only should not produce signature.
  PASS(test_Sign(0x6985, true));

  uint32_t ctr1;
  PASS(ctr1 = test_Sign(0x9000));
  PASS(test_Sign(0x6985));

  WaitForUserPresence(device, arg_hasButton);

  uint32_t ctr2;
  PASS(ctr2 = test_Sign(0x9000));

  // Ctr should have incremented by 1.
  CHECK_EQ(ctr2, ctr1 + 1);

  regRsp.keyHandleLen -= 8; // perturb keyhandle length
  PASS(test_Sign(0x6a80, false));

  U2Fob_destroy(device);
  return 0;
}
