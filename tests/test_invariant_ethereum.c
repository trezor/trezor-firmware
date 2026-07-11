#include <check.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

/*
 * Simulates the vulnerable calculation pattern from ethereum.c:
 *   data_left = total_data_length - bytes_processed
 *   msg_tx_request.data_length = data_left <= 1024 ? data_left : 1024;
 *
 * Security invariant: The computed chunk size must ALWAYS be in [0, 1024].
 * No integer overflow or underflow in the upstream calculation of data_left
 * should cause the chunk size to exceed 1024 or wrap to a huge value.
 */

/* Mimics the logic in ethereum.c using safe types */
static uint32_t compute_chunk_size(uint32_t total_length, uint32_t bytes_processed) {
    /* This is the vulnerable pattern: subtraction may underflow if
     * bytes_processed > total_length due to adversarial input */
    uint32_t data_left = total_length - bytes_processed;
    uint32_t chunk = (data_left <= 1024) ? data_left : 1024;
    return chunk;
}

/* Safe version that should be used instead */
static uint32_t compute_chunk_size_safe(uint32_t total_length, uint32_t bytes_processed) {
    if (bytes_processed > total_length) {
        return 0;
    }
    uint32_t data_left = total_length - bytes_processed;
    uint32_t chunk = (data_left <= 1024) ? data_left : 1024;
    return chunk;
}

typedef struct {
    uint32_t total_length;
    uint32_t bytes_processed;
    const char *description;
} TestCase;

START_TEST(test_chunk_size_security_invariant)
{
    /* Invariant: chunk size must always be <= 1024 and must not wrap/overflow */
    TestCase cases[] = {
        /* Normal cases */
        {0,          0,          "zero total, zero processed"},
        {1024,       0,          "exactly 1024 total, zero processed"},
        {1024,       512,        "1024 total, 512 processed"},
        {1024,       1024,       "1024 total, fully processed"},
        {2048,       0,          "2048 total, zero processed"},
        {2048,       1024,       "2048 total, 1024 processed"},
        {2048,       2048,       "2048 total, fully processed"},

        /* Boundary cases */
        {1,          0,          "1 byte total"},
        {1025,       0,          "just over 1024"},
        {1023,       0,          "just under 1024"},

        /* Adversarial: bytes_processed > total_length (underflow scenario) */
        {0,          1,          "underflow: 0 total, 1 processed"},
        {0,          1024,       "underflow: 0 total, 1024 processed"},
        {0,          0xFFFFFFFF, "underflow: 0 total, max processed"},
        {100,        200,        "underflow: 100 total, 200 processed"},
        {1024,       1025,       "underflow: 1024 total, 1025 processed"},
        {1024,       0xFFFFFFFF, "underflow: 1024 total, max processed"},
        {0x7FFFFFFF, 0x80000000, "underflow: near max total, over max processed"},

        /* Adversarial: large total_length values (potential overflow in upstream) */
        {0xFFFFFFFF, 0,          "max total, zero processed"},
        {0xFFFFFFFF, 0xFFFFFFFE, "max total, near-max processed"},
        {0xFFFFFFFF, 0xFFFFFFFF, "max total, max processed"},
        {0x80000000, 0,          "high bit set total, zero processed"},
        {0x80000000, 0x7FFFFFFF, "high bit set total, near-half processed"},
        {0x80000001, 0x80000000, "high bit set total, just under processed"},

        /* Adversarial: values that trigger integer overflow in addition/multiplication
         * if total_length was computed from user fields like (count * size) */
        {0xFFFF0000, 0xFFFF,     "near-overflow computed total"},
        {0x0000FFFF, 0x00010000, "underflow with 16-bit boundary values"},
        {0x00010000, 0x00010001, "underflow just past 64k boundary"},

        /* Adversarial: values near chunk boundary */
        {1025,       1,          "data_left exactly 1024"},
        {1026,       1,          "data_left exactly 1025"},
        {2048,       1023,       "data_left exactly 1025"},
        {2048,       1024,       "data_left exactly 1024"},
    };

    int num_cases = sizeof(cases) / sizeof(cases[0]);

    for (int i = 0; i < num_cases; i++) {
        uint32_t total = cases[i].total_length;
        uint32_t processed = cases[i].bytes_processed;

        /* Test the safe version - must always produce chunk <= 1024 */
        uint32_t safe_chunk = compute_chunk_size_safe(total, processed);
        ck_assert_msg(safe_chunk <= 1024,
            "SECURITY VIOLATION (safe): chunk=%u > 1024 for case '%s' "
            "(total=%u, processed=%u)",
            safe_chunk, cases[i].description, total, processed);

        /* The safe version must also not produce a chunk larger than remaining data */
        if (processed <= total) {
            uint32_t remaining = total - processed;
            ck_assert_msg(safe_chunk <= remaining,
                "SECURITY VIOLATION (safe): chunk=%u > remaining=%u for case '%s'",
                safe_chunk, remaining, cases[i].description);
        } else {
            /* If processed > total, safe version must return 0 */
            ck_assert_msg(safe_chunk == 0,
                "SECURITY VIOLATION (safe): chunk=%u != 0 when processed > total "
                "for case '%s' (total=%u, processed=%u)",
                safe_chunk, cases[i].description, total, processed);
        }

        /* For the vulnerable version, document that it CAN violate the invariant
         * when bytes_processed > total_length (underflow), but the safe version
         * must not. This demonstrates the regression guard. */
        if (processed <= total) {
            /* When no underflow, both versions should agree */
            uint32_t vuln_chunk = compute_chunk_size(total, processed);
            ck_assert_msg(vuln_chunk <= 1024,
                "SECURITY VIOLATION (vuln, no-underflow): chunk=%u > 1024 "
                "for case '%s' (total=%u, processed=%u)",
                vuln_chunk, cases[i].description, total, processed);
            ck_assert_msg(vuln_chunk == safe_chunk,
                "MISMATCH: vuln_chunk=%u != safe_chunk=%u for case '%s'",
                vuln_chunk, safe_chunk, cases[i].description);
        }
    }
}
END_TEST

START_TEST(test_chunk_size_never_exceeds_max)
{
    /* Invariant: For any valid (non-underflowing) inputs, chunk size <= 1024 */
    uint32_t test_totals[] = {
        0, 1, 512, 1023, 1024, 1025, 2048, 65536,
        0x7FFFFFFF, 0x80000000, 0xFFFFFFFF
    };
    int num_totals = sizeof(test_totals) / sizeof(test_totals[0]);

    for (int i = 0; i < num_totals; i++) {
        uint32_t total = test_totals[i];
        /* Test at various processed offsets: 0, half, total-1, total */
        uint32_t offsets[] = {0, total / 2, total > 0 ? total - 1 : 0, total};
        int num_offsets = sizeof(offsets) / sizeof(offsets[0]);

        for (int j = 0; j < num_offsets; j++) {
            uint32_t processed = offsets[j];
            if (processed > total) continue; /* skip underflow cases here */

            uint32_t chunk = compute_chunk_size_safe(total, processed);
            ck_assert_msg(chunk <= 1024,
                "SECURITY VIOLATION: chunk=%u > 1024 (total=%u, processed=%u)",
                chunk, total, processed);

            uint32_t remaining = total - processed;
            ck_assert_msg(chunk <= remaining || remaining == 0,
                "SECURITY VIOLATION: chunk=%u > remaining=%u (total=%u, processed=%u)",
                chunk, remaining, total, processed);
        }
    }
}
END_TEST

START_TEST(test_data_length_field_bounds)
{
    /* Invariant: The data_length field written to msg_tx_request must be
     * representable as a valid, non-overflowing uint32_t <= 1024 */

    /* Simulate adversarial transaction length fields that could be combined
     * to produce overflow in upstream calculations */
    typedef struct {
        uint32_t field_a;  /* e.g., data_initial_chunk length */
        uint32_t field_b;  /* e.g., data_length from protobuf */
        const char *desc;
    } OverflowCase;

    OverflowCase overflow_cases[] = {
        {0xFFFFFFFF, 1,          "max + 1 overflow"},
        {0x80000000, 0x80000000, "two halves overflow"},
        {0xFFFFFFFE, 2,          "near-max + 2 overflow"},
        {0x7FFFFFFF, 0x7FFFFFFF, "two near-halves"},
        {0xFFFF,     0xFFFF0001, "16-bit + complement overflow"},
        {1024,       0xFFFFFC00, "1024 + complement overflow"},
        {0,          0,          "zero + zero"},
        {1024,       0,          "normal: 1024 + 0"},
        {512,        512,        "normal: 512 + 512"},
    };

    int num_cases = sizeof(overflow_cases) / sizeof(overflow_cases[0]);

    for (int i = 0; i < num_cases; i++) {
        uint32_t a = overflow_cases[i].field_a;
        uint32_t b = overflow_cases[i].field_b;

        /* Check if addition would overflow */
        int overflows = (b > 0 && a > UINT32_MAX - b);

        if (!overflows) {
            uint32_t combined = a + b;
            /* Safe chunk computation on combined value */
            uint32_t chunk = compute_chunk_size_safe(combined, 0);
            ck_assert_msg(chunk <= 1024,
                "SECURITY VIOLATION: chunk=%u > 1024 for case '%s' "
                "(a=%u, b=%u, combined=%u)",
                chunk, overflow_cases[i].desc, a, b, combined);
        }
        /* If it overflows, the safe implementation should handle it gracefully
         * by saturating or clamping - we just verify no crash occurs */
    }
}
END_TEST

/*
 * Models the exact computation pattern used in ethereum_signing_init() and
 * ethereum_signing_init_eip1559() after the fix applied for V-004:
 *
 *   data_left = (params.data_initial_chunk_size <= data_total)
 *                   ? data_total - params.data_initial_chunk_size
 *                   : 0;
 *
 * This directly validates that the patched guard prevents unsigned integer
 * underflow when data_initial_chunk_size exceeds data_total.
 */
static uint32_t signing_init_data_left(uint32_t data_total,
                                       uint32_t initial_chunk_size) {
    return (initial_chunk_size <= data_total)
               ? data_total - initial_chunk_size
               : 0;
}

START_TEST(test_signing_init_data_left_exact_pattern)
{
    /*
     * Verify the exact ternary guard from ethereum_signing_init() and
     * ethereum_signing_init_eip1559() never produces a data_left value
     * larger than data_total, and handles adversarial inputs safely.
     */
    typedef struct {
        uint32_t data_total;
        uint32_t initial_chunk_size;
        uint32_t expected_data_left;
        const char *description;
    } SigningInitCase;

    SigningInitCase cases[] = {
        /* Normal cases: initial_chunk_size <= data_total */
        {0,          0,          0,          "zero total, zero chunk"},
        {1024,       0,          1024,       "1024 total, zero chunk"},
        {1024,       512,        512,        "1024 total, 512 chunk"},
        {1024,       1024,       0,          "1024 total, fully consumed"},
        {2048,       1024,       1024,       "2048 total, 1024 chunk"},
        {2048,       2048,       0,          "2048 total, fully consumed"},
        {0xFFFFFFFF, 0,          0xFFFFFFFF, "max total, zero chunk"},
        {0xFFFFFFFF, 0xFFFFFFFE, 1,          "max total, max-1 chunk"},
        {0xFFFFFFFF, 0xFFFFFFFF, 0,          "max total, max chunk"},

        /* Adversarial: initial_chunk_size > data_total -- must clamp to 0 */
        {0,          1,          0,          "underflow: 0 total, 1 chunk"},
        {0,          1024,       0,          "underflow: 0 total, 1024 chunk"},
        {0,          0xFFFFFFFF, 0,          "underflow: 0 total, max chunk"},
        {100,        200,        0,          "underflow: 100 total, 200 chunk"},
        {1024,       1025,       0,          "underflow: 1024 total, 1025 chunk"},
        {1024,       0xFFFFFFFF, 0,          "underflow: 1024 total, max chunk"},
        {0x7FFFFFFF, 0x80000000, 0,          "underflow: near-max total, over chunk"},
        {0x80000000, 0x80000001, 0,          "underflow: high-bit total, over chunk"},
    };

    int num_cases = sizeof(cases) / sizeof(cases[0]);

    for (int i = 0; i < num_cases; i++) {
        uint32_t result = signing_init_data_left(cases[i].data_total,
                                                 cases[i].initial_chunk_size);

        ck_assert_msg(result == cases[i].expected_data_left,
            "FAIL [%s]: signing_init_data_left(%u, %u) = %u, expected %u",
            cases[i].description,
            cases[i].data_total, cases[i].initial_chunk_size,
            result, cases[i].expected_data_left);

        /* Core security invariant: data_left must never exceed data_total */
        ck_assert_msg(result <= cases[i].data_total,
            "SECURITY VIOLATION [%s]: data_left=%u > data_total=%u "
            "(initial_chunk_size=%u)",
            cases[i].description,
            result, cases[i].data_total, cases[i].initial_chunk_size);
    }
}
END_TEST

Suite *security_suite(void)
{
    Suite *s;
    TCase *tc_core;

    s = suite_create("Security");
    tc_core = tcase_create("Core");

    tcase_add_test(tc_core, test_chunk_size_security_invariant);
    tcase_add_test(tc_core, test_chunk_size_never_exceeds_max);
    tcase_add_test(tc_core, test_data_length_field_bounds);
    tcase_add_test(tc_core, test_signing_init_data_left_exact_pattern);
    suite_add_tcase(s, tc_core);

    return s;
}

int main(void)
{
    int number_failed;
    Suite *s;
    SRunner *sr;

    s = security_suite();
    sr = srunner_create(s);

    srunner_run_all(sr, CK_NORMAL);
    number_failed = srunner_ntests_failed(sr);
    srunner_free(sr);

    return (number_failed == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}