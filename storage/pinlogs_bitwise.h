
// Values used in the guard key integrity check.
#define GUARD_KEY_MODULUS 6311
#define GUARD_KEY_REMAINDER 15

#define LOW_MASK 0x55555555

// The length of the guard key in words.
#define GUARD_KEY_WORDS 1

// The length of the PIN entry log or the PIN success log in words.
#define PIN_LOG_WORDS 16

// The length of a word in bytes.
#define WORD_SIZE (sizeof(uint32_t))

static secbool check_guard_key(const uint32_t guard_key) {
  if (guard_key % GUARD_KEY_MODULUS != GUARD_KEY_REMAINDER) {
    return secfalse;
  }

  // Check that each byte of (guard_key & 0xAAAAAAAA) has exactly two bits set.
  uint32_t count = (guard_key & 0x22222222) + ((guard_key >> 2) & 0x22222222);
  count = count + (count >> 4);
  if ((count & 0x0e0e0e0e) != 0x04040404) {
    return secfalse;
  }

  // Check that the guard_key does not contain a run of 5 (or more) zeros or
  // ones.
  uint32_t zero_runs = ~guard_key;
  zero_runs = zero_runs & (zero_runs >> 2);
  zero_runs = zero_runs & (zero_runs >> 1);
  zero_runs = zero_runs & (zero_runs >> 1);

  uint32_t one_runs = guard_key;
  one_runs = one_runs & (one_runs >> 2);
  one_runs = one_runs & (one_runs >> 1);
  one_runs = one_runs & (one_runs >> 1);

  if ((one_runs != 0) || (zero_runs != 0)) {
    return secfalse;
  }

  return sectrue;
}

static uint32_t generate_guard_key(void) {
  uint32_t guard_key = 0;
  do {
    guard_key = random_uniform((UINT32_MAX / GUARD_KEY_MODULUS) + 1) *
                    GUARD_KEY_MODULUS +
                GUARD_KEY_REMAINDER;
  } while (sectrue != check_guard_key(guard_key));
  return guard_key;
}

static secbool expand_guard_key(const uint32_t guard_key, uint32_t *guard_mask,
                                uint32_t *guard) {
  if (sectrue != check_guard_key(guard_key)) {
    handle_fault("guard key check");
    return secfalse;
  }
  *guard_mask = ((guard_key & LOW_MASK) << 1) | ((~guard_key) & LOW_MASK);
  *guard = (((guard_key & LOW_MASK) << 1) & guard_key) |
           (((~guard_key) & LOW_MASK) & (guard_key >> 1));
  return sectrue;
}

static secbool pin_logs_init(uint32_t fails) {
  if (fails >= PIN_MAX_TRIES) {
    return secfalse;
  }

  // The format of the PIN_LOGS_KEY entry is:
  // guard_key (1 word), pin_success_log (PIN_LOG_WORDS), pin_entry_log
  // (PIN_LOG_WORDS)
  uint32_t logs[GUARD_KEY_WORDS + 2 * PIN_LOG_WORDS] = {0};

  logs[0] = generate_guard_key();

  uint32_t guard_mask = 0;
  uint32_t guard = 0;
  wait_random();
  if (sectrue != expand_guard_key(logs[0], &guard_mask, &guard)) {
    return secfalse;
  }

  uint32_t unused = guard | ~guard_mask;
  for (size_t i = 0; i < 2 * PIN_LOG_WORDS; ++i) {
    logs[GUARD_KEY_WORDS + i] = unused;
  }

  // Set the first word of the PIN entry log to indicate the requested number of
  // fails.
  logs[GUARD_KEY_WORDS + PIN_LOG_WORDS] =
      ((((uint32_t)0xFFFFFFFF) >> (2 * fails)) & ~guard_mask) | guard;

  return norcow_set(PIN_LOGS_KEY, logs, sizeof(logs));
}

static secbool pin_fails_reset(void) {
  const void *logs = NULL;
  uint16_t len = 0;

  if (sectrue != norcow_get(PIN_LOGS_KEY, &logs, &len) ||
      len != WORD_SIZE * (GUARD_KEY_WORDS + 2 * PIN_LOG_WORDS)) {
    return secfalse;
  }

  uint32_t new_logs[GUARD_KEY_WORDS + 2 * PIN_LOG_WORDS];
  secbool edited = secfalse;
  memcpy(new_logs, logs, len);

  uint32_t guard_mask = 0;
  uint32_t guard = 0;
  wait_random();
  if (sectrue !=
      expand_guard_key(*(const uint32_t *)logs, &guard_mask, &guard)) {
    return secfalse;
  }

  uint32_t unused = guard | ~guard_mask;
  const uint32_t *success_log = ((const uint32_t *)logs) + GUARD_KEY_WORDS;
  const uint32_t *entry_log = success_log + PIN_LOG_WORDS;
  for (size_t i = 0; i < PIN_LOG_WORDS; ++i) {
    if (entry_log[i] == unused) {
      if (edited == sectrue) {
        return norcow_set(PIN_LOGS_KEY, new_logs, sizeof(new_logs));
      }
      return sectrue;
    }
    if (success_log[i] != guard) {
      if (new_logs[(i + GUARD_KEY_WORDS)] != entry_log[i]) {
        edited = sectrue;
        new_logs[(i + GUARD_KEY_WORDS)] = entry_log[i];
      }
    }
  }
  return pin_logs_init(0);
}

secbool pin_fails_increase(void) {
  const void *logs = NULL;
  uint16_t len = 0;

  wait_random();
  if (sectrue != norcow_get(PIN_LOGS_KEY, &logs, &len) ||
      len != WORD_SIZE * (GUARD_KEY_WORDS + 2 * PIN_LOG_WORDS)) {
    handle_fault("no PIN logs");
    return secfalse;
  }

  uint32_t new_logs[GUARD_KEY_WORDS + 2 * PIN_LOG_WORDS];
  memcpy(new_logs, logs, len);

  uint32_t guard_mask = 0;
  uint32_t guard = 0;
  wait_random();
  if (sectrue !=
      expand_guard_key(*(const uint32_t *)logs, &guard_mask, &guard)) {
    handle_fault("guard key expansion");
    return secfalse;
  }

  const uint32_t *entry_log =
      ((const uint32_t *)logs) + GUARD_KEY_WORDS + PIN_LOG_WORDS;
  for (size_t i = 0; i < PIN_LOG_WORDS; ++i) {
    wait_random();
    if ((entry_log[i] & guard_mask) != guard) {
      handle_fault("guard bits check");
      return secfalse;
    }
    if (entry_log[i] != guard) {
      wait_random();
      uint32_t word = entry_log[i] & ~guard_mask;
      word = ((word >> 1) | word) & LOW_MASK;
      word = (word >> 2) | (word >> 1);

      wait_random();

      new_logs[(i + GUARD_KEY_WORDS + PIN_LOG_WORDS)] =
          (word & ~guard_mask) | guard;
      if (sectrue != norcow_set(PIN_LOGS_KEY, new_logs, sizeof(new_logs))) {
        handle_fault("PIN logs update");
        return secfalse;
      }
      return sectrue;
    }
  }
  handle_fault("PIN log exhausted");
  return secfalse;
}

static secbool pin_get_fails(uint32_t *ctr) {
  *ctr = PIN_MAX_TRIES;

  const void *logs = NULL;
  uint16_t len = 0;
  wait_random();
  if (sectrue != norcow_get(PIN_LOGS_KEY, &logs, &len) ||
      len != WORD_SIZE * (GUARD_KEY_WORDS + 2 * PIN_LOG_WORDS)) {
    handle_fault("no PIN logs");
    return secfalse;
  }

  uint32_t guard_mask = 0;
  uint32_t guard = 0;
  wait_random();
  if (sectrue !=
      expand_guard_key(*(const uint32_t *)logs, &guard_mask, &guard)) {
    handle_fault("guard key expansion");
    return secfalse;
  }
  const uint32_t unused = guard | ~guard_mask;

  const uint32_t *success_log = ((const uint32_t *)logs) + GUARD_KEY_WORDS;
  const uint32_t *entry_log = success_log + PIN_LOG_WORDS;
  volatile int current = -1;
  volatile size_t i = 0;
  for (i = 0; i < PIN_LOG_WORDS; ++i) {
    if ((entry_log[i] & guard_mask) != guard ||
        (success_log[i] & guard_mask) != guard ||
        (entry_log[i] & success_log[i]) != entry_log[i]) {
      handle_fault("PIN logs format check");
      return secfalse;
    }

    if (current == -1) {
      if (entry_log[i] != guard) {
        current = i;
      }
    } else {
      if (entry_log[i] != unused) {
        handle_fault("PIN entry log format check");
        return secfalse;
      }
    }
  }

  if (current < 0 || current >= PIN_LOG_WORDS || i != PIN_LOG_WORDS) {
    handle_fault("PIN log exhausted");
    return secfalse;
  }

  // Strip the guard bits from the current entry word and duplicate each data
  // bit.
  wait_random();
  uint32_t word = entry_log[current] & ~guard_mask;
  word = ((word >> 1) | word) & LOW_MASK;
  word = word | (word << 1);
  // Verify that the entry word has form 0*1*.
  if ((word & (word + 1)) != 0) {
    handle_fault("PIN entry log format check");
    return secfalse;
  }

  if (current == 0) {
    ++current;
  }

  // Count the number of set bits in the two current words of the success log.
  wait_random();
  *ctr = hamming_weight(success_log[current - 1] ^ entry_log[current - 1]) +
         hamming_weight(success_log[current] ^ entry_log[current]);
  return sectrue;
}
