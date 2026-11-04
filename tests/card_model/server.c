/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include "card_model.h"
#include "card_proto.h"

/* Card model server: one TCP connection is one tap; the card resets when it
 * opens and when it closes. Frames are a u16 BE length and the APDU.
 *
 * It also plays the user: the card is presented some time after the firmware
 * asks for it (-t, or Enter with -i), and leaves after it has been idle for a
 * while (-k), so the next command needs a new tap. */

#define DEFAULT_MNEMONIC "all all all all all all all all all all all all"

typedef struct {
  int verbose, interactive, tap_ms, hold_ms;
} options_t;

static int io(int fd, int sending, uint8_t *buffer, size_t length) {
  while (length) {
    ssize_t n = sending ? send(fd, buffer, length, MSG_NOSIGNAL)
                        : recv(fd, buffer, length, 0);
    if (n <= 0) return 0;
    buffer += n;
    length -= n;
  }
  return 1;
}

/* The firmware asks for the card when its first command arrives. */
static int present(int fd, const options_t *o) {
  struct pollfd request = {.fd = fd, .events = POLLIN};
  if (poll(&request, 1, -1) <= 0) return 0;
  if (o->interactive) {
    fprintf(stderr, "Card requested: press Enter to tap it\n");
    int c;
    while ((c = getchar()) != '\n')
      if (c == EOF) return 0;
  } else if (o->tap_ms) {
    poll(NULL, 0, o->tap_ms);
  }
  if (o->verbose) fprintf(stderr, "card presented\n");
  return 1;
}

/* With -k, the card leaves once no command came for hold_ms. */
static int held(int fd, const options_t *o) {
  struct pollfd next = {.fd = fd, .events = POLLIN};
  return !o->hold_ms || poll(&next, 1, o->hold_ms) > 0;
}

static void serve(int fd, const options_t *o) {
  uint8_t command[CARD_COMMAND_MAX], response[CARD_RESPONSE_MAX], header[2];
  card_model_reset();
  if (!present(fd, o)) return;
  while (held(fd, o) && io(fd, 0, header, 2)) {
    size_t length = header[0] << 8 | header[1];
    if (length > sizeof(command) || !io(fd, 0, command, length)) break;
    size_t out = card_model_process(command, length, response);
    if (o->verbose)
      fprintf(stderr, "INS %02x -> SW %02x%02x\n", length > 1 ? command[1] : 0,
              response[out - 2], response[out - 1]);
    header[0] = out >> 8;
    header[1] = out;
    if (!io(fd, 1, header, 2) || !io(fd, 1, response, out)) break;
  }
  card_model_reset();
}

int main(int argc, char **argv) {
  int port = 28993;
  options_t o = {0};
  const char *mnemonic = DEFAULT_MNEMONIC;
  int opt;
  while ((opt = getopt(argc, argv, "p:m:t:k:iv")) != -1) {
    if (opt == 'p') {
      port = atoi(optarg);
    } else if (opt == 'm') {
      mnemonic = optarg;
    } else if (opt == 't') {
      o.tap_ms = atoi(optarg);
    } else if (opt == 'k') {
      o.hold_ms = atoi(optarg);
    } else if (opt == 'i') {
      o.interactive = 1;
    } else if (opt == 'v') {
      o.verbose = 1;
    } else {
      fprintf(stderr,
              "usage: %s [-p port] [-m mnemonic] [-t tap_ms] [-k hold_ms] "
              "[-i] [-v]\n"
              "  -t  present the card tap_ms after the firmware asks for it\n"
              "  -k  the card leaves after hold_ms without a command\n"
              "  -i  present the card when Enter is pressed\n",
              argv[0]);
      return 2;
    }
  }
  if (!card_model_init(mnemonic)) {
    fprintf(stderr, "Invalid mnemonic\n");
    return 1;
  }
  int listener = socket(AF_INET, SOCK_STREAM, 0), one = 1;
  setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
  struct sockaddr_in address = {.sin_family = AF_INET,
                                .sin_port = htons(port),
                                .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
  if (bind(listener, (struct sockaddr *)&address, sizeof(address)) ||
      listen(listener, 1)) {
    perror("card model");
    return 1;
  }
  fprintf(stderr, "Card model ready on 127.0.0.1:%d\n", port);
  for (;;) {
    int fd = accept(listener, NULL, NULL);
    if (fd < 0) continue;
    if (o.verbose) fprintf(stderr, "tap\n");
    serve(fd, &o);
    close(fd);
    if (o.verbose) fprintf(stderr, "card removed\n");
  }
}
