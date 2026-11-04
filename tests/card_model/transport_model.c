/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <string.h>

#include "card_model.h"
#include "card_proto.h"
#include "card_transport.h"

/* The card model linked in-process: native tests, or an app without a card.
 * Set card_model_present to 0 to simulate a removed card. */

int card_model_present = 1;
static int card_model_tapped;

void card_disconnect(void) {
  card_model_reset();
  card_model_tapped = 0;
}

bool card_transceive(const uint8_t *command, size_t command_length,
                     uint8_t *response, size_t *response_length) {
  uint8_t buffer[CARD_RESPONSE_MAX];
  if (!card_model_present) {
    if (card_model_tapped) card_disconnect();
    return false;
  }
  card_model_tapped = 1;
  size_t length = card_model_process(command, command_length, buffer);
  if (length > *response_length) return false;
  memcpy(response, buffer, length);
  *response_length = length;
  return true;
}
