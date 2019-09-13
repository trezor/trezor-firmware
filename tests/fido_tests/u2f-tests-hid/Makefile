# Copyright 2014 Google Inc. All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

all: HIDTest U2FTest

CC ?= gcc
CXX ?= g++
CFLAGS ?= -Wall

%.o: %.c
	$(CC) -c $(CFLAGS) $^

%.o: %.cc
	$(CXX) -c $(CFLAGS) $^

HIDTest: dev.o HIDTest.cc u2f_util.o hidapi-udp.o
	$(CXX) $(CFLAGS) -o $@ $^

U2FTest: dev.o U2FTest.o u2f_util.o dsa_sig.o hidapi-udp.o p256.o p256_ec.o p256_ecdsa.o sha256.o
	$(CXX) $(CFLAGS) -o $@ $^

clean:
	rm -f *.o HIDTest U2FTest
