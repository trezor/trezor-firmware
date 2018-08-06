#!/bin/sh
# libsodium-dev replacement
#
# The purpose of this file is to install libsodium in
# the Travis CI environment. Outside this environment,
# you would probably not want to install it like this.

set -e
export LIBSODIUM_VER="1.0.16"

# check if libsodium is already installed
if [ ! -d "$HOME/libsodium/lib" ]; then
  wget "https://github.com/jedisct1/libsodium/releases/download/${LIBSODIUM_VER}/libsodium-${LIBSODIUM_VER}.tar.gz"
  tar xvfz "libsodium-${LIBSODIUM_VER}.tar.gz"
  cd "libsodium-${LIBSODIUM_VER}"
  ./configure --prefix=$HOME/libsodium
  make
  make install
else
  echo 'Using cached directory.'
fi
