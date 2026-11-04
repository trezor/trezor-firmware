/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

#include "card_proto.h"
#include "card_transport.h"

/* Card model transport: one TCP connection is one tap. Frames are a u16 BE
 * length and the APDU, in both directions. TREZOR_CARD_PORT selects the
 * port on localhost (default 28993, next to the Tropic model). The model
 * answers once the card is presented, and closes the connection when the
 * card leaves. */

#define CARD_DEFAULT_PORT 28993
#define CARD_POLL_MS 50

typedef enum { CARD_OK, CARD_LOST, CARD_GAVE_UP } card_result_t;

static int card_socket = -1;

void card_disconnect(void) {
  if (card_socket >= 0) close(card_socket);
  card_socket = -1;
}

static bool card_connect(void) {
  if (card_socket >= 0) return true;
  const char *port = getenv("TREZOR_CARD_PORT");
  struct sockaddr_in address = {
      .sin_family = AF_INET,
      .sin_port = htons(port ? atoi(port) : CARD_DEFAULT_PORT),
      .sin_addr.s_addr = htonl(INADDR_LOOPBACK),
  };
  card_socket = socket(AF_INET, SOCK_STREAM, 0);
  if (card_socket < 0) return false;
  int one = 1;
  setsockopt(card_socket, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
  if (connect(card_socket, (struct sockaddr *)&address, sizeof(address))) {
    card_disconnect();
    return false;
  }
  return true;
}

static card_result_t card_send(const uint8_t *buffer, size_t length) {
  while (length) {
    ssize_t n = send(card_socket, buffer, length, MSG_NOSIGNAL);
    if (n <= 0) return CARD_LOST;
    buffer += n;
    length -= n;
  }
  return CARD_OK;
}

/* Poll, so that the vault can prompt for the card while it is not there. */
static card_result_t card_receive(uint8_t *buffer, size_t length,
                                  uint32_t *waited) {
  while (length) {
    struct pollfd fd = {.fd = card_socket, .events = POLLIN};
    int ready = poll(&fd, 1, CARD_POLL_MS);
    if (ready < 0) return CARD_LOST;
    if (!ready) {
      *waited += CARD_POLL_MS;
      if (!card_waiting(*waited)) return CARD_GAVE_UP;
      continue;
    }
    ssize_t n = recv(card_socket, buffer, length, 0);
    if (n <= 0) return CARD_LOST;
    buffer += n;
    length -= n;
  }
  return CARD_OK;
}

static card_result_t card_exchange(const uint8_t *command,
                                   size_t command_length, uint8_t *response,
                                   size_t *response_length) {
  uint8_t header[2] = {command_length >> 8, command_length};
  uint32_t waited = 0;
  card_result_t result = card_send(header, 2);
  if (result == CARD_OK) result = card_send(command, command_length);
  if (result == CARD_OK) result = card_receive(header, 2, &waited);
  if (result != CARD_OK) return result;
  size_t length = header[0] << 8 | header[1];
  if (length < 2 || length > *response_length) return CARD_LOST;
  result = card_receive(response, length, &waited);
  if (result == CARD_OK) *response_length = length;
  return result;
}

bool card_transceive(const uint8_t *command, size_t command_length,
                     uint8_t *response, size_t *response_length) {
  if (command_length > CARD_COMMAND_MAX) return false;
  bool tapped = card_socket >= 0;
  if (!card_connect()) return false;
  card_result_t result =
      card_exchange(command, command_length, response, response_length);
  /* The card left since the last command: ask for a new tap. Commands are
   * idempotent, so sending this one again is safe. */
  if (result == CARD_LOST && tapped) {
    card_disconnect();
    if (card_connect())
      result =
          card_exchange(command, command_length, response, response_length);
  }
  if (result != CARD_OK) card_disconnect();
  return result == CARD_OK;
}
