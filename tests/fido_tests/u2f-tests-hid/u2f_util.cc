// Copyright 2014 Google Inc. All rights reserved.
//
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file or at
// https://developers.google.com/open-source/licenses/bsd

#include <stdlib.h>
#include <string.h>

#ifdef __OS_WIN
#include <winsock2.h>  // ntohl, htonl
#else
#include <arpa/inet.h>  // ntohl, htonl
#endif

#include <string>

#include "u2f_util.h"

// This is a "library"; do not abort.
#define AbortOrNot()                           \
  std::cerr << "returning false" << std::endl; \
  return false

#ifdef __OS_WIN
#define strdup _strdup
#endif

#ifdef __OS_MAC
// Implement something compatible w/ linux clock_gettime()

#include <mach/mach_time.h>

#define CLOCK_MONOTONIC 0

static void clock_gettime(int which, struct timespec* ts) {
  static mach_timebase_info_data_t __clock_gettime_inf;
  uint64_t now, nano;

  now = mach_absolute_time();
  if (0 == __clock_gettime_inf.denom) mach_timebase_info(&__clock_gettime_inf);

  nano = now * __clock_gettime_inf.numer / __clock_gettime_inf.denom;
  ts->tv_sec = nano * 1e-9;
  ts->tv_nsec = nano - (ts->tv_sec * 1e9);
}
#endif  // __OS_MAC

std::string b2a(const void* ptr, size_t size) {
  const uint8_t* p = reinterpret_cast<const uint8_t*>(ptr);
  std::string result;

  for (size_t i = 0; i < 2 * size; ++i) {
    int nib = p[i / 2];
    if ((i & 1) == 0) nib >>= 4;
    nib &= 15;
    result.push_back("0123456789ABCDEF"[nib]);
  }

  return result;
}

std::string b2a(const std::string& s) { return b2a(s.data(), s.size()); }

std::string a2b(const std::string& s) {
  std::string result;
  int v;
  for (size_t i = 0; i < s.size(); ++i) {
    if ((i & 1) == 1)
      v <<= 4;
    else
      v = 0;
    char d = s[i];
    if (d >= '0' && d <= '9')
      v += (d - '0');
    else if (d >= 'A' && d <= 'F')
      v += (d - 'A' + 10);
    else if (d >= 'a' && d <= 'f')
      v += (d - 'a' + 10);
    if ((i & 1) == 1) result.push_back(v & 255);
  }
  return result;
}

float U2Fob_deltaTime(uint64_t* state) {
  uint64_t now, delta;
#ifdef __OS_WIN
  now = (uint64_t)GetTickCount64() * 1000000;
#else
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  now = (uint64_t)(ts.tv_sec * 1e9 + ts.tv_nsec);
#endif
  delta = *state ? now - *state : 0;
  *state = now;
  return (float)(delta / 1.0e9);
}

struct U2Fob* U2Fob_create() {
  struct U2Fob* f = NULL;
  if (hid_init() == 0) {
    f = (struct U2Fob*)malloc(sizeof(struct U2Fob));
    memset(f, 0, sizeof(struct U2Fob));
    f->cid = -1;
  }
  return f;
}

void U2Fob_destroy(struct U2Fob* device) {
  if (device) {
    U2Fob_close(device);
    if (device->path) {
      free(device->path);
      device->path = NULL;
    }
    free(device);
  }
  hid_exit();
}

uint32_t U2Fob_getCid(struct U2Fob* device) { return device->cid; }

int U2Fob_open(struct U2Fob* device, const char* path) {
  U2Fob_close(device);
  if (device->path) {
    free(device->path);
    device->path = NULL;
  }
  device->path = strdup(path);
  DEV_open_path(device);
  return DEV_opened(device) ? -ERR_NONE : -ERR_OTHER;
}

void U2Fob_close(struct U2Fob* device) { DEV_close(device); }

int U2Fob_reopen(struct U2Fob* device) {
  U2Fob_close(device);
  DEV_open_path(device);
  return DEV_opened(device) ? -ERR_NONE : -ERR_OTHER;
}

void U2Fob_setLog(struct U2Fob* device, FILE* fd, int level) {
  device->logfp = fd;
  device->loglevel = level;
  device->logtime = 0;
  U2Fob_deltaTime(&device->logtime);
}

static void U2Fob_logFrame(struct U2Fob* device, const char* tag,
                           const U2FHID_FRAME* f) {
  if (device->logfp) {
    fprintf(device->logfp, "t+%.3f", U2Fob_deltaTime(&device->logtime));
    fprintf(device->logfp, "%s %08x:%02x", tag, f->cid, f->type);
    if (f->type & TYPE_INIT) {
      int len = f->init.bcnth * 256 + f->init.bcntl;
      fprintf(device->logfp, "[%d]:", len);
      for (size_t i = 0; i < sizeof(f->init.data); ++i)
        fprintf(device->logfp, "%02X", f->init.data[i]);
    } else {
      fprintf(device->logfp, ":");
      for (size_t i = 0; i < sizeof(f->cont.data); ++i)
        fprintf(device->logfp, "%02X", f->cont.data[i]);
    }
    fprintf(device->logfp, "\n");
  }
}

int U2Fob_sendHidFrame(struct U2Fob* device, U2FHID_FRAME* f) {
  uint8_t d[sizeof(U2FHID_FRAME) + 1];
  int res;

  d[0] = 0;                // un-numbered report
  f->cid = htonl(f->cid);  // cid is in network order on the wire
  memcpy(d + 1, f, sizeof(U2FHID_FRAME));
  f->cid = ntohl(f->cid);

  if (!DEV_opened(device)) return -ERR_OTHER;
  res = DEV_write(device, d, sizeof(d));

  if (res == sizeof(d)) {
    U2Fob_logFrame(device, ">", f);
    return 0;
  }

  return -ERR_OTHER;
}

int U2Fob_receiveHidFrame(struct U2Fob* device, U2FHID_FRAME* r, float to) {
  if (to <= 0.0) return -ERR_MSG_TIMEOUT;

  if (!DEV_opened(device)) return -ERR_OTHER;
  memset((int8_t*)r, 0xEE, sizeof(U2FHID_FRAME));
  int res = DEV_read_timeout(device, (uint8_t*)r, sizeof(U2FHID_FRAME),
                             (int)(to * 1000));
  if (res == sizeof(U2FHID_FRAME)) {
    r->cid = ntohl(r->cid);
    U2Fob_logFrame(device, "<", r);
    return 0;
  }

  if (res == -1) return -ERR_OTHER;

  if (device->logfp) {
    fprintf(device->logfp, "t+%.3f", U2Fob_deltaTime(&device->logtime));
    fprintf(device->logfp, "< (timeout)\n");
  }

  return -ERR_MSG_TIMEOUT;
}

int U2Fob_init(struct U2Fob* device) {
  int res;
  U2FHID_FRAME challenge;

  for (size_t i = 0; i < sizeof(device->nonce); ++i) {
    device->nonce[i] ^= (rand() >> 3);
  }

  challenge.cid = device->cid;
  challenge.init.cmd = U2FHID_INIT | TYPE_INIT;
  challenge.init.bcnth = 0;
  challenge.init.bcntl = INIT_NONCE_SIZE;
  memcpy(challenge.init.data, device->nonce, INIT_NONCE_SIZE);

  res = U2Fob_sendHidFrame(device, &challenge);
  if (res != 0) return res;

  for (;;) {
    U2FHID_FRAME response;
    res = U2Fob_receiveHidFrame(device, &response, 2.0);

    if (res == -ERR_MSG_TIMEOUT) return res;
    if (res == -ERR_OTHER) return res;

    if (response.cid != challenge.cid) continue;
    if (response.init.cmd != challenge.init.cmd) continue;
    if (MSG_LEN(response) != sizeof(U2FHID_INIT_RESP)) continue;
    if (memcmp(response.init.data, challenge.init.data, INIT_NONCE_SIZE))
      continue;

    device->cid = (response.init.data[8] << 24) |
                  (response.init.data[9] << 16) |
                  (response.init.data[10] << 8) | (response.init.data[11] << 0);

    break;
  }

  return 0;
}

int U2Fob_send(struct U2Fob* device, uint8_t cmd, const void* data,
               size_t size) {
  U2FHID_FRAME frame;
  int res;
  size_t frameLen;
  uint8_t seq = 0;
  uint8_t* pData = (uint8_t*)data;

  frame.cid = device->cid;
  frame.init.cmd = TYPE_INIT | cmd;
  frame.init.bcnth = (size >> 8) & 255;
  frame.init.bcntl = (size & 255);

  frameLen = min(size, sizeof(frame.init.data));
  memset(frame.init.data, 0xEE, sizeof(frame.init.data));
  memcpy(frame.init.data, pData, frameLen);

  do {
    res = U2Fob_sendHidFrame(device, &frame);
    if (res != 0) return res;

    if (device->dev == NULL) usleep(10000);

    size -= frameLen;
    pData += frameLen;

    frame.cont.seq = seq++;
    frameLen = min(size, sizeof(frame.cont.data));
    memset(frame.cont.data, 0xEE, sizeof(frame.cont.data));
    memcpy(frame.cont.data, pData, frameLen);
  } while (size);

  return 0;
}

int U2Fob_recv(struct U2Fob* device, uint8_t* cmd, void* data, size_t max,
               float timeout) {
  U2FHID_FRAME frame;
  int res, result;
  size_t totalLen, frameLen;
  uint8_t seq = 0;
  uint8_t* pData = (uint8_t*)data;
  uint64_t timeTracker = 0;

  U2Fob_deltaTime(&timeTracker);

  do {
    res = U2Fob_receiveHidFrame(device, &frame, timeout);
    if (res != 0) return res;

    timeout -= U2Fob_deltaTime(&timeTracker);
  } while (frame.cid != device->cid || FRAME_TYPE(frame) != TYPE_INIT);

  if (frame.init.cmd == U2FHID_ERROR) return -frame.init.data[0];

  *cmd = frame.init.cmd;

  totalLen = min(max, MSG_LEN(frame));
  frameLen = min(sizeof(frame.init.data), totalLen);

  result = totalLen;

  memcpy(pData, frame.init.data, frameLen);
  totalLen -= frameLen;
  pData += frameLen;

  while (totalLen) {
    res = U2Fob_receiveHidFrame(device, &frame, timeout);
    if (res != 0) return res;

    timeout -= U2Fob_deltaTime(&timeTracker);

    if (frame.cid != device->cid) continue;
    if (FRAME_TYPE(frame) != TYPE_CONT) return -ERR_INVALID_SEQ;
    if (FRAME_SEQ(frame) != seq++) return -ERR_INVALID_SEQ;

    frameLen = min(sizeof(frame.cont.data), totalLen);

    memcpy(pData, frame.cont.data, frameLen);
    totalLen -= frameLen;
    pData += frameLen;
  }

  return result;
}

int U2Fob_exchange_apdu_buffer(struct U2Fob* device, void* data, size_t size,
                               std::string* in) {
  uint8_t cmd = U2FHID_MSG;

  int res = U2Fob_send(device, cmd, data, size);
  if (res != 0) return res;

  uint8_t buf[4096];
  memset(buf, 0xEE, sizeof(buf));
  res = U2Fob_recv(device, &cmd, buf, sizeof(buf), 5.0);
  if (res < 0) return res;

  if (cmd != U2FHID_MSG) return -ERR_OTHER;

  uint16_t sw12;

  if (res < 2) return -ERR_OTHER;
  sw12 = (buf[res - 2] << 8) | buf[res - 1];
  res -= 2;

  in->assign(reinterpret_cast<char*>(buf), res);

  return sw12;
}

int U2Fob_apdu(struct U2Fob* device, uint8_t CLA, uint8_t INS, uint8_t P1,
               uint8_t P2, const std::string& out, std::string* in) {
  uint8_t buf[4096];
  size_t nc = out.size() ? (3 + out.size()) : 0;

  // Construct outgoing message.
  memset(buf, 0xEE, sizeof(buf));
  buf[0] = CLA;
  buf[1] = INS;
  buf[2] = P1;
  buf[3] = P2;

  uint8_t offs = 4;

  // Encode lc.
  if (nc) {
    buf[offs++] = 0;  // extended length
    buf[offs++] = (out.size() >> 8) & 255;
    buf[offs++] = (out.size() & 255);
    memcpy(buf + offs, out.data(), out.size());
    offs += out.size();
  }

  // Encode le.
  if (!nc) {
    // When there are no data sent, an extra 0 is necessary prior to Le.
    buf[offs++] = 0;
  }
  buf[offs++] = 0;
  buf[offs++] = 0;

  return U2Fob_exchange_apdu_buffer(device, buf, offs, in);
}

bool getCertificate(const U2F_REGISTER_RESP& rsp, std::string* cert) {
  size_t hkLen = rsp.keyHandleLen;

  CHECK_GE(hkLen, 64);
  CHECK_LT(hkLen, sizeof(rsp.keyHandleCertSig));

  size_t certOff = hkLen;
  size_t certLen = sizeof(rsp.keyHandleCertSig) - certOff;
  const uint8_t* p = &rsp.keyHandleCertSig[certOff];

  CHECK_GE(certLen, 4);
  CHECK_EQ(p[0], 0x30);

  CHECK_GE(p[1], 0x81);
  CHECK_LE(p[1], 0x82);

  size_t seqLen;
  size_t headerLen;
  if (p[1] == 0x81) {
    seqLen = p[2];
    headerLen = 3;
  } else if (p[1] == 0x82) {
    seqLen = p[2] * 256 + p[3];
    headerLen = 4;
  } else {
    // FAIL
    AbortOrNot();
  }

  CHECK_LE(seqLen, certLen - headerLen);

  cert->assign(reinterpret_cast<const char*>(p), seqLen + headerLen);
  return true;
}

bool getSignature(const U2F_REGISTER_RESP& rsp, std::string* sig) {
  std::string cert;
  CHECK_NE(false, getCertificate(rsp, &cert));

  size_t sigOff = rsp.keyHandleLen + cert.size();
  CHECK_LE(sigOff, sizeof(rsp.keyHandleCertSig));

  size_t sigLen = sizeof(rsp.keyHandleCertSig) - sigOff;
  const uint8_t* p = &rsp.keyHandleCertSig[sigOff];

  CHECK_GE(sigLen, 2);
  CHECK_EQ(p[0], 0x30);

  size_t seqLen = p[1];
  CHECK_LE(seqLen, sigLen - 2);

  sig->assign(reinterpret_cast<const char*>(p), seqLen + 2);
  return true;
}

bool getSubjectPublicKey(const std::string& cert, std::string* pk) {
  CHECK_GE(cert.size(), P256_POINT_SIZE);

  // Explicitly search for asn1 lead-in sequence of p256-ecdsa public key.
  const char asn1[] = "3059301306072A8648CE3D020106082A8648CE3D030107034200";
  std::string pkStart(a2b(asn1));

  size_t off = cert.find(pkStart);
  CHECK_NE(off, std::string::npos);

  off += pkStart.size();
  CHECK_LE(off, cert.size() - P256_POINT_SIZE);

  pk->assign(cert, off, P256_POINT_SIZE);
  return true;
}

bool getCertSignature(const std::string& cert, std::string* sig) {
  // Explicitly search asn1 lead-in sequence of p256-ecdsa signature.
  const char asn1[] = "300A06082A8648CE3D04030203";
  std::string sigStart(a2b(asn1));

  size_t off = cert.find(sigStart);
  CHECK_NE(off, std::string::npos);

  off += sigStart.size();
  CHECK_LE(off, cert.size() - 8);

  size_t bitStringLen = cert[off] & 255;
  CHECK_EQ(bitStringLen, cert.size() - off - 1);
  CHECK_EQ(cert[off + 1], 0);

  sig->assign(cert, off + 2, cert.size() - off - 2);
  return true;
}

bool verifyCertificate(const std::string& pk, const std::string& cert) {
  CHECK_EQ(true, false);  // not yet implemented
}
