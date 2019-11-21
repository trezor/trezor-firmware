/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 alepop <alepooop@gmail.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "vsys.h"
#include "bitmaps.h"
#include "crypto.h"
#include "curves.h"
#include "fsm.h"
#include "gettext.h"
#include "layout2.h"
#include "messages.pb.h"
#include "protect.h"
#include "util.h"

#define MAX_AMOUNT_SIZE 20


void vsys_sign_tx(const HDNode *node, VsysSignTx *msg, VsysSignedTx *resp) {
  memcpy(msg->senderPublicKey.bytes, &node->public_key[1], 32);
  resp->signature.size = 64;
}

// Helpers
void vsys_get_address_from_public_key(const uint8_t *public_key,
                                      char *address) {
  uint8_t i;
  for (i=0; i<MAX_VSYS_ADDRESS_SIZE; i++) {
    address[i] = public_key[i]; //TODO: implement public_key -> address
  }
}

static void vsys_format_amount(uint64_t value, char *formated_value) {
  bn_format_uint64(value, NULL, " VSYS", 8, 0, false, formated_value,
                   MAX_AMOUNT_SIZE);
}

// Layouts
void layoutVsysPublicKey(const uint8_t *pubkey) {
  const char **str = split_message_hex(pubkey, 32);
  layoutDialogSwipe(&bmp_icon_question, NULL, _("Continue"), NULL,
                    _("Public Key:"), str[0], str[1], str[2], str[3], NULL);
}

void layoutVsysVerifyAddress(const char *address) {
  const char **str =
      split_message((const uint8_t *)address, strlen(address), 10);
  layoutDialogSwipe(&bmp_icon_info, _("Cancel"), _("Confirm"),
                    _("Confirm address?"), _("Message signed by:"), str[0],
                    str[1], NULL, NULL, NULL);
}

void layoutVsysRequireConfirmTx(char *recipient_id, uint64_t amount) {
  char formated_amount[MAX_AMOUNT_SIZE] = {0};
  const char **str =
      split_message((const uint8_t *)recipient_id, strlen(recipient_id), 16);
  vsys_format_amount(amount, formated_amount);
  layoutDialogSwipe(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
                    _("Confirm sending"), formated_amount, _("to:"), str[0],
                    str[1], NULL);
}