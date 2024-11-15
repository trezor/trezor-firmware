INCLUDE "./embed/sys/linker/stm32f4/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = FIRMWARE_P1_START, LENGTH = FIRMWARE_P1_MAXSIZE
  FLASH2 (r)      : ORIGIN = FIRMWARE_P2_START, LENGTH = FIRMWARE_P2_MAXSIZE
  CCMRAM (wal)    : ORIGIN = MCU_CCMRAM + KERNEL_STACK_SIZE, LENGTH = MCU_CCMRAM_SIZE - KERNEL_CCMRAM_SIZE - KERNEL_FRAMEBUFFER_SIZE - KERNEL_STACK_SIZE
  SRAM   (wal)    : ORIGIN = MCU_SRAM + KERNEL_SRAM_SIZE, LENGTH = MCU_SRAM_SIZE - KERNEL_SRAM_SIZE
}

main_stack_base = ORIGIN(SRAM) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(SRAM);
_estack = main_stack_base;
_stack_size = SIZEOF(.stack);

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

_codelen = LENGTH(FLASH) - SIZEOF(.vendorheader) - SIZEOF(.header) + SIZEOF(.flash2);
_flash_start = ORIGIN(FLASH);
_flash_end = ORIGIN(FLASH) + LENGTH(FLASH);
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
  } >SRAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >SRAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >SRAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >SRAM

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(ORIGIN(SRAM) + LENGTH(SRAM)); /* this explicitly sets the end of the heap */
  } >SRAM

  .data_ccm : ALIGN(4) {
    *(.no_dma_buffers*);
    . = ALIGN(4);
  } >CCMRAM


  /DISCARD/ : {
    *(.ARM.exidx*);
  }

}
