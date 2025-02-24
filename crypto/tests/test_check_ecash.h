/**
 * Copyright (c) 2025 The Bitcoin ABC developers
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include "ecash/schnorr.h"

START_TEST(test_ecash_schnorr_sign_verify_digest) {
  static struct {
    const char *digest;
    const char *priv_key;
    const char *sig;
  } tests[] = {
      {
          /* Very deterministic message */
          "5255683DA567900BFD3E786ED8836A4E7763C221BF1AC20ECE2A5171B9199E8A",
          "12B004FFF7F4B69EF8650E767F18F11EDE158148B425660723B9F9A66E61F747",
          "2C56731AC2F7A7E7F11518FC7722A166B02438924CA9D8B4D111347B81D07175"
          "71846DE67AD3D913A8FDF9D8F3F73161A4C48AE81CB183B214765FEB86E255CE",
      },
  };

  const ecdsa_curve *curve = &secp256k1;
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  uint8_t priv_key[32] = {0};
  uint8_t pub_key[33] = {0};
  uint8_t result[SCHNORR_SIG_LENGTH] = {0};
  uint8_t expected[SCHNORR_SIG_LENGTH] = {0};
  int res = 0;

  for (size_t i = 0; i < sizeof(tests) / sizeof(*tests); i++) {
    memcpy(digest, fromhex(tests[i].digest), SHA256_DIGEST_LENGTH);
    memcpy(priv_key, fromhex(tests[i].priv_key), 32);
    memcpy(expected, fromhex(tests[i].sig), SCHNORR_SIG_LENGTH);

    ecdsa_get_public_key33(curve, priv_key, pub_key);

    schnorr_sign_digest(curve, priv_key, digest, result);

    ck_assert_mem_eq(expected, result, SCHNORR_SIG_LENGTH);

    res = schnorr_verify_digest(curve, pub_key, digest, result);
    ck_assert_int_eq(res, 0);
  }
}
END_TEST

START_TEST(test_ecash_schnorr_verify_digest) {
  static struct {
    const char *digest;
    const char *pub_key;
    const char *sig;
    const int res;
  } tests[] = {
      {
          /* Very deterministic message */
          "5255683DA567900BFD3E786ED8836A4E7763C221BF1AC20ECE2A5171B9199E8A",
          "030B4C866585DD868A9D62348A9CD008D6A312937048FFF31670E7E920CFC7A744",
          "2C56731AC2F7A7E7F11518FC7722A166B02438924CA9D8B4D111347B81D07175"
          "71846DE67AD3D913A8FDF9D8F3F73161A4C48AE81CB183B214765FEB86E255CE",
          0, /* Success */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 1.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "0000000000000000000000000000000000000000000000000000000000000000",
          "0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798",
          "787A848E71043D280C50470E8E1532B2DD5D20EE912A45DBDD2BD1DFBF187EF6"
          "7031A98831859DC34DFFEEDDA86831842CCD0079E1F92AF177F7F22CC1DCED05",
          0, /* Success */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 2.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
          "02DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
          "2A298DACAE57395A15D0795DDBFD1DCB564DA82B0F269BC70A74F8220429BA1D"
          "1E51A22CCEC35599B8F266912281F8365FFC2D035A230434A1A64DC59F7013FD",
          0, /* Success */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 3.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "5E2D58D8B3BCDF1ABADEC7829054F90DDA9805AAB56C77333024B9D0A508B75C",
          "03FAC2114C2FBB091527EB7C64ECB11F8021CB45E8E7809D3C0938E4B8C0E5F84B",
          "00DA9B08172A9B6F0466A2DEFD817F2D7AB437E0D253CB5395A963866B3574BE"
          "00880371D01766935B92D2AB4CD5C8A2A5837EC57FED7660773A05F0DE142380",
          0, /* Success */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 4.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "4DF3C3F68FCC83B27E9D42C90431A72499F17875C81A599B566C9889B9696703",
          "03DEFDEA4CDB677750A420FEE807EACF21EB9898AE79B9768766E4FAA04A2D4A34",
          "00000000000000000000003B78CE563F89A0ED9414F5AA28AD0D96D6795F9C63"
          "02A8DC32E64E86A333F20EF56EAC9BA30B7246D6D25E22ADB8C6BE1AEB08D49D",
          0, /* Success */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 4b.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "0000000000000000000000000000000000000000000000000000000000000000",
          "031B84C5567B126440995D3ED5AABA0565D71E1834604819FF9C17F5E9D5DD078F",
          "52818579ACA59767E3291D91B76B637BEF062083284992F2D95F564CA6CB4E35"
          "30B1DA849C8E8304ADC0CFE870660334B3CFC18E825EF1DB34CFAE3DFC5D8187",
          0, /* Success */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 6.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
          "02DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
          "2A298DACAE57395A15D0795DDBFD1DCB564DA82B0F269BC70A74F8220429BA1D"
          "FA16AEE06609280A19B67A24E1977E4697712B5FD2943914ECD5F730901B4AB7",
          6, /* R.y is not a quadratic residue */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 7.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "5E2D58D8B3BCDF1ABADEC7829054F90DDA9805AAB56C77333024B9D0A508B75C",
          "03FAC2114C2FBB091527EB7C64ECB11F8021CB45E8E7809D3C0938E4B8C0E5F84B",
          "00DA9B08172A9B6F0466A2DEFD817F2D7AB437E0D253CB5395A963866B3574BE"
          "D092F9D860F1776A1F7412AD8A1EB50DACCC222BC8C0E26B2056DF2F273EFDEC",
          5, /* Negated message hash, R.x mismatch */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 8.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "0000000000000000000000000000000000000000000000000000000000000000",
          "0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798",
          "787A848E71043D280C50470E8E1532B2DD5D20EE912A45DBDD2BD1DFBF187EF6"
          "8FCE5677CE7A623CB20011225797CE7A8DE1DC6CCD4F754A47DA6C600E59543C",
          5, /* Negated s, R.x mismatch */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 9.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
          "03DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
          "2A298DACAE57395A15D0795DDBFD1DCB564DA82B0F269BC70A74F8220429BA1D"
          "1E51A22CCEC35599B8F266912281F8365FFC2D035A230434A1A64DC59F7013FD",
          5, /* Negated P, R.x mismatch */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 10.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
          "02DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
          "2A298DACAE57395A15D0795DDBFD1DCB564DA82B0F269BC70A74F8220429BA1D"
          "8C3428869A663ED1E954705B020CBB3E7BB6AC31965B9EA4C73E227B17C5AF5A",
          4, /* s * G = e * P, R = 0 */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 11.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
          "02DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
          "4A298DACAE57395A15D0795DDBFD1DCB564DA82B0F269BC70A74F8220429BA1D"
          "1E51A22CCEC35599B8F266912281F8365FFC2D035A230434A1A64DC59F7013FD",
          5, /* R.x not on the curve, R.x mismatch */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 12.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
          "02DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
          "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC2F"
          "1E51A22CCEC35599B8F266912281F8365FFC2D035A230434A1A64DC59F7013FD",
          1, /* r = p */
      },
      {
          /*
           * From Bitcoin ABC libsecp256k1, test vector 13.
           * https://github.com/Bitcoin-ABC/secp256k1/blob/master/src/modules/schnorr/tests_impl.h
           */
          "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
          "02DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659",
          "2A298DACAE57395A15D0795DDBFD1DCB564DA82B0F269BC70A74F8220429BA1D"
          "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141",
          1, /* s = n */
      },
      {
          /* Very deterministic message */
          "5255683DA567900BFD3E786ED8836A4E7763C221BF1AC20ECE2A5171B9199E8A",
          "010B4C866585DD868A9D62348A9CD008D6A312937048FFF31670E7E920CFC7A744",
          "2C56731AC2F7A7E7F11518FC7722A166B02438924CA9D8B4D111347B81D07175"
          "71846DE67AD3D913A8FDF9D8F3F73161A4C48AE81CB183B214765FEB86E255CE",
          2, /* Invalid public key */
      },
  };

  const ecdsa_curve *curve = &secp256k1;
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  uint8_t pub_key[33] = {0};
  uint8_t signature[SCHNORR_SIG_LENGTH] = {0};
  int res = 0;

  for (size_t i = 0; i < sizeof(tests) / sizeof(*tests); i++) {
    memcpy(digest, fromhex(tests[i].digest), SHA256_DIGEST_LENGTH);
    memcpy(pub_key, fromhex(tests[i].pub_key), 33);
    memcpy(signature, fromhex(tests[i].sig), SCHNORR_SIG_LENGTH);

    res = schnorr_verify_digest(curve, pub_key, digest, signature);
    ck_assert_int_eq(res, tests[i].res);
  }
}
END_TEST
