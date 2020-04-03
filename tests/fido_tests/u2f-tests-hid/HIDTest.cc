// Copyright 2014 Google Inc. All rights reserved.
//
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file or at
// https://developers.google.com/open-source/licenses/bsd

// Basic U2F HID framing compliance test.

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <iostream>
#include <iomanip>

#include "u2f_util.h"

using namespace std;

int arg_Verbose = 0;  // default
bool arg_Pause = false;  // default
bool arg_Abort = true;  // default
bool arg_Time = false;  // default
float recvTimeout = 5.0;

static
void checkPause() {
  if (arg_Pause) {
    printf("\nPress any key to continue..");
    getchar();
    printf("\n");
  }
}

static
void AbortOrNot() {
  checkPause();
  if (arg_Abort) exit(3);
  cerr << "(continuing -a)" << endl;
}

struct U2Fob* device;

#define SEND(f) CHECK_EQ(0, U2Fob_sendHidFrame(device, &f))
#define RECV(f, t) CHECK_EQ(0, U2Fob_receiveHidFrame(device, &f, t))

// Initialize a frame with |len| random payload, or data.
void initFrame(U2FHID_FRAME* f, uint32_t cid, uint8_t cmd,
               size_t len, const void* data = NULL) {
  memset(f, 0, sizeof(U2FHID_FRAME));
  f->cid = cid;
  f->init.cmd = cmd | TYPE_INIT;
  f->init.bcnth = (uint8_t) (len >> 8);
  f->init.bcntl = (uint8_t) len;
  for (size_t i = 0; i < min(len, sizeof(f->init.data)); ++i) {
    f->init.data[i] = data ? ((const uint8_t*)data)[i] : (rand() & 255);
  }
}

// Initialize a continue frame
void contFrame(U2FHID_FRAME* f, uint32_t cid, uint8_t seqno, uint8_t val) {
  memset(f, val, sizeof(U2FHID_FRAME));
  f->cid = cid;
  f->cont.seq = seqno & ~TYPE_INIT;
}

// Return true if frame r is error frame for expected error.
bool isError(const U2FHID_FRAME r, int error) {
  return
      r.init.cmd == U2FHID_ERROR &&
      MSG_LEN(r) == 1 &&
      r.init.data[0] == error;
}

// Test basic INIT.
// Returns basic capabilities field.
uint8_t test_BasicInit() {
  U2FHID_FRAME f, r;
  initFrame(&f, U2Fob_getCid(device), U2FHID_INIT, INIT_NONCE_SIZE);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(r.init.cmd, U2FHID_INIT);
  CHECK_EQ(MSG_LEN(r), sizeof(U2FHID_INIT_RESP));
  CHECK_EQ(memcmp(&f.init.data[0], &r.init.data[0], INIT_NONCE_SIZE), 0);
  CHECK_EQ(r.init.data[12], U2FHID_IF_VERSION);
  return r.init.data[16];
}

// Test we have a working (single frame) echo.
void test_Echo() {
  U2FHID_FRAME f, r;
  uint64_t t = 0; U2Fob_deltaTime(&t);

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 8);

  U2Fob_deltaTime(&t);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  // Expect echo somewhat quickly.
  if (arg_Time)
    CHECK_LT(U2Fob_deltaTime(&t), .1);

  // Check echoed content matches.
  CHECK_EQ(U2FHID_PING, r.init.cmd);
  CHECK_EQ(MSG_LEN(f), MSG_LEN(r));
  CHECK_EQ(0, memcmp(f.init.data, r.init.data, MSG_LEN(f)));
}

// Test we can echo message larger than a single frame.
void test_LongEcho() {
  const size_t TESTSIZE = 1024;
  uint8_t challenge[TESTSIZE];
  uint8_t response[TESTSIZE];
  uint8_t cmd = U2FHID_PING;

  for (size_t i = 0; i < sizeof(challenge); ++i) challenge[i] = rand();

  uint64_t t = 0; U2Fob_deltaTime(&t);

  CHECK_EQ(0, U2Fob_send(device, cmd, challenge, sizeof(challenge)));

  float sent = U2Fob_deltaTime(&t);

  CHECK_EQ(sizeof(response),
           U2Fob_recv(device, &cmd, response, sizeof(response), 2.0));

  float received = U2Fob_deltaTime(&t);

  CHECK_EQ(cmd, U2FHID_PING);
  CHECK_EQ(0, memcmp(challenge, response, sizeof(challenge)));

  INFO << "sent: " << sent << ", received: " << received;

  // Expected transfer times for 2ms bInterval.
  // We do not want fobs to be too slow or too agressive.
  if (device->dev != NULL && arg_Time) {
    CHECK_GE(sent, .020);
    CHECK_LE(sent, .075);
    CHECK_GE(received, .020);
    CHECK_LE(received, .075);
  }
}

// Execute WINK, if implemented.
// Visually inspect fob for compliance.
void test_OptionalWink() {
  U2FHID_FRAME f, r;
  uint8_t caps = test_BasicInit();

  initFrame(&f, U2Fob_getCid(device), U2FHID_WINK, 0);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  if (caps & CAPFLAG_WINK) {
    CHECK_EQ(f.init.cmd, r.init.cmd);
    CHECK_EQ(MSG_LEN(r), 0);
  } else {
    CHECK_EQ(isError(r, ERR_INVALID_CMD), true);
  }
}

// Test max data size limit enforcement.
// We try echo 7610 bytes.
// Device should pre-empt communications with error reply.
void test_Limits() {
  U2FHID_FRAME f, r;
  uint64_t t = 0; U2Fob_deltaTime(&t);

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 7610);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(isError(r, ERR_INVALID_LEN), true);
}

// Check there are no frames pending for this cid.
// Poll for a frame with short timeout.
// Make sure none got received and timeout time passed.
void test_Idle(float timeOut = .3) {
  U2FHID_FRAME r;
  uint64_t t = 0; U2Fob_deltaTime(&t);

  U2Fob_deltaTime(&t);
  CHECK_EQ(-ERR_MSG_TIMEOUT, U2Fob_receiveHidFrame(device, &r, timeOut));
  CHECK_GE(U2Fob_deltaTime(&t), .2);
  CHECK_LE(U2Fob_deltaTime(&t), .5);
}

// Check we get a timeout error frame if not sending TYPE_CONT frames
// for a message that spans multiple frames.
// Device should timeout at ~.5 seconds.
void test_Timeout() {
  U2FHID_FRAME f, r;
  float measuredTimeout;
  uint64_t t = 0; U2Fob_deltaTime(&t);

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 99);

  U2Fob_deltaTime(&t);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(isError(r, ERR_MSG_TIMEOUT), true);

  measuredTimeout = U2Fob_deltaTime(&t);

  INFO << "measured timeout: " << measuredTimeout;
  CHECK_GE(measuredTimeout, .4);  // needs to be at least 0.4 seconds
  if (arg_Time)
    CHECK_LE(measuredTimeout, 1.0);  // but at most 1.0 seconds
}

// Test LOCK functionality, if implemented.
void test_Lock() {
  U2FHID_FRAME f, r;
  uint64_t t = 0; U2Fob_deltaTime(&t);
  uint8_t caps = test_BasicInit();

  // Check whether lock is supported using an unlock command.
  initFrame(&f, U2Fob_getCid(device), U2FHID_LOCK, 1, "\x00");
  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  if (!(caps & CAPFLAG_LOCK)) {
    // Make sure CAPFLAG reflects behavior.
    CHECK_EQ(isError(r, ERR_INVALID_CMD), true);
    return;
  }

  // Lock channel for 3 seconds.
  initFrame(&f, U2Fob_getCid(device), U2FHID_LOCK, 1, "\x03");

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(f.init.cmd, r.init.cmd);
  CHECK_EQ(0, MSG_LEN(r));

  // Rattle lock, checking for BUSY.
  int count = 0;
  do {
    // The requested channel timeout (3 seconds) resets
    // after every message, so we only send a couple of
    // messages down the channel in this loop. Otherwise
    // the lock would never expire.
    if (++count < 2) test_Echo();
    usleep(100000);
    initFrame(&f, U2Fob_getCid(device) ^ 1, U2FHID_PING, 1);

    SEND(f);
    RECV(r, recvTimeout);
    CHECK_EQ(f.cid, r.cid);

    if (r.init.cmd == U2FHID_ERROR) {
      // We only expect BUSY here.
      CHECK_EQ(isError(r, ERR_CHANNEL_BUSY), true);
    }
  } while (r.init.cmd == U2FHID_ERROR);

  CHECK_GE(U2Fob_deltaTime(&t), 2.5);
}

// Check we get abort if we send TYPE_INIT when TYPE_CONT is expected.
void test_NotCont() {
  U2FHID_FRAME f, r;
  uint64_t t = 0; U2Fob_deltaTime(&t);

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 99);  // Note 99 > frame.

  SEND(f);

  SEND(f);  // Send frame again, i.e. another TYPE_INIT frame.
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  if (arg_Time)
    CHECK_LT(U2Fob_deltaTime(&t), .1);  // Expect fail reply quickly.

  CHECK_EQ(isError(r, ERR_INVALID_SEQ), true);

  // Check there are no further messages.
  CHECK_EQ(-ERR_MSG_TIMEOUT, U2Fob_receiveHidFrame(device, &r, 0.6f));
}

// Check we get a error when sending wrong sequence in continuation frame.
void test_WrongSeq() {
  U2FHID_FRAME f, r;
  uint64_t t = 0; U2Fob_deltaTime(&t);

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 99);

  SEND(f);

  f.cont.seq = 1 | TYPE_CONT;  // Send wrong SEQ, 0 is expected.

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  if (arg_Time)
    CHECK_LT(U2Fob_deltaTime(&t), .1);  // Expect fail reply quickly.

  CHECK_EQ(isError(r, ERR_INVALID_SEQ), true);

  // Check there are no further messages.
  CHECK_EQ(-ERR_MSG_TIMEOUT, U2Fob_receiveHidFrame(device, &r, 0.6f));
}

// Check we hear nothing if we send a random CONT frame.
void test_NotFirst() {
  U2FHID_FRAME f, r;

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 8);
  f.cont.seq = 0 | TYPE_CONT;  // Make continuation packet.

  SEND(f);
  CHECK_EQ(-ERR_MSG_TIMEOUT, U2Fob_receiveHidFrame(device, &r, 1.0));
}

// Check we get a BUSY if device is waiting for CONT on other channel.
void test_Busy() {
  U2FHID_FRAME f, r;
  uint64_t t = 0; U2Fob_deltaTime(&t);

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 99);

  SEND(f);

  f.cid ^= 1;  // Flip channel.

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  if (arg_Time)
    CHECK_LT(U2Fob_deltaTime(&t), .1);  // Expect busy reply quickly.

  CHECK_EQ(isError(r, ERR_CHANNEL_BUSY), true);

  f.cid ^= 1;  // Flip back.

  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(isError(r, ERR_MSG_TIMEOUT), true);

  CHECK_GE(U2Fob_deltaTime(&t), .45);  // Expect T/O msg only after timeout.
}

// Check that fob ignores CONT frame for different cid.
void test_Interleave() {
  U2FHID_FRAME f, r;
  uint64_t t = 0; U2Fob_deltaTime(&t);
  uint32_t cid0 = U2Fob_getCid(device);
  uint32_t cid1 = U2Fob_getCid(device) ^ 1;
  uint8_t expected;

  // Start a 2 frame request on cid 0
  initFrame(&f, cid0, U2FHID_PING, sizeof(f.cont.data) + sizeof(f.init.data));
  expected = f.init.data[0];
  SEND(f);

  // Interleave a 2 frame request on cid 1
  initFrame(&f, cid1, U2FHID_PING, sizeof(f.cont.data) + sizeof(f.init.data));
  SEND(f);
  contFrame(&f, cid1, 0, expected ^ 1);
  SEND(f);

  // Then send 2nd frame on cid 0
  contFrame(&f, cid0, 0, expected);
  SEND(f);

  // Expect CHANNEL_BUSY for  cid 1
  RECV(r, recvTimeout);
  CHECK_EQ(r.cid, cid1);
  CHECK_EQ(isError(r, ERR_CHANNEL_BUSY), true);

  // Expect correct 2 frame reply for cid 0
  RECV(r, recvTimeout);
  CHECK_EQ(r.cid, cid0);
  CHECK_EQ(r.init.data[0], expected);
  RECV(r, recvTimeout);
  CHECK_EQ(r.cid, cid0);
  CHECK_EQ(r.cont.data[1], expected);

  // Expect nothing left to receive
  CHECK_EQ(-ERR_MSG_TIMEOUT, U2Fob_receiveHidFrame(device, &r, .5));
}

// Test INIT self aborts wait for CONT frame
void test_InitSelfAborts() {
  U2FHID_FRAME f, r;

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 99);
  SEND(f);

  initFrame(&f, U2Fob_getCid(device), U2FHID_INIT, INIT_NONCE_SIZE);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(r.init.cmd, U2FHID_INIT);
  CHECK_GE(MSG_LEN(r), MSG_LEN(f));
  CHECK_EQ(memcmp(&f.init.data[0], &r.init.data[0], INIT_NONCE_SIZE), 0);

  test_NotFirst();
}

// Test INIT other does not abort wait for CONT.
void test_InitOther() {
  U2FHID_FRAME f, f2, r;

  initFrame(&f, U2Fob_getCid(device), U2FHID_PING, 99);
  SEND(f);

  initFrame(&f2, U2Fob_getCid(device) ^ 1, U2FHID_INIT, INIT_NONCE_SIZE);

  SEND(f2);
  RECV(r, recvTimeout);
  CHECK_EQ(f2.cid, r.cid);

  // Expect sync reply for requester
  CHECK_EQ(r.init.cmd, U2FHID_INIT);
  CHECK_GE(MSG_LEN(r), MSG_LEN(f2));
  CHECK_EQ(memcmp(&f2.init.data[0], &r.init.data[0], INIT_NONCE_SIZE), 0);

  // Expect error frame after timeout on first channel.
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(isError(r, ERR_MSG_TIMEOUT), true);
}

void wait_Idle() {
  U2FHID_FRAME r;

  while (-ERR_MSG_TIMEOUT != U2Fob_receiveHidFrame(device, &r, .2f)) {
  }
}

void test_LeadingZero() {
  U2FHID_FRAME f, r;
  initFrame(&f, 0x100, U2FHID_PING, 10);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(r.cid, f.cid);

  CHECK_EQ(r.init.cmd, U2FHID_PING);
  CHECK_EQ(MSG_LEN(f), MSG_LEN(r));
}

void test_InitOnNonBroadcastEchoesCID() {
  U2FHID_FRAME f, r;
  size_t cs = INIT_NONCE_SIZE;

  initFrame(&f, 0xdeadbeef, U2FHID_INIT, cs);  // Use non-broadcast cid

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(r.cid, f.cid);

  CHECK_EQ(r.init.cmd, U2FHID_INIT);
  CHECK_EQ(MSG_LEN(r), sizeof(U2FHID_INIT_RESP));
  CHECK_EQ(0, memcmp(f.init.data, r.init.data, cs));

  uint32_t cid =
      (r.init.data[cs + 0] << 24) |
      (r.init.data[cs + 1] << 16) |
      (r.init.data[cs + 2] << 8) |
      (r.init.data[cs + 3] << 0);

  CHECK_EQ(cid, 0xdeadbeef);
}

uint32_t test_Init(bool check = true) {
  U2FHID_FRAME f, r;
  size_t cs = INIT_NONCE_SIZE;

  initFrame(&f, -1, U2FHID_INIT, cs);  // -1 is broadcast channel

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(r.cid, f.cid);

  // expect init reply
  CHECK_EQ(r.init.cmd, U2FHID_INIT);

  CHECK_EQ(MSG_LEN(r), sizeof(U2FHID_INIT_RESP));

  // Check echo of challenge
  CHECK_EQ(0, memcmp(f.init.data, r.init.data, cs));

  uint32_t cid =
      (r.init.data[cs + 0] << 0) |
      (r.init.data[cs + 1] << 8) |
      (r.init.data[cs + 2] << 16) |
      (r.init.data[cs + 3] << 24);

  if (check) {
    // Check that another INIT yields a distinct cid.
    CHECK_NE(test_Init(false), cid);
  }

  return cid;
}

void test_InitUnderLock() {
  U2FHID_FRAME f, r;
  uint8_t caps = test_BasicInit();

  // Check whether lock is supported, using an unlock command.
  initFrame(&f, U2Fob_getCid(device), U2FHID_LOCK, 1, "\x00");  // unlock

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  if (!(caps & CAPFLAG_LOCK)) {
    // Make sure CAPFLAG reflects behavior.
    CHECK_EQ(isError(r, ERR_INVALID_CMD), true);
    return;
  }

  initFrame(&f, U2Fob_getCid(device), U2FHID_LOCK, 1, "\x03");  // 3 seconds

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(f.init.cmd, r.init.cmd);
  CHECK_EQ(0, MSG_LEN(r));

  // We have a lock. CMD_INIT should work whilst another holds lock.

  test_Init(false);
  test_InitOnNonBroadcastEchoesCID();

  // Unlock.
  initFrame(&f, U2Fob_getCid(device), U2FHID_LOCK, 1, "\x00");

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(f.init.cmd, r.init.cmd);
  CHECK_EQ(0, MSG_LEN(r));
}

void test_Unknown(uint8_t cmd) {
  U2FHID_FRAME f, r;

  initFrame(&f, U2Fob_getCid(device), cmd, 0);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(isError(r, ERR_INVALID_CMD), true);
}

void test_OnlyInitOnBroadcast() {
  U2FHID_FRAME f, r;

  initFrame(&f, -1, U2FHID_PING, INIT_NONCE_SIZE);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(isError(r, ERR_INVALID_CID), true);
}

void test_NothingOnChannel0() {
  U2FHID_FRAME f, r;

  initFrame(&f, 0, U2FHID_INIT, INIT_NONCE_SIZE);

  SEND(f);
  RECV(r, recvTimeout);
  CHECK_EQ(f.cid, r.cid);

  CHECK_EQ(isError(r, ERR_INVALID_CID), true);
}

int main(int argc, char* argv[]) {
  if (argc < 2) {
    cerr << "Usage: " << argv[0]
         << " <device-path> [-a] [-v] [-V] [-p] [-t]" << endl;
    return -1;
  }

  device = U2Fob_create();

  char* arg_DeviceName = argv[1];

  while (--argc > 1) {
    if (!strncmp(argv[argc], "-v", 2)) {
      // INFO only
      arg_Verbose |= 1;
    }
    if (!strncmp(argv[argc], "-V", 2)) {
      // All logging
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
    if (!strncmp(argv[argc], "-t", 2)) {
      // Strict timing checks
      arg_Time = true;
      recvTimeout = 1.0;
    }
  }

  srand((unsigned int) time(NULL));

  // Start of tests
  //
  CHECK_EQ(U2Fob_open(device, arg_DeviceName), 0);

  PASS(test_Idle());

  PASS(test_Init());

  // Now that we have INIT, get a proper cid for device.
  CHECK_EQ(U2Fob_init(device), 0);

  PASS(test_BasicInit());

  PASS(test_Unknown(U2FHID_SYNC));

  PASS(test_InitOnNonBroadcastEchoesCID());
  PASS(test_InitUnderLock());
  PASS(test_InitSelfAborts());
  PASS(test_InitOther());

  PASS(test_OptionalWink());

  PASS(test_Lock());

  PASS(test_Echo());
  PASS(test_LongEcho());

  PASS(test_Timeout());

  PASS(test_WrongSeq());
  PASS(test_NotCont());
  PASS(test_NotFirst());

  PASS(test_Limits());

  PASS(test_Busy());
  PASS(test_Interleave());
  PASS(test_LeadingZero());

  PASS(test_Idle(2.0));

  PASS(test_NothingOnChannel0());
  PASS(test_OnlyInitOnBroadcast());

  U2Fob_destroy(device);

  return 0;
}
