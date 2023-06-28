/* Trezor v2 bootloader linker script */

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = 0x0C010000, LENGTH = 128K
  SRAM1  (wal) : ORIGIN = 0x30000000, LENGTH =  768K
  SRAM2  (wal) : ORIGIN = 0x300C0000, LENGTH =  64K
  SRAM3  (wal) : ORIGIN = 0x300D0000, LENGTH =  832K
  SRAM5  (wal) : ORIGIN = 0x301A0000, LENGTH =  832K
  SRAM6  (wal) : ORIGIN = 0x30270000, LENGTH =  512K
  SRAM4  (wal) : ORIGIN = 0x38000000, LENGTH =  16K
}

main_stack_base = ORIGIN(SRAM2) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(SRAM2) + 0x100;
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

/* used by the startup code to populate variables used by the C code */
sensitive_lma = LOADADDR(.sensitive);
sensitive_vma = ADDR(.sensitive);
sensitive_size = SIZEOF(.sensitive);

/* used by the startup code to wipe memory */
sram1_start = ORIGIN(SRAM1);
sram1_end = ORIGIN(SRAM1) + LENGTH(SRAM1);
sram2_start = ORIGIN(SRAM2);
sram2_end = ORIGIN(SRAM2) + LENGTH(SRAM2);
sram3_start = ORIGIN(SRAM3);
sram3_end = ORIGIN(SRAM3) + LENGTH(SRAM3);
sram4_start = ORIGIN(SRAM4);
sram4_end = ORIGIN(SRAM4) + LENGTH(SRAM4);
sram5_start = ORIGIN(SRAM5);
sram5_end = ORIGIN(SRAM5) + LENGTH(SRAM5);
sram6_start = ORIGIN(SRAM6);
sram6_end = ORIGIN(SRAM6) + LENGTH(SRAM6);

/* IMAGE_HEADER_SIZE is 0x400, this is for interaction-less firmware update start */
firmware_header_start = sram1_end - 0x400;
_stay_in_bootloader_flag_addr = ABSOLUTE(sram1_end - 0x400 - 4);

_codelen = SIZEOF(.flash) + SIZEOF(.data) + SIZEOF(.sensitive);

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
  } >SRAM1 AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >SRAM1

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >SRAM1

  .stack : ALIGN(8) {
    . = 16K + 0x100; /* Exactly 16K allocated for stack. Overflow causes MemManage fault (when using MPU). */
  } >SRAM2

  .sensitive : ALIGN(512) {
    *(.sensitive*);
    . = ALIGN(512);
  } >SRAM2 AT>FLASH

  .fb1 : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >SRAM3

  .fb2 : ALIGN(4) {
    *(.fb2*);
    . = ALIGN(4);
  } >SRAM5
}
