/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef TREZOR_SECRET_LIFECYCLE_H
#define TREZOR_SECRET_LIFECYCLE_H
/* No VM calls, allocation or Python finalizers. Identities never wrap. */
void trezorcrypto_secret_reset(void);
#endif
