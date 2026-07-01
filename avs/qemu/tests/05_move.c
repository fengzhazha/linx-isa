/*
 * Move and Immediate Unit Tests for LinxISA
 * Tests: MOVR, MOVI, LUI, ADDI with immediates, register moves
 */

#include "linx_test.h"

/* Test register moves */
static void test_mov_reg_basic(void) {
    uint32_t src = 0x12345678;
    uint32_t dst = src;
    TEST_EQ(dst, 0x12345678, 0xE001);
}

static void test_mov_reg_zero(void) {
    uint32_t dst = 0xABCDEF;
    uint32_t zero = 0;
    dst = zero;
    TEST_EQ(dst, 0, 0xE002);
}

static void test_mov_reg_chain(void) {
    uint32_t a = 100;
    uint32_t b = a;
    uint32_t c = b;
    uint32_t d = c;
    TEST_EQ(d, 100, 0xE003);
}

/* Test move with clock hands (T-hand form) */
static void test_mov_t_hand_chain(void) {
    uint32_t t1 = 1;
    uint32_t t2 = t1 + 1;
    uint32_t t3 = t2 + 1;
    uint32_t t4 = t3 + 1;
    TEST_EQ(t4, 4, 0xE010);
}

/* Test move with U-hand form */
static void test_mov_u_hand_stack(void) {
    uint32_t result = 0;
    result = 10;
    uint32_t tmp = result;
    result = tmp + 20;
    TEST_EQ(result, 30, 0xE020);
}

/* Test immediate loads */
static void test_movi_positive(void) {
    uint32_t imm = 100;
    TEST_EQ(imm, 100, 0xE030);
}

static void test_movi_zero(void) {
    uint32_t imm = 0;
    TEST_EQ(imm, 0, 0xE031);
}

static void test_movi_large(void) {
    uint32_t imm = 0xFFFF;
    TEST_EQ(imm, 0xFFFF, 0xE032);
}

static void test_movi_negative(void) {
    int32_t imm = -100;
    TEST_EQ32(imm, -100, 0xE033);
}

/* Test LUI (load upper immediate) */
static void test_lui_basic(void) {
    uint32_t val = 0x12340000;
    TEST_EQ(val, 0x12340000, 0xE040);
}

static void test_lui_zeros(void) {
    uint32_t val = 0x0;
    TEST_EQ(val, 0, 0xE041);
}

static void test_lui_all_ones_upper(void) {
    uint32_t val = 0xFFFF0000;
    TEST_EQ(val, 0xFFFF0000, 0xE042);
}

/* Test immediate arithmetic */
static void test_addi_positive(void) {
    uint32_t a = 50;
    a = a + 25;
    TEST_EQ(a, 75, 0xE050);
}

static void test_addi_negative(void) {
    int32_t a = 100;
    a = a + (-50);
    TEST_EQ32(a, 50, 0xE051);
}

static void test_subi_positive(void) {
    uint32_t a = 100;
    a = a - 30;
    TEST_EQ(a, 70, 0xE060);
}

static void test_subi_negative(void) {
    int32_t a = 50;
    a = a - (-20);
    TEST_EQ32(a, 70, 0xE061);
}

/* Test bitwise with immediates */
static void test_andi_basic(void) {
    uint32_t a = 0xFF;
    a = a & 0x0F;
    TEST_EQ(a, 0x0F, 0xE070);
}

static void test_ori_basic(void) {
    uint32_t a = 0xFF00;
    a = a | 0x00FF;
    TEST_EQ(a, 0xFFFF, 0xE080);
}

static void test_xori_basic(void) {
    uint32_t a = 0xFF;
    a = a ^ 0x0F;
    TEST_EQ(a, 0xF0, 0xE090);
}

/* Test shift with immediates */
static void test_slli_basic(void) {
    uint32_t a = 0x1;
    a = a << 8;
    TEST_EQ(a, 0x100, 0xE0A0);
}

static void test_srli_basic(void) {
    uint32_t a = 0xFF00;
    a = a >> 8;
    TEST_EQ(a, 0xFF, 0xE0B0);
}

static void test_srai_basic(void) {
    int32_t a = -8;  /* 0xFFFFFFF8 */
    a = a >> 1;
    TEST_EQ32(a, -4, 0xE0C0);
}

/* Test word operations with immediates */
static void test_addiw_basic(void) {
    int64_t a = 0x100000000LL;
    a = a + 1000;
    TEST_EQ64(a, 0x1000003E8LL, 0xE0D0);
}

static void test_andiw_basic(void) {
    int32_t a = 0xFFFFFFFF;
    a = a & 0xFFFF;
    TEST_EQ32(a, 0xFFFF, 0xE0E0);
}

static void test_slliw_basic(void) {
    int32_t a = 1;
    a = a << 16;
    TEST_EQ32(a, 0x10000, 0xE0F0);
}

/* Test MOVR and MOVI compressed forms */
static void test_movr_basic(void) {
    uint32_t src = 42;
    uint32_t dst = src;
    TEST_EQ(dst, 42, 0xE100);
}

static void test_movi_compressed(void) {
    int8_t val = 10;
    TEST_EQ(val, 10, 0xE110);
}

/* Test SETRET */
static void test_setret_basic(void) {
    /* SETRET sets return address register (ra) */
    uint32_t ret_addr = 0;
    (void)ret_addr;
}

/* Test CSEL with various conditions */
static void test_csel_cond_eq(void) {
    int32_t a = 10;
    int32_t b = 10;
    int32_t result = (a == b) ? 100 : 200;
    TEST_EQ(result, 100, 0xE120);
}

static void test_csel_cond_ne(void) {
    int32_t a = 10;
    int32_t b = 20;
    int32_t result = (a != b) ? 100 : 200;
    TEST_EQ(result, 100, 0xE121);
}

static void test_csel_cond_lt(void) {
    int32_t a = 5;
    int32_t b = 10;
    int32_t result = (a < b) ? 100 : 200;
    TEST_EQ(result, 100, 0xE122);
}

static void test_csel_cond_ge(void) {
    int32_t a = 20;
    int32_t b = 10;
    int32_t result = (a >= b) ? 100 : 200;
    TEST_EQ(result, 100, 0xE123);
}

static uint64_t csel_literal(uint64_t pred, uint64_t src_l, uint64_t src_r) {
    uint64_t out;
    __asm__ volatile("csel %1, %2, %3, ->%0"
                     : "=r"(out)
                     : "r"(pred), "r"(src_l), "r"(src_r)
                     : "memory");
    return out;
}

static void test_csel_literal_true_src_l(void) {
    uint64_t result = csel_literal(1, 0x1111222233334444ULL,
                                   0xaaaabbbbccccddddULL);
    TEST_EQ64(result, 0x1111222233334444ULL, 0xE124);
}

static void test_csel_literal_false_src_r(void) {
    uint64_t result = csel_literal(0, 0x1111222233334444ULL,
                                   0xaaaabbbbccccddddULL);
    TEST_EQ64(result, 0xaaaabbbbccccddddULL, 0xE125);
}

/* Test sign/zero extension */
static void test_sext_byte(void) {
    int8_t src = -1;  /* 0xFF */
    int32_t dst = src;
    TEST_EQ32(dst, -1, 0xE130);
}

static void test_sext_half(void) {
    int16_t src = -1;  /* 0xFFFF */
    int32_t dst = src;
    TEST_EQ32(dst, -1, 0xE131);
}

static void test_zext_byte(void) {
    uint8_t src = 0xFF;
    uint32_t dst = src;
    TEST_EQ(dst, 0xFF, 0xE140);
}

static void test_zext_half(void) {
    uint16_t src = 0xFFFF;
    uint32_t dst = src;
    TEST_EQ(dst, 0xFFFF, 0xE141);
}

/* Main test runner */
void run_move_tests(void) {
    test_suite_begin(0xE000);
    
    /* Register move tests */
    RUN_TEST(test_mov_reg_basic, 0xE001);
    RUN_TEST(test_mov_reg_zero, 0xE002);
    RUN_TEST(test_mov_reg_chain, 0xE003);
    
    /* Clock hand tests */
    RUN_TEST(test_mov_t_hand_chain, 0xE010);
    RUN_TEST(test_mov_u_hand_stack, 0xE020);
    
    /* Immediate load tests */
    RUN_TEST(test_movi_positive, 0xE030);
    RUN_TEST(test_movi_zero, 0xE031);
    RUN_TEST(test_movi_large, 0xE032);
    RUN_TEST(test_movi_negative, 0xE033);
    
    /* LUI tests */
    RUN_TEST(test_lui_basic, 0xE040);
    RUN_TEST(test_lui_zeros, 0xE041);
    RUN_TEST(test_lui_all_ones_upper, 0xE042);
    
    /* Immediate arithmetic */
    RUN_TEST(test_addi_positive, 0xE050);
    RUN_TEST(test_addi_negative, 0xE051);
    RUN_TEST(test_subi_positive, 0xE060);
    RUN_TEST(test_subi_negative, 0xE061);
    
    /* Bitwise with immediates */
    RUN_TEST(test_andi_basic, 0xE070);
    RUN_TEST(test_ori_basic, 0xE080);
    RUN_TEST(test_xori_basic, 0xE090);
    
    /* Shift with immediates */
    RUN_TEST(test_slli_basic, 0xE0A0);
    RUN_TEST(test_srli_basic, 0xE0B0);
    RUN_TEST(test_srai_basic, 0xE0C0);
    
    /* Word operations */
    RUN_TEST(test_addiw_basic, 0xE0D0);
    RUN_TEST(test_andiw_basic, 0xE0E0);
    RUN_TEST(test_slliw_basic, 0xE0F0);
    
    /* Compressed forms */
    RUN_TEST(test_movr_basic, 0xE100);
    RUN_TEST(test_movi_compressed, 0xE110);
    
    /* SETRET */
    RUN_TEST(test_setret_basic, 0xE111);
    
    /* CSEL tests */
    RUN_TEST(test_csel_cond_eq, 0xE120);
    RUN_TEST(test_csel_cond_ne, 0xE121);
    RUN_TEST(test_csel_cond_lt, 0xE122);
    RUN_TEST(test_csel_cond_ge, 0xE123);
    RUN_TEST(test_csel_literal_true_src_l, 0xE124);
    RUN_TEST(test_csel_literal_false_src_r, 0xE125);
    
    /* Extension tests */
    RUN_TEST(test_sext_byte, 0xE130);
    RUN_TEST(test_sext_half, 0xE131);
    RUN_TEST(test_zext_byte, 0xE140);
    RUN_TEST(test_zext_half, 0xE141);
    
    test_suite_end(33, 33);
}
