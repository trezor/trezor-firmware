#/bin/bash

export EMULATOR=1
export PIZERO=1
export PYTHON=python3.7
export RANDOM_DEV_FILE="/dev/random"

#export DEBUG_LINK=1
#export OPTFLAGS=-O0
#export DBGFLAGS=-g3 -ggdb3

case "$1" in
  "-clean")
    make clean
    make -C vendor/nanopb/generator/proto clean
    make -C firmware/protob clean
    make -C firmware clean
    make -C emulator clean
    make -C emulator/pizero clean
    exit
    ;;
  "-pizero")
    export PATH=/opt/poky/3.4.1/sysroots/x86_64-pokysdk-linux/usr/bin:/opt/poky/3.4.1/sysroots/x86_64-pokysdk-linux/usr/bin/arm-poky-linux-gnueabi:$PATH
    export PKG_CONFIG_SYSROOT_DIR=/opt/poky/3.4.1/sysroots/arm1176jzfshf-vfp-poky-linux-gnueabi
    export PKG_CONFIG_PATH=/opt/poky/3.4.1/sysroots/arm1176jzfshf-vfp-poky-linux-gnueabi/usr/lib/pkgconfig
    export CC=arm-poky-linux-gnueabi-gcc
    export CPUFLAGS="-march=armv6 -mfpu=vfp -mfloat-abi=hard -mtune=arm1176jzf-s -mfpu=vfp --sysroot=/opt/poky/3.4.1/sysroots/arm1176jzfshf-vfp-poky-linux-gnueabi"
    export ARCH_BITS=32
    ;;
  "-pi4")
    export PATH=/opt/poky/3.4.1/sysroots/x86_64-pokysdk-linux/usr/bin:/opt/poky/3.4.1/sysroots/x86_64-pokysdk-linux/usr/bin/aarch64-poky-linux:$PATH
    export PKG_CONFIG_SYSROOT_DIR=/opt/poky/3.4.1/sysroots/cortexa53-poky-linux
    export PKG_CONFIG_PATH=/opt/poky/3.4.1/sysroots/cortexa53-poky-linux/usr/lib/pkgconfig
    export CC=aarch64-poky-linux-gcc
    export CPUFLAGS="-mcpu=cortex-a53 -march=armv8-a+crc --sysroot=/opt/poky/3.4.1/sysroots/cortexa53-poky-linux"
    export ARCH_BITS=64
    ;;
  *)
    ;;
esac

make vendor
make -C emulator/pizero
make -C emulator
make -C vendor/nanopb/generator/proto
make -C firmware/protob
make
make -C firmware trezor.elf
