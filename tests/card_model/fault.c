/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdlib.h>

#include "fault_handler.h"

/* Host builds of the model: a detected fault halts, as on the card. */
void tc_fault_handler(const char *msg) {
  fprintf(stderr, "card model fault: %s\n", msg);
  abort();
}
