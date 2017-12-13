/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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

#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

#define TREZOR_UDP_PORT 21324

static int fd = -1;
static struct sockaddr_in from;
static socklen_t fromlen;

void emulatorSocketInit(void) {
	fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
	if (fd < 0) {
		perror("Failed to create socket");
		exit(1);
	}

	fromlen = 0;

	struct sockaddr_in addr;
	addr.sin_family = AF_INET;
	addr.sin_port = htons(TREZOR_UDP_PORT);
	addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

	if (bind(fd, (struct sockaddr *) &addr, sizeof(addr)) != 0) {
		perror("Failed to bind socket");
		exit(1);
	}
}

size_t emulatorSocketRead(void *buffer, size_t size) {
	fromlen = sizeof(from);
	ssize_t n = recvfrom(fd, buffer, size, MSG_DONTWAIT, (struct sockaddr *) &from, &fromlen);

	if (n < 0) {
		if (errno != EAGAIN && errno != EWOULDBLOCK) {
			perror("Failed to read socket");
		}
		return 0;
	}

	static const char msg_ping[] = { 'P', 'I', 'N', 'G', 'P', 'I', 'N', 'G' };
	static const char msg_pong[] = { 'P', 'O', 'N', 'G', 'P', 'O', 'N', 'G' };

	if (n == sizeof(msg_ping) && memcmp(buffer, msg_ping, sizeof(msg_ping)) == 0) {
		emulatorSocketWrite(msg_pong, sizeof(msg_pong));
		return 0;
	}

	return n;
}

size_t emulatorSocketWrite(const void *buffer, size_t size) {
	if (fromlen > 0) {
		ssize_t n = sendto(fd, buffer, size, MSG_DONTWAIT, (const struct sockaddr *) &from, fromlen);
		if (n < 0 || ((size_t) n) != size) {
			perror("Failed to write socket");
			return 0;
		}
	}

	return size;
}
