INCLUDE "./embed/sys/linker/stm32f4/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = FIRMWARE_P1_START, LENGTH = FIRMWARE_P1_MAXSIZE
  FLASH2 (r)      : ORIGIN = FIRMWARE_P2_START, LENGTH = FIRMWARE_P2_MAXSIZE
  COREAPP_RAM1 (wal) : ORIGIN = AUX_RAM_START, LENGTH = AUX_RAM_SIZE
  COREAPP_RAM2 (wal) : ORIGIN = COREAPP_RAM2_START, LENGTH = COREAPP_RAM2_SIZE
}

main_stack_base = ADDR(.stack) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ADDR(.stack);
_estack = main_stack_base;
_stack_size = SIZEOF(.stack);

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

_codelen = LENGTH(FLASH) - SIZEOF(.vendorheader) - SIZEOF(.header) + SIZEOF(.flash2);
_heap_start = ADDR(.heap);
_heap_end = ADDR(.heap) + SIZEOF(.heap);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH AT>FLASH

  .flash2 : ALIGN(CODE_ALIGNMENT) {
    build/firmware/frozen_mpy.o(.rodata*);
    build/firmware/vendor/secp256k1-zkp/src/secp256k1.o(.rodata*);
    build/firmware/vendor/secp256k1-zkp/src/precomputed_ecmult.o(.rodata*);
    build/firmware/vendor/secp256k1-zkp/src/precomputed_ecmult_gen.o(.rodata*);
    build/firmware/vendor/trezor-crypto/aes/aestab.o(.rodata*);
    . = ALIGN(4);
    */libtrezor_lib.a:(.text*);
    . = ALIGN(4);
    */libtrezor_lib.a:(.rodata*);
    . = ALIGN(512);
  } >FLASH2 AT>FLASH2

  .flash : ALIGN(512) {
    KEEP(*(.kernel));
    . = ALIGN(COREAPP_ALIGNMENT);
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(4);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . = 16K; /* Exactly 16K allocated for stack. Overflow causes MemManage fault (when using MPU). */
  } >COREAPP_RAM1

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >COREAPP_RAM1 AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >COREAPP_RAM1

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >COREAPP_RAM1

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(ORIGIN(COREAPP_RAM1) + LENGTH(COREAPP_RAM1)); /* this explicitly sets the end of the heap */
  } >COREAPP_RAM1

  .data_ccm : ALIGN(4) {
    *(.no_dma_buffers*);
    . = ALIGN(4);
  } >COREAPP_RAM2


  /DISCARD/ : {
    *(.ARM.exidx*);
  }

}
