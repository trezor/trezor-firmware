/* TREZORv2 firmware linker script */

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = 0x08040000, LENGTH = 768K
  FLASH2 (r)   : ORIGIN = 0x08120000, LENGTH = 896K
  CCMRAM (wal) : ORIGIN = 0x10000000, LENGTH = 64K
  SRAM   (wal) : ORIGIN = 0x20000000, LENGTH = 192K
}

main_stack_base = ORIGIN(SRAM) + LENGTH(SRAM); /* 8-byte aligned full descending stack */
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

/* used by the startup code to wipe memory */
ccmram_start = ORIGIN(CCMRAM);
ccmram_end = ORIGIN(CCMRAM) + LENGTH(CCMRAM);

/* used by the startup code to wipe memory */
sram_start = ORIGIN(SRAM);
sram_end = ORIGIN(SRAM) + LENGTH(SRAM);
_ram_start = sram_start;
_ram_end = sram_end;

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

  .flash2 : ALIGN(512) {
    build/firmware/frozen_mpy.o(.rodata*);
    . = ALIGN(512);
  } >FLASH2 AT>FLASH2

  .flash : ALIGN(512) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >SRAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >SRAM

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(sram_end - 16K); /* this explicitly sets the end of the heap effectively giving the stack at most 16K */
  } >SRAM

  .stack : ALIGN(8) {
    . = 4K; /* this acts as a build time assertion that at least this much memory is available for stack use */
  } >SRAM
}
