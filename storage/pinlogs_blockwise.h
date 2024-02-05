
#if FLASH_BLOCK_WORDS <= 1
#error "FLASH_BLOCK_WORDS must be at least 2 to fit the counter and header"
#endif

#define PIN_LOG_HALFWORDS (((FLASH_BLOCK_WORDS - 1) * sizeof(uint32_t)) / 2)

static uint16_t expand_counter(uint16_t c) {
  c = ((c << 4) | c) & 0x0f0f;
  c = ((c << 2) | c) & 0x3333;
  c = ((c << 1) | c) & 0x5555;
  c = ((c << 1) | c) ^ 0xaaaa;
  return c;
}

static uint16_t compress_counter(uint16_t c) {
  if (((c ^ (c << 1)) & 0xAAAA) != 0xAAAA) {
    handle_fault("ill-formed counter");
  }
  c = c & 0x5555;
  c = ((c >> 1) | c) & 0x3333;
  c = ((c >> 2) | c) & 0x0f0f;
  c = ((c >> 4) | c) & 0x00ff;
  return c;
}

static secbool pin_get_fails(uint32_t *ctr) {
  const void *logs = NULL;
  uint16_t len = 0;

  wait_random();

  if (sectrue != norcow_get(PIN_LOGS_KEY, &logs, &len) ||
      len != PIN_LOG_HALFWORDS * sizeof(uint16_t)) {
    handle_fault("no PIN logs");
    return secfalse;
  }

  uint16_t c = compress_counter(((uint16_t *)logs)[0]);

  uint16_t correct_bytes_cnt = 0;

  for (uint8_t i = 0; i < PIN_LOG_HALFWORDS; i++) {
    wait_random();
    correct_bytes_cnt += compress_counter(((uint16_t *)logs)[i]) == c;
    *ctr = c;
  }

  if (correct_bytes_cnt != PIN_LOG_HALFWORDS) {
    handle_fault("PIN logs corrupted");
    return secfalse;
  }

  return sectrue * (correct_bytes_cnt == PIN_LOG_HALFWORDS);
}

static secbool pin_logs_init(uint32_t fails) {
  wait_random();

  uint16_t logs[PIN_LOG_HALFWORDS];
  uint16_t ctr = expand_counter(fails);

  for (uint8_t i = 0; i < PIN_LOG_HALFWORDS; i++) {
    logs[i] = ctr;
  }

  if (fails != compress_counter(ctr)) {
    handle_fault("PIN logs increase failed");
    return secfalse;
  }

  return norcow_set(PIN_LOGS_KEY, logs, sizeof(logs));
}

static secbool pin_fails_reset(void) { return pin_logs_init(0); }

secbool pin_fails_increase(void) {
  uint32_t fails;

  if (sectrue != pin_get_fails(&fails)) {
    return secfalse;
  }

  fails++;

  return pin_logs_init(fails);
}
