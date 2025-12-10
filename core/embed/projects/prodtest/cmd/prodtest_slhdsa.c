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

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/rng.h>
#include <sec/xsha256.h>
#include <sys/systick.h>

#include <../vendor/sphincsplus/ref/api.h>

int g_sha256_perfc_init_calls;
int g_sha256_perfc_inc_blocks_calls;
int g_sha256_perfc_inc_blocks;
int g_sha256_perfc_finalize_calls;
int g_sha256_perfc_finalize_bytes;

static void clear_perf_counters() {
  g_sha256_perfc_init_calls = 0;
  g_sha256_perfc_inc_blocks_calls = 0;
  g_sha256_perfc_inc_blocks = 0;
  g_sha256_perfc_finalize_calls = 0;
  g_sha256_perfc_finalize_bytes = 0;
}

static void trace_perf_counters(cli_t* cli) {
  cli_trace(cli, "SHA256 performance counters:");
  cli_trace(cli, "  init calls:           %d", g_sha256_perfc_init_calls);
  cli_trace(cli, "  inc blocks calls:     %d", g_sha256_perfc_inc_blocks_calls);
  cli_trace(cli, "  inc blocks processed: %d", g_sha256_perfc_inc_blocks);
  cli_trace(cli, "  finalize calls:       %d", g_sha256_perfc_finalize_calls);
  cli_trace(cli, "  finalize bytes:       %d", g_sha256_perfc_finalize_bytes);
}

static void prodtest_test_slhdsa(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "crypto_sign_secretkeybytes() -> %d",
            crypto_sign_secretkeybytes());
  cli_trace(cli, "crypto_sign_publickeybytes() -> %d",
            crypto_sign_publickeybytes());
  cli_trace(cli, "crypto_sign_bytes() -> %d", crypto_sign_bytes());
  cli_trace(cli, "crypto_sign_seedbytes() -> %d", crypto_sign_seedbytes());

  unsigned char pub_key[CRYPTO_PUBLICKEYBYTES];
  unsigned char sec_key[CRYPTO_SECRETKEYBYTES];

  unsigned char msg[] = "Test message for SLHDSA signature";

  unsigned char sig[CRYPTO_BYTES];
  unsigned int sig_len = 0;

  crypto_sign_keypair(pub_key, sec_key);

  ticks_t start;
  uint32_t duration;

  cli_trace(cli, "Signing message using SLHDSA...");

  clear_perf_counters();
  start = systick_ms();
  crypto_sign_signature(sig, &sig_len, msg, sizeof(msg), sec_key);
  duration = systick_ms() - start;

  cli_trace(cli, "Signed in %u.%u s", duration / 1000, duration % 1000);
  trace_perf_counters(cli);

  cli_trace(cli, "Verifying signature using SLHDSA...");

  clear_perf_counters();
  start = systick_ms();
  int rc = crypto_sign_verify(sig, sig_len, msg, sizeof(msg), pub_key);
  duration = systick_ms() - start;

  cli_trace(cli, "Verified in %u.%u s", duration / 1000, duration % 1000);
  trace_perf_counters(cli);

  cli_trace(cli, "Signature verification result: %s",
            (rc == 0) ? "OK" : "FAIL");

  cli_ok(cli, "");
}

void randombytes(unsigned char* x, unsigned long long xlen) {
  rng_fill_buffer(x, xlen);
}

void prodtest_test_hash(cli_t* cli) {
  const char* test_vec = cli_arg(cli, "test-vector");

  uint8_t digest[32];

  xsha256_ctx_t ctx1;
  xsha256_init(&ctx1);

#if XSHA256_CONTEXT_SAVING
  // Test context saving/restoring
  xsha256_ctx_t ctx2;
  xsha256_init(&ctx2);
#endif

  xsha256_update(&ctx1, (const uint8_t*)test_vec, strlen(test_vec));

#if XSHA256_CONTEXT_SAVING
  const char* test_vec2 =
      "xxx232132130-391oakjdlksjfodkjfssdlkfns<;"
      "fdsfposdfspdofispdofisdopfidspfoisf";
  xsha256_update(&ctx2, (const uint8_t*)test_vec2, strlen(test_vec2));
#endif

  xsha256_digest(&ctx1, digest);

  cli_ok_hexdata(cli, digest, sizeof(digest));
}

// clang-format off
PRODTEST_CLI_CMD(
  .name = "test-slhdsa",
  .func = prodtest_test_slhdsa,
  .info = "Perform SLHDSA self-test",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "test-hash",
  .func = prodtest_test_hash,
  .info = "Test hardware hash unit",
  .args = "<test-vector>"
);
