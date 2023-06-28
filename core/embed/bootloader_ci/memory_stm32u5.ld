/* Trezor v2 bootloader linker script */

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = 0x08010000, LENGTH = 128K
  SRAM1  (wal) : ORIGIN = 0x20000000, LENGTH =  768K
  SRAM2  (wal) : ORIGIN = 0x200C0000, LENGTH =  64K
  SRAM3  (wal) : ORIGIN = 0x200D0000, LENGTH =  832K
  SRAM5  (wal) : ORIGIN = 0x201A0000, LENGTH =  832K
  SRAM6  (wal) : ORIGIN = 0x20270000, LENGTH =  512K
  SRAM4  (wal) : ORIGIN = 0x28000000, LENGTH =  16K
}

main_stack_base = ORIGIN(SRAM1) + SIZEOF(.stack) ; /* 8-byte aligned full descending stack */

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

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

  .stack : ALIGN(8) {
    . = 16K; /* Exactly 16K allocated for stack. Overflow causes MemManage fault (when using MPU). */
  } >SRAM1

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

  .fb1 : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >SRAM3

  .fb2 : ALIGN(4) {
    *(.fb2*);
    . = ALIGN(4);
  } >SRAM5

}
