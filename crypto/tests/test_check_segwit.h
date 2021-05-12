#include "segwit_addr.h"

static const char* valid_checksum[] = {
    "A12UEL5L",
    "an83characterlonghumanreadablepartthatcontainsthenumber1andtheexcludedchar"
    "actersbio1tt5tgs",
    "abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw",
    "11qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
    "qqqqqqqqqqc8247j",
    "split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w",
};

static const char* invalid_checksum[] = {
    " 1nwldj5",
    "\x7f"
    "1axkwrx",
    "an84characterslonghumanreadablepartthatcontainsthenumber1andtheexcludedcha"
    "ractersbio1569pvx",
    "pzry9x0s0muk",
    "1pzry9x0s0muk",
    "x1b4n0q5v",
    "li1dgmt3",
    "de1lg7wt\xff",
};

struct valid_address_data {
  const char* address;
  size_t scriptPubKeyLen;
  const uint8_t scriptPubKey[42];
};

struct invalid_address_data {
  const char* hrp;
  int version;
  size_t program_length;
};

static struct valid_address_data valid_address[] = {
    {"BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4",
     22,
     {0x00, 0x14, 0x75, 0x1e, 0x76, 0xe8, 0x19, 0x91, 0x96, 0xd4, 0x54,
      0x94, 0x1c, 0x45, 0xd1, 0xb3, 0xa3, 0x23, 0xf1, 0x43, 0x3b, 0xd6}},
    {"tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7",
     34,
     {0x00, 0x20, 0x18, 0x63, 0x14, 0x3c, 0x14, 0xc5, 0x16, 0x68, 0x04, 0xbd,
      0x19, 0x20, 0x33, 0x56, 0xda, 0x13, 0x6c, 0x98, 0x56, 0x78, 0xcd, 0x4d,
      0x27, 0xa1, 0xb8, 0xc6, 0x32, 0x96, 0x04, 0x90, 0x32, 0x62}},
    {"bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7k7grpl"
     "x",
     42,
     {0x51, 0x28, 0x75, 0x1e, 0x76, 0xe8, 0x19, 0x91, 0x96, 0xd4, 0x54,
      0x94, 0x1c, 0x45, 0xd1, 0xb3, 0xa3, 0x23, 0xf1, 0x43, 0x3b, 0xd6,
      0x75, 0x1e, 0x76, 0xe8, 0x19, 0x91, 0x96, 0xd4, 0x54, 0x94, 0x1c,
      0x45, 0xd1, 0xb3, 0xa3, 0x23, 0xf1, 0x43, 0x3b, 0xd6}},
    {"BC1SW50QA3JX3S", 4, {0x60, 0x02, 0x75, 0x1e}},
    {"bc1zw508d6qejxtdg4y5r3zarvaryvg6kdaj",
     18,
     {0x52, 0x10, 0x75, 0x1e, 0x76, 0xe8, 0x19, 0x91, 0x96, 0xd4, 0x54, 0x94,
      0x1c, 0x45, 0xd1, 0xb3, 0xa3, 0x23}},
    {"tb1qqqqqp399et2xygdj5xreqhjjvcmzhxw4aywxecjdzew6hylgvsesrxh6hy",
     34,
     {0x00, 0x20, 0x00, 0x00, 0x00, 0xc4, 0xa5, 0xca, 0xd4, 0x62, 0x21, 0xb2,
      0xa1, 0x87, 0x90, 0x5e, 0x52, 0x66, 0x36, 0x2b, 0x99, 0xd5, 0xe9, 0x1c,
      0x6c, 0xe2, 0x4d, 0x16, 0x5d, 0xab, 0x93, 0xe8, 0x64, 0x33}}};

static const char* invalid_address[] = {
    "tc1qw508d6qejxtdg4y5r3zarvary0c5xw7kg3g4ty",
    "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5",
    "BC13W508D6QEJXTDG4Y5R3ZARVARY0C5XW7KN40WF2",
    "bc1rw5uspcuh",
    "bc10w508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kw5rljs"
    "90",
    "BC1QR508D6QEJXTDG4Y5R3ZARVARYV98GJ9P",
    "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sL5k7",
    "bc1zw508d6qejxtdg4y5r3zarvaryvqyzf3du",
    "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3pjxtptv",
    "bc1gmk9yu",
};

static struct invalid_address_data invalid_address_enc[] = {
    {"BC", 0, 20}, {"bc", 0, 21}, {"bc", 17, 32}, {"bc", 1, 1}, {"bc", 16, 41},
};

static void segwit_scriptpubkey(uint8_t* scriptpubkey, size_t* scriptpubkeylen,
                                int witver, const uint8_t* witprog,
                                size_t witprog_len) {
  scriptpubkey[0] = witver ? (0x50 + witver) : 0;
  scriptpubkey[1] = witprog_len;
  memcpy(scriptpubkey + 2, witprog, witprog_len);
  *scriptpubkeylen = witprog_len + 2;
}

START_TEST(test_segwit) {
  size_t i;
  for (i = 0; i < sizeof(valid_checksum) / sizeof(valid_checksum[0]); ++i) {
    uint8_t data[82];
    char rebuild[92];
    char hrp[84];
    size_t data_len;
    int res = bech32_decode(hrp, data, &data_len, valid_checksum[i]);
    ck_assert_int_eq(res, 1);
    res = bech32_encode(rebuild, hrp, data, data_len);
    ck_assert_int_eq(res, 1);
    ck_assert_int_eq(my_strncasecmp(rebuild, valid_checksum[i], 92), 0);
  }
  for (i = 0; i < sizeof(invalid_checksum) / sizeof(invalid_checksum[0]); ++i) {
    uint8_t data[82];
    char hrp[84];
    size_t data_len;
    int res = bech32_decode(hrp, data, &data_len, invalid_checksum[i]);
    ck_assert_int_eq(res, 0);
  }
  for (i = 0; i < sizeof(valid_address) / sizeof(valid_address[0]); ++i) {
    uint8_t witprog[40];
    size_t witprog_len;
    int witver;
    const char* hrp = "bc";
    uint8_t scriptpubkey[42];
    size_t scriptpubkey_len;
    char rebuild[93];
    int ret = segwit_addr_decode(&witver, witprog, &witprog_len, hrp,
                                 valid_address[i].address);
    if (!ret) {
      hrp = "tb";
      ret = segwit_addr_decode(&witver, witprog, &witprog_len, hrp,
                               valid_address[i].address);
    }
    ck_assert_int_eq(ret, 1);
    segwit_scriptpubkey(scriptpubkey, &scriptpubkey_len, witver, witprog,
                        witprog_len);
    ck_assert_uint_eq(scriptpubkey_len, valid_address[i].scriptPubKeyLen);
    ck_assert_int_eq(
        memcmp(scriptpubkey, valid_address[i].scriptPubKey, scriptpubkey_len),
        0);
    ck_assert_int_eq(
        segwit_addr_encode(rebuild, hrp, witver, witprog, witprog_len), 1);
    ck_assert_int_eq(my_strncasecmp(valid_address[i].address, rebuild, 93), 0);
  }
  for (i = 0; i < sizeof(invalid_address) / sizeof(invalid_address[0]); ++i) {
    uint8_t witprog[40];
    size_t witprog_len;
    int witver;
    int ret = segwit_addr_decode(&witver, witprog, &witprog_len, "bc",
                                 invalid_address[i]);
    ck_assert_int_eq(ret, 0);
    ret = segwit_addr_decode(&witver, witprog, &witprog_len, "tb",
                             invalid_address[i]);
    ck_assert_int_eq(ret, 0);
  }
  for (i = 0; i < sizeof(invalid_address_enc) / sizeof(invalid_address_enc[0]);
       ++i) {
    char rebuild[93];
    static const uint8_t program[42] = {0};
    int ret = segwit_addr_encode(rebuild, invalid_address_enc[i].hrp,
                                 invalid_address_enc[i].version, program,
                                 invalid_address_enc[i].program_length);
    ck_assert_int_eq(ret, 0);
  }
}
END_TEST
