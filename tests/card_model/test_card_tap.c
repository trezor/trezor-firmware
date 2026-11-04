/* SPDX-License-Identifier: GPL-3.0-or-later */
/* The vault card backend over TCP against a card model server that plays a
 * slow user: run by `make test_tap`, which starts the server with -t and -k. */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#include <sec/vault.h>
#include <sec/vault_card.h>
#include "curves.h"

#include "card_transport.h"
#include "vault_stub.h"

#define H 0x80000000u

static int failures;
#define CHECK(x)                                                   \
  do {                                                             \
    if (!(x)) {                                                    \
      fprintf(stderr, "%s:%d: FAIL %s\n", __FILE__, __LINE__, #x); \
      failures++;                                                  \
    }                                                              \
  } while (0)

/* The prompt, as coreapp would show it. */
static int prompts, outcomes;
static vault_card_state_t outcome;
static bool cancel;
static bool ui(vault_card_state_t state, uint32_t remaining_ms) {
  if (state == VAULT_CARD_WAITING) {
    CHECK(remaining_ms > 0 && remaining_ms <= CARD_WAIT_MS);
    prompts++;
  } else {
    outcome = state;
    outcomes++;
  }
  return cancel;
}

static uint32_t now_ms(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void sleep_ms(uint32_t ms) {
  struct timespec t = {ms / 1000, (ms % 1000) * 1000000L};
  nanosleep(&t, NULL);
}

/* Derive a hardened child: the card computes the parent's public key. */
static bool derive(vault_blob_t *blob, uint32_t index) {
  vault_request_t r = {.abi = VAULT_ABI,
                       .op = VAULT_DERIVE,
                       .owner = 2,
                       .length = 4,
                       .blob = *blob};
  vault_response_t out;
  memcpy(r.data, &index, 4);
  if (!vault_call(&r, &out)) return false;
  *blob = out.blob;
  return true;
}

/* Run one card operation; report the prompts it showed and its duration. */
static bool tap(vault_blob_t *blob, uint32_t index, int *shown,
                uint32_t *took) {
  prompts = outcomes = 0;
  outcome = VAULT_CARD_WAITING;
  uint32_t start = now_ms();
  bool ok = derive(blob, index);
  *took = now_ms() - start;
  *shown = prompts;
  /* Exactly one outcome after a prompt, and none for a quiet success. */
  CHECK(outcomes == (prompts > 0 || !ok));
  return ok;
}

int main(void) {
  int tap_ms = atoi(getenv("CARD_TAP_MS")),
      hold_ms = atoi(getenv("CARD_HOLD_MS"));
  vault_card_set_ui(ui);

  vault_request_t r = {.abi = VAULT_ABI, .op = VAULT_SEED_STORAGE, .owner = 2};
  vault_response_t out;
  CHECK(vault_call(&r, &out));
  r = (vault_request_t){.abi = VAULT_ABI,
                        .op = VAULT_FROM_SEED,
                        .owner = 2,
                        .arg = 1,
                        .blob = out.blob};
  strcpy(r.curve, SECP256K1_NAME);
  CHECK(vault_call(&r, &out));
  vault_blob_t node = out.blob;
  int shown;
  uint32_t took;

  /* The user brings the card: the prompt shows until it arrives. */
  CHECK(tap(&node, 44 | H, &shown, &took));
  CHECK(shown > 0 && took >= (uint32_t)tap_ms && outcome == VAULT_CARD_DONE);
  printf("first tap: %u ms, %d prompt updates\n", took, shown);

  /* The card is still there: no prompt. */
  CHECK(tap(&node, 0 | H, &shown, &took));
  CHECK(shown == 0 && took < (uint32_t)tap_ms);

  /* The card left: the next operation asks for a new tap. */
  sleep_ms(hold_ms + 200);
  CHECK(tap(&node, 0 | H, &shown, &took));
  CHECK(shown > 0 && took >= (uint32_t)tap_ms && outcome == VAULT_CARD_DONE);
  printf("second tap: %u ms, %d prompt updates\n", took, shown);

  /* The user cancels the prompt: the operation fails at once. */
  sleep_ms(hold_ms + 200);
  cancel = true;
  vault_blob_t before = node;
  CHECK(!tap(&node, 0, &shown, &took));
  CHECK(shown == 1 && took < (uint32_t)tap_ms);
  CHECK(outcome == VAULT_CARD_CANCELLED);
  cancel = false;

  /* ... and the next one asks again. */
  node = before;
  CHECK(tap(&node, 0, &shown, &took));
  CHECK(shown > 0 && outcome == VAULT_CARD_DONE);

  /* Nobody taps: the prompt gives up after CARD_WAIT_MS. The reader is a
   * listener that never answers. */
  int silent = socket(AF_INET, SOCK_STREAM, 0);
  struct sockaddr_in address = {.sin_family = AF_INET,
                                .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
  socklen_t size = sizeof(address);
  CHECK(bind(silent, (struct sockaddr *)&address, size) == 0 &&
        listen(silent, 1) == 0 &&
        getsockname(silent, (struct sockaddr *)&address, &size) == 0);
  char port[8];
  snprintf(port, sizeof(port), "%u", ntohs(address.sin_port));
  const char *card_port = getenv("TREZOR_CARD_PORT");
  setenv("TREZOR_CARD_PORT", port, 1);
  card_disconnect();
  node = before;
  CHECK(!tap(&node, 0, &shown, &took));
  CHECK(outcome == VAULT_CARD_TIMEOUT && took >= CARD_WAIT_MS);
  close(silent);
  setenv("TREZOR_CARD_PORT", card_port, 1);

  /* No reader at all: the operation fails, and says so without a prompt. */
  card_disconnect();
  setenv("TREZOR_CARD_PORT", "1", 1);
  node = before;
  CHECK(!tap(&node, 0, &shown, &took));
  CHECK(shown == 0 && outcome == VAULT_CARD_FAILED);

  if (failures) {
    fprintf(stderr, "%d failures\n", failures);
    return 1;
  }
  printf("card tap: all checks passed\n");
  return 0;
}
