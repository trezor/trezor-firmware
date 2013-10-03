#include <string.h>

#include "ripemd160.h"

#define ROL(x, n)	(((x) << (n)) | ((x) >> (32-(n))))

#define F(x, y, z)		((x) ^ (y) ^ (z))
#define G(x, y, z)		(((x) & (y)) | (~(x) & (z)))
#define H(x, y, z)		(((x) | ~(y)) ^ (z))
#define IQ(x, y, z)		(((x) & (z)) | ((y) & ~(z)))
#define J(x, y, z)		((x) ^ ((y) | ~(z)))

#define FF(a, b, c, d, e, x, s)        {\
      (a) += F((b), (c), (d)) + (x);\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define GG(a, b, c, d, e, x, s)        {\
      (a) += G((b), (c), (d)) + (x) + 0x5a827999UL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define HH(a, b, c, d, e, x, s)        {\
      (a) += H((b), (c), (d)) + (x) + 0x6ed9eba1UL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define II(a, b, c, d, e, x, s)        {\
      (a) += IQ((b), (c), (d)) + (x) + 0x8f1bbcdcUL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define JJ(a, b, c, d, e, x, s)        {\
      (a) += J((b), (c), (d)) + (x) + 0xa953fd4eUL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define FFF(a, b, c, d, e, x, s)        {\
      (a) += F((b), (c), (d)) + (x);\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define GGG(a, b, c, d, e, x, s)        {\
      (a) += G((b), (c), (d)) + (x) + 0x7a6d76e9UL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define HHH(a, b, c, d, e, x, s)        {\
      (a) += H((b), (c), (d)) + (x) + 0x6d703ef3UL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define III(a, b, c, d, e, x, s)        {\
      (a) += IQ((b), (c), (d)) + (x) + 0x5c4dd124UL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }
#define JJJ(a, b, c, d, e, x, s)        {\
      (a) += J((b), (c), (d)) + (x) + 0x50a28be6UL;\
      (a) = ROL((a), (s)) + (e);\
      (c) = ROL((c), 10);\
   }

static void compress(uint32_t *MDbuf, uint32_t *X)
{
	uint32_t aa = MDbuf[0],  bb = MDbuf[1],  cc = MDbuf[2], dd = MDbuf[3],  ee = MDbuf[4];
	uint32_t aaa = MDbuf[0], bbb = MDbuf[1], ccc = MDbuf[2], ddd = MDbuf[3], eee = MDbuf[4];

	/* round 1 */
	FF(aa, bb, cc, dd, ee, X[ 0], 11);
	FF(ee, aa, bb, cc, dd, X[ 1], 14);
	FF(dd, ee, aa, bb, cc, X[ 2], 15);
	FF(cc, dd, ee, aa, bb, X[ 3], 12);
	FF(bb, cc, dd, ee, aa, X[ 4],  5);
	FF(aa, bb, cc, dd, ee, X[ 5],  8);
	FF(ee, aa, bb, cc, dd, X[ 6],  7);
	FF(dd, ee, aa, bb, cc, X[ 7],  9);
	FF(cc, dd, ee, aa, bb, X[ 8], 11);
	FF(bb, cc, dd, ee, aa, X[ 9], 13);
	FF(aa, bb, cc, dd, ee, X[10], 14);
	FF(ee, aa, bb, cc, dd, X[11], 15);
	FF(dd, ee, aa, bb, cc, X[12],  6);
	FF(cc, dd, ee, aa, bb, X[13],  7);
	FF(bb, cc, dd, ee, aa, X[14],  9);
	FF(aa, bb, cc, dd, ee, X[15],  8);

	/* round 2 */
	GG(ee, aa, bb, cc, dd, X[ 7],  7);
	GG(dd, ee, aa, bb, cc, X[ 4],  6);
	GG(cc, dd, ee, aa, bb, X[13],  8);
	GG(bb, cc, dd, ee, aa, X[ 1], 13);
	GG(aa, bb, cc, dd, ee, X[10], 11);
	GG(ee, aa, bb, cc, dd, X[ 6],  9);
	GG(dd, ee, aa, bb, cc, X[15],  7);
	GG(cc, dd, ee, aa, bb, X[ 3], 15);
	GG(bb, cc, dd, ee, aa, X[12],  7);
	GG(aa, bb, cc, dd, ee, X[ 0], 12);
	GG(ee, aa, bb, cc, dd, X[ 9], 15);
	GG(dd, ee, aa, bb, cc, X[ 5],  9);
	GG(cc, dd, ee, aa, bb, X[ 2], 11);
	GG(bb, cc, dd, ee, aa, X[14],  7);
	GG(aa, bb, cc, dd, ee, X[11], 13);
	GG(ee, aa, bb, cc, dd, X[ 8], 12);

	/* round 3 */
	HH(dd, ee, aa, bb, cc, X[ 3], 11);
	HH(cc, dd, ee, aa, bb, X[10], 13);
	HH(bb, cc, dd, ee, aa, X[14],  6);
	HH(aa, bb, cc, dd, ee, X[ 4],  7);
	HH(ee, aa, bb, cc, dd, X[ 9], 14);
	HH(dd, ee, aa, bb, cc, X[15],  9);
	HH(cc, dd, ee, aa, bb, X[ 8], 13);
	HH(bb, cc, dd, ee, aa, X[ 1], 15);
	HH(aa, bb, cc, dd, ee, X[ 2], 14);
	HH(ee, aa, bb, cc, dd, X[ 7],  8);
	HH(dd, ee, aa, bb, cc, X[ 0], 13);
	HH(cc, dd, ee, aa, bb, X[ 6],  6);
	HH(bb, cc, dd, ee, aa, X[13],  5);
	HH(aa, bb, cc, dd, ee, X[11], 12);
	HH(ee, aa, bb, cc, dd, X[ 5],  7);
	HH(dd, ee, aa, bb, cc, X[12],  5);

	/* round 4 */
	II(cc, dd, ee, aa, bb, X[ 1], 11);
	II(bb, cc, dd, ee, aa, X[ 9], 12);
	II(aa, bb, cc, dd, ee, X[11], 14);
	II(ee, aa, bb, cc, dd, X[10], 15);
	II(dd, ee, aa, bb, cc, X[ 0], 14);
	II(cc, dd, ee, aa, bb, X[ 8], 15);
	II(bb, cc, dd, ee, aa, X[12],  9);
	II(aa, bb, cc, dd, ee, X[ 4],  8);
	II(ee, aa, bb, cc, dd, X[13],  9);
	II(dd, ee, aa, bb, cc, X[ 3], 14);
	II(cc, dd, ee, aa, bb, X[ 7],  5);
	II(bb, cc, dd, ee, aa, X[15],  6);
	II(aa, bb, cc, dd, ee, X[14],  8);
	II(ee, aa, bb, cc, dd, X[ 5],  6);
	II(dd, ee, aa, bb, cc, X[ 6],  5);
	II(cc, dd, ee, aa, bb, X[ 2], 12);

	/* round 5 */
	JJ(bb, cc, dd, ee, aa, X[ 4],  9);
	JJ(aa, bb, cc, dd, ee, X[ 0], 15);
	JJ(ee, aa, bb, cc, dd, X[ 5],  5);
	JJ(dd, ee, aa, bb, cc, X[ 9], 11);
	JJ(cc, dd, ee, aa, bb, X[ 7],  6);
	JJ(bb, cc, dd, ee, aa, X[12],  8);
	JJ(aa, bb, cc, dd, ee, X[ 2], 13);
	JJ(ee, aa, bb, cc, dd, X[10], 12);
	JJ(dd, ee, aa, bb, cc, X[14],  5);
	JJ(cc, dd, ee, aa, bb, X[ 1], 12);
	JJ(bb, cc, dd, ee, aa, X[ 3], 13);
	JJ(aa, bb, cc, dd, ee, X[ 8], 14);
	JJ(ee, aa, bb, cc, dd, X[11], 11);
	JJ(dd, ee, aa, bb, cc, X[ 6],  8);
	JJ(cc, dd, ee, aa, bb, X[15],  5);
	JJ(bb, cc, dd, ee, aa, X[13],  6);

	/* parallel round 1 */
	JJJ(aaa, bbb, ccc, ddd, eee, X[ 5],  8);
	JJJ(eee, aaa, bbb, ccc, ddd, X[14],  9);
	JJJ(ddd, eee, aaa, bbb, ccc, X[ 7],  9);
	JJJ(ccc, ddd, eee, aaa, bbb, X[ 0], 11);
	JJJ(bbb, ccc, ddd, eee, aaa, X[ 9], 13);
	JJJ(aaa, bbb, ccc, ddd, eee, X[ 2], 15);
	JJJ(eee, aaa, bbb, ccc, ddd, X[11], 15);
	JJJ(ddd, eee, aaa, bbb, ccc, X[ 4],  5);
	JJJ(ccc, ddd, eee, aaa, bbb, X[13],  7);
	JJJ(bbb, ccc, ddd, eee, aaa, X[ 6],  7);
	JJJ(aaa, bbb, ccc, ddd, eee, X[15],  8);
	JJJ(eee, aaa, bbb, ccc, ddd, X[ 8], 11);
	JJJ(ddd, eee, aaa, bbb, ccc, X[ 1], 14);
	JJJ(ccc, ddd, eee, aaa, bbb, X[10], 14);
	JJJ(bbb, ccc, ddd, eee, aaa, X[ 3], 12);
	JJJ(aaa, bbb, ccc, ddd, eee, X[12],  6);

	/* parallel round 2 */
	III(eee, aaa, bbb, ccc, ddd, X[ 6],  9);
	III(ddd, eee, aaa, bbb, ccc, X[11], 13);
	III(ccc, ddd, eee, aaa, bbb, X[ 3], 15);
	III(bbb, ccc, ddd, eee, aaa, X[ 7],  7);
	III(aaa, bbb, ccc, ddd, eee, X[ 0], 12);
	III(eee, aaa, bbb, ccc, ddd, X[13],  8);
	III(ddd, eee, aaa, bbb, ccc, X[ 5],  9);
	III(ccc, ddd, eee, aaa, bbb, X[10], 11);
	III(bbb, ccc, ddd, eee, aaa, X[14],  7);
	III(aaa, bbb, ccc, ddd, eee, X[15],  7);
	III(eee, aaa, bbb, ccc, ddd, X[ 8], 12);
	III(ddd, eee, aaa, bbb, ccc, X[12],  7);
	III(ccc, ddd, eee, aaa, bbb, X[ 4],  6);
	III(bbb, ccc, ddd, eee, aaa, X[ 9], 15);
	III(aaa, bbb, ccc, ddd, eee, X[ 1], 13);
	III(eee, aaa, bbb, ccc, ddd, X[ 2], 11);

	/* parallel round 3 */
	HHH(ddd, eee, aaa, bbb, ccc, X[15],  9);
	HHH(ccc, ddd, eee, aaa, bbb, X[ 5],  7);
	HHH(bbb, ccc, ddd, eee, aaa, X[ 1], 15);
	HHH(aaa, bbb, ccc, ddd, eee, X[ 3], 11);
	HHH(eee, aaa, bbb, ccc, ddd, X[ 7],  8);
	HHH(ddd, eee, aaa, bbb, ccc, X[14],  6);
	HHH(ccc, ddd, eee, aaa, bbb, X[ 6],  6);
	HHH(bbb, ccc, ddd, eee, aaa, X[ 9], 14);
	HHH(aaa, bbb, ccc, ddd, eee, X[11], 12);
	HHH(eee, aaa, bbb, ccc, ddd, X[ 8], 13);
	HHH(ddd, eee, aaa, bbb, ccc, X[12],  5);
	HHH(ccc, ddd, eee, aaa, bbb, X[ 2], 14);
	HHH(bbb, ccc, ddd, eee, aaa, X[10], 13);
	HHH(aaa, bbb, ccc, ddd, eee, X[ 0], 13);
	HHH(eee, aaa, bbb, ccc, ddd, X[ 4],  7);
	HHH(ddd, eee, aaa, bbb, ccc, X[13],  5);

	/* parallel round 4 */
	GGG(ccc, ddd, eee, aaa, bbb, X[ 8], 15);
	GGG(bbb, ccc, ddd, eee, aaa, X[ 6],  5);
	GGG(aaa, bbb, ccc, ddd, eee, X[ 4],  8);
	GGG(eee, aaa, bbb, ccc, ddd, X[ 1], 11);
	GGG(ddd, eee, aaa, bbb, ccc, X[ 3], 14);
	GGG(ccc, ddd, eee, aaa, bbb, X[11], 14);
	GGG(bbb, ccc, ddd, eee, aaa, X[15],  6);
	GGG(aaa, bbb, ccc, ddd, eee, X[ 0], 14);
	GGG(eee, aaa, bbb, ccc, ddd, X[ 5],  6);
	GGG(ddd, eee, aaa, bbb, ccc, X[12],  9);
	GGG(ccc, ddd, eee, aaa, bbb, X[ 2], 12);
	GGG(bbb, ccc, ddd, eee, aaa, X[13],  9);
	GGG(aaa, bbb, ccc, ddd, eee, X[ 9], 12);
	GGG(eee, aaa, bbb, ccc, ddd, X[ 7],  5);
	GGG(ddd, eee, aaa, bbb, ccc, X[10], 15);
	GGG(ccc, ddd, eee, aaa, bbb, X[14],  8);

	/* parallel round 5 */
	FFF(bbb, ccc, ddd, eee, aaa, X[12] ,  8);
	FFF(aaa, bbb, ccc, ddd, eee, X[15] ,  5);
	FFF(eee, aaa, bbb, ccc, ddd, X[10] , 12);
	FFF(ddd, eee, aaa, bbb, ccc, X[ 4] ,  9);
	FFF(ccc, ddd, eee, aaa, bbb, X[ 1] , 12);
	FFF(bbb, ccc, ddd, eee, aaa, X[ 5] ,  5);
	FFF(aaa, bbb, ccc, ddd, eee, X[ 8] , 14);
	FFF(eee, aaa, bbb, ccc, ddd, X[ 7] ,  6);
	FFF(ddd, eee, aaa, bbb, ccc, X[ 6] ,  8);
	FFF(ccc, ddd, eee, aaa, bbb, X[ 2] , 13);
	FFF(bbb, ccc, ddd, eee, aaa, X[13] ,  6);
	FFF(aaa, bbb, ccc, ddd, eee, X[14] ,  5);
	FFF(eee, aaa, bbb, ccc, ddd, X[ 0] , 15);
	FFF(ddd, eee, aaa, bbb, ccc, X[ 3] , 13);
	FFF(ccc, ddd, eee, aaa, bbb, X[ 9] , 11);
	FFF(bbb, ccc, ddd, eee, aaa, X[11] , 11);

	/* combine results */
	ddd += cc + MDbuf[1];
	MDbuf[1] = MDbuf[2] + dd + eee;
	MDbuf[2] = MDbuf[3] + ee + aaa;
	MDbuf[3] = MDbuf[4] + aa + bbb;
	MDbuf[4] = MDbuf[0] + bb + ccc;
	MDbuf[0] = ddd;
}

void ripemd160(const uint8_t *msg, uint32_t msg_len, uint8_t *hash)
{
	uint32_t i;
	int j;
	uint32_t digest[5] = {0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0UL};

	for (i = 0; i < (msg_len >> 6); ++i) {
		uint32_t chunk[16];

		for (j = 0; j < 16; ++j) {
			chunk[j] = (uint32_t)(*(msg++));
			chunk[j] |= (uint32_t)(*(msg++)) << 8;
			chunk[j] |= (uint32_t)(*(msg++)) << 16;
			chunk[j] |= (uint32_t)(*(msg++)) << 24;
		}

		compress (digest, chunk);
	}

	// Last chunk
	{
		uint32_t chunk[16] = {0};

		for (i = 0; i < (msg_len & 63); ++i) {
			chunk[i >> 2] ^= (uint32_t) *msg++ << ((i&3) << 3);
		}

		chunk[(msg_len >> 2)&15] ^= (uint32_t)1 << (8*(msg_len&3) + 7);

		if ((msg_len & 63) > 55) {
			compress (digest, chunk);
			memset (chunk, 0, 64);
		}

		chunk[14] = msg_len << 3;
		chunk[15] = (msg_len >> 29);
		compress (digest, chunk);
	}

	for (i = 0; i < 5; ++i) {
		*(hash++) = digest[i];
		*(hash++) = digest[i] >> 8;
		*(hash++) = digest[i] >> 16;
		*(hash++) = digest[i] >> 24;
	}
}
