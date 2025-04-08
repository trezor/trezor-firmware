#ifndef PQCLEAN_COMMON_COMPAT_H
#define PQCLEAN_COMMON_COMPAT_H

/* This file serves to solve compatibility issues between different
 * versions of compilers.
 *
 * This file is allowed to use #ifdefs and toggle things by compiler versions.
 */

// From
// https://github.com/gcc-mirror/gcc/blob/af73a8b2027d9ab64944d7dbbb48e207d7790ce6/gcc/config/i386/avxintrin.h#L62-L71
/* Unaligned versions of the vector types */
#define UNALIGNED_VECTOR_POLYFILL_GCC                                      \
  typedef float __m256_u                                                   \
      __attribute__((__vector_size__(32), __may_alias__, __aligned__(1))); \
  typedef double __m256d_u                                                 \
      __attribute__((__vector_size__(32), __may_alias__, __aligned__(1))); \
  typedef long long __m256i_u                                              \
      __attribute__((__vector_size__(32), __may_alias__, __aligned__(1)));

/*********************************
 * Prevent branching on variable *
 *********************************/

#if defined(__GNUC__) || defined(__clang__)
// Prevent the compiler from
//    1) inferring that b is 0/1-valued, and
//    2) handling the two cases with a branch.
// This is not necessary when verify.c and kem.c are separate translation
// units, but we expect that downstream consumers will copy this code and/or
// change how it is built.
#define PQCLEAN_PREVENT_BRANCH_HACK(b) __asm__("" : "+r"(b) : /* no inputs \
                                                               */);
#else
#define PQCLEAN_PREVENT_BRANCH_HACK(b)
#endif

#define PQCLEAN_VLA(__t, __x, __s) __t __x[__s]

#endif  // PQCLEAN_COMMON_COMPAT_H
