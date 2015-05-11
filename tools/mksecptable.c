#include <stdio.h>
#include <assert.h>
#include "bignum.h"
#include "ecdsa.h"
#include "secp256k1.h"
#include "rand.h"

/*
 * This program prints the contents of the secp256k1_cp array.
 * The entry secp256k1_cp[i][j] contains the number (2*j+1)*16^i*G,
 * where G is the generator of secp256k1.
 */
int main(int __attribute__((unused)) argc, char __attribute__((unused)) **argv) {
	int i,j,k;
	curve_point ng = G256k1;
	curve_point pow2ig = G256k1;
	for (i = 0; i < 64; i++) {
		// invariants:
		//   pow2ig = 16^i * G
		//   ng     = pow2ig
		printf("\t{\n");
		for (j = 0; j < 8; j++) {
			// invariants:
			//   pow2ig = 16^i * G
			//   ng     = (2*j+1) * 16^i * G
#ifndef NDEBUG
			curve_point checkresult;
			bignum256 a;
			bn_zero(&a);
			a.val[(4*i) / 30] = ((uint32_t) 2*j+1) << ((4*i) % 30);
			bn_normalize(&a);
			point_multiply(&a, &G256k1, &checkresult);
			assert(point_is_equal(&checkresult, &ng));
#endif
			printf("\t\t/* %2d*16^%d*G: */\n\t\t{{{", 2*j + 1, i);
			// print x coordinate
			for (k = 0; k < 9; k++) {
				printf((k < 8 ? "0x%08x, " : "0x%04x"), ng.x.val[k]);
			}
			printf("}},\n\t\t {{");
			// print y coordinate
			for (k = 0; k < 9; k++) {
				printf((k < 8 ? "0x%08x, " : "0x%04x"), ng.y.val[k]);
			}
			if (j == 7) {
				printf("}}}\n\t},\n");
			} else {
				printf("}}},\n");
				point_add(&pow2ig, &ng);
			}
			point_add(&pow2ig, &ng);
		}
		pow2ig = ng;
	}
	return 0;
}
