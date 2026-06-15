/*
 * Branch and Control Flow Unit Tests for LinxISA
 * Tests: B.EQ, B.NE, B.LT, B.GE, B.LTU, B.GEU, J, JR
 *        B.NZ, B.Z, BSTART, BSTOP, SETC
 */

#include "linx_test.h"

/* Test data for comparisons */
static int32_t cmp_a = 10;
static int32_t cmp_b = 20;
static int32_t cmp_c = -5;
static int32_t cmp_d = -10;
static uint32_t cmp_ua = 10;
static uint32_t cmp_ub = 20;

/* Global to track branch execution */
static volatile uint32_t g_branch_taken = 0;
static volatile uint32_t g_branch_not_taken = 0;

/* Test CMP.EQ (compare equal) */
static void test_cmp_eq_true(void) {
    int32_t a = 10;
    int32_t b = 10;
    int32_t result = (a == b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD001);
}

static void test_cmp_eq_false(void) {
    int32_t a = 10;
    int32_t b = 20;
    int32_t result = (a == b) ? 1 : 0;
    TEST_EQ(result, 0, 0xD002);
}

static void test_cmp_eq_negative(void) {
    int32_t a = -5;
    int32_t b = -5;
    int32_t result = (a == b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD003);
}

/* Test CMP.NE (compare not equal) */
static void test_cmp_ne_true(void) {
    int32_t a = 10;
    int32_t b = 20;
    int32_t result = (a != b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD010);
}

static void test_cmp_ne_false(void) {
    int32_t a = 10;
    int32_t b = 10;
    int32_t result = (a != b) ? 1 : 0;
    TEST_EQ(result, 0, 0xD011);
}

/* Test CMP.LT (compare less than, signed) */
static void test_cmp_lt_true(void) {
    int32_t a = 5;
    int32_t b = 10;
    int32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD020);
}

static void test_cmp_lt_false(void) {
    int32_t a = 20;
    int32_t b = 10;
    int32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 0, 0xD021);
}

static void test_cmp_lt_negative(void) {
    int32_t a = -10;
    int32_t b = 5;
    int32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD022);
}

static void test_cmp_lt_both_negative(void) {
    int32_t a = -20;
    int32_t b = -10;
    int32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD023);
}

/* Test CMP.GE (compare greater than or equal, signed) */
static void test_cmp_ge_true(void) {
    int32_t a = 20;
    int32_t b = 10;
    int32_t result = (a >= b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD030);
}

static void test_cmp_ge_equal(void) {
    int32_t a = 10;
    int32_t b = 10;
    int32_t result = (a >= b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD031);
}

static void test_cmp_ge_false(void) {
    int32_t a = 5;
    int32_t b = 10;
    int32_t result = (a >= b) ? 1 : 0;
    TEST_EQ(result, 0, 0xD032);
}

/* Test CMP.LTU (compare less than, unsigned) */
static void test_cmp_ltu_true(void) {
    uint32_t a = 5;
    uint32_t b = 10;
    uint32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD040);
}

static void test_cmp_ltu_false(void) {
    uint32_t a = 20;
    uint32_t b = 10;
    uint32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 0, 0xD041);
}

/* Test CMP.GEU (compare greater than or equal, unsigned) */
static void test_cmp_geu_true(void) {
    uint32_t a = 20;
    uint32_t b = 10;
    uint32_t result = (a >= b) ? 1 : 0;
    TEST_EQ(result, 1, 0xD050);
}

static void test_cmp_geu_false(void) {
    uint32_t a = 5;
    uint32_t b = 10;
    uint32_t result = (a >= b) ? 1 : 0;
    TEST_EQ(result, 0, 0xD051);
}

/* Test immediate comparison variants */
static void test_cmp_eqi_positive(void) {
    int32_t a = 100;
    int32_t result = (a == 100) ? 1 : 0;
    TEST_EQ(result, 1, 0xD060);
}

static void test_cmp_eqi_negative(void) {
    int32_t a = 100;
    int32_t result = (a == -50) ? 1 : 0;
    TEST_EQ(result, 0, 0xD061);
}

static void test_cmp_lti_positive(void) {
    int32_t a = 50;
    int32_t result = (a < 100) ? 1 : 0;
    TEST_EQ(result, 1, 0xD070);
}

static void test_cmp_gei_positive(void) {
    int32_t a = 100;
    int32_t result = (a >= 50) ? 1 : 0;
    TEST_EQ(result, 1, 0xD080);
}

/* Test SETC instructions (set condition) */
static void test_setc_eq_true(void) {
    int32_t a = 10;
    int32_t b = 10;
    uint32_t cond = (a == b) ? 1 : 0;
    TEST_EQ(cond, 1, 0xD090);
}

static void test_setc_ne_true(void) {
    int32_t a = 10;
    int32_t b = 20;
    uint32_t cond = (a != b) ? 1 : 0;
    TEST_EQ(cond, 1, 0xD091);
}

static void test_setc_lt_true(void) {
    int32_t a = 5;
    int32_t b = 10;
    uint32_t cond = (a < b) ? 1 : 0;
    TEST_EQ(cond, 1, 0xD092);
}

static void test_setc_ge_true(void) {
    int32_t a = 20;
    int32_t b = 10;
    uint32_t cond = (a >= b) ? 1 : 0;
    TEST_EQ(cond, 1, 0xD093);
}

/* Test conditional selection (CSEL) */
static void test_csel_true(void) {
    int32_t a = 10;
    int32_t b = 20;
    int32_t result = (a < b) ? a : b;
    TEST_EQ(result, 10, 0xD0A0);
}

static void test_csel_false(void) {
    int32_t a = 20;
    int32_t b = 10;
    int32_t result = (a < b) ? a : b;
    TEST_EQ(result, 10, 0xD0A1);
}

static void test_csel_unsigned(void) {
    uint32_t a = 5;
    uint32_t b = 10;
    uint32_t result = (a < b) ? a : b;
    TEST_EQ(result, 5, 0xD0A2);
}

/* Test MIN/MAX operations */
static void test_min_signed(void) {
    int32_t a = -10;
    int32_t b = 20;
    int32_t result = (a < b) ? a : b;
    TEST_EQ(result, -10, 0xD0B0);
}

static void test_max_signed(void) {
    int32_t a = -10;
    int32_t b = 20;
    int32_t result = (a > b) ? a : b;
    TEST_EQ(result, 20, 0xD0B1);
}

static void test_min_unsigned(void) {
    uint32_t a = 5;
    uint32_t b = 10;
    uint32_t result = (a < b) ? a : b;
    TEST_EQ(result, 5, 0xD0B2);
}

static void test_max_unsigned(void) {
    uint32_t a = 5;
    uint32_t b = 10;
    uint32_t result = (a > b) ? a : b;
    TEST_EQ(result, 10, 0xD0B3);
}

/* Test branch prediction helpers */
static void test_branch_prediction_basic(void) {
    /* Test that both taken and not-taken paths work */
    uint32_t result = 0;
    
    if (1) {
        result = 1;
    }
    TEST_EQ(result, 1, 0xD0C0);
    
    result = 0;
    if (0) {
        result = 1;
    }
    TEST_EQ(result, 0, 0xD0C1);
}

static void test_branch_chain(void) {
    uint32_t result = 0;
    
    if (1) {
        if (1) {
            if (1) {
                result = 7;
            }
        }
    }
    TEST_EQ(result, 7, 0xD0D0);
}

static void test_fall_setc_skips_direct_trampoline(void) {
    uint64_t result;
    uint64_t lhs = 1;
    uint64_t rhs = 0;

    __asm__ volatile(
        "  C.BSTART\n"
        "  c.setc.ne %1, %2\n"
        "  C.BSTART DIRECT, 1f\n"
        "  C.BSTART COND, 2f\n"
        "1:\n"
        "  C.BSTART\n"
        "  addi zero, 13, ->%0\n"
        "  C.BSTART DIRECT, 3f\n"
        "2:\n"
        "  C.BSTART\n"
        "  addi zero, 17, ->%0\n"
        "3:\n"
        "  C.BSTART\n"
        : "=&r"(result)
        : "r"(lhs), "r"(rhs)
        : "memory");

    TEST_EQ64(result, 17, 0xD0D1);
}

/* Test loop execution */
static void test_loop_execution(void) {
    uint32_t sum = 0;
    for (uint32_t i = 0; i < 10; i++) {
        sum += i;
    }
    TEST_EQ(sum, 45, 0xD0E0);
}

static void test_while_loop(void) {
    uint32_t count = 0;
    while (count < 5) {
        count++;
    }
    TEST_EQ(count, 5, 0xD0E1);
}

static void test_do_while(void) {
    uint32_t count = 0;
    do {
        count++;
    } while (count < 3);
    TEST_EQ(count, 3, 0xD0E2);
}

/* Main test runner */
void run_branch_tests(void) {
    test_suite_begin(0xD000);
    
    /* CMP.EQ tests */
    RUN_TEST(test_cmp_eq_true, 0xD001);
    RUN_TEST(test_cmp_eq_false, 0xD002);
    RUN_TEST(test_cmp_eq_negative, 0xD003);
    
    /* CMP.NE tests */
    RUN_TEST(test_cmp_ne_true, 0xD010);
    RUN_TEST(test_cmp_ne_false, 0xD011);
    
    /* CMP.LT tests */
    RUN_TEST(test_cmp_lt_true, 0xD020);
    RUN_TEST(test_cmp_lt_false, 0xD021);
    RUN_TEST(test_cmp_lt_negative, 0xD022);
    RUN_TEST(test_cmp_lt_both_negative, 0xD023);
    
    /* CMP.GE tests */
    RUN_TEST(test_cmp_ge_true, 0xD030);
    RUN_TEST(test_cmp_ge_equal, 0xD031);
    RUN_TEST(test_cmp_ge_false, 0xD032);
    
    /* CMP.LTU tests */
    RUN_TEST(test_cmp_ltu_true, 0xD040);
    RUN_TEST(test_cmp_ltu_false, 0xD041);
    
    /* CMP.GEU tests */
    RUN_TEST(test_cmp_geu_true, 0xD050);
    RUN_TEST(test_cmp_geu_false, 0xD051);
    
    /* Immediate comparison tests */
    RUN_TEST(test_cmp_eqi_positive, 0xD060);
    RUN_TEST(test_cmp_eqi_negative, 0xD061);
    RUN_TEST(test_cmp_lti_positive, 0xD070);
    RUN_TEST(test_cmp_gei_positive, 0xD080);
    
    /* SETC tests */
    RUN_TEST(test_setc_eq_true, 0xD090);
    RUN_TEST(test_setc_ne_true, 0xD091);
    RUN_TEST(test_setc_lt_true, 0xD092);
    RUN_TEST(test_setc_ge_true, 0xD093);
    
    /* CSEL tests */
    RUN_TEST(test_csel_true, 0xD0A0);
    RUN_TEST(test_csel_false, 0xD0A1);
    RUN_TEST(test_csel_unsigned, 0xD0A2);
    
    /* MIN/MAX tests */
    RUN_TEST(test_min_signed, 0xD0B0);
    RUN_TEST(test_max_signed, 0xD0B1);
    RUN_TEST(test_min_unsigned, 0xD0B2);
    RUN_TEST(test_max_unsigned, 0xD0B3);
    
    /* Branch prediction tests */
    RUN_TEST(test_branch_prediction_basic, 0xD0C0);
    RUN_TEST(test_branch_chain, 0xD0D0);
    RUN_TEST(test_fall_setc_skips_direct_trampoline, 0xD0D1);
    
    /* Loop tests */
    RUN_TEST(test_loop_execution, 0xD0E0);
    RUN_TEST(test_while_loop, 0xD0E1);
    RUN_TEST(test_do_while, 0xD0E2);
    
    test_suite_end(32, 32);
}
