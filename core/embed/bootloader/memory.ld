/* Trezor v2 bootloader linker script */

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = 0x08020000, LENGTH = 128K
  CCMRAM (wal) : ORIGIN = 0x10000000, LENGTH = 64K
  SRAM   (wal) : ORIGIN = 0x20000000, LENGTH = 192K
}

main_stack_base = ORIGIN(CCMRAM) + LENGTH(CCMRAM); /* 8-byte aligned full descending stack */

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

_codelen = SIZEOF(.flash) + SIZEOF(.data);

SECTIONS {
  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH AT>FLASH

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
  } >CCMRAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >CCMRAM

  .stack : ALIGN(8) {
    . = 4K; /* this acts as a build time assertion that at least this much memory is available for stack use */
  } >CCMRAM
}
