/* TREZORv2 firmware linker script */

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = 0x080D0000, LENGTH = 256K
  SRAM1  (wal) : ORIGIN = 0x20040000, LENGTH =  128K
  SRAM2  (wal) : ORIGIN = 0x200C8000, LENGTH =  16K
}

main_stack_base = ORIGIN(SRAM2) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(SRAM2);
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

/* used by the startup code to wipe memory */
sram1_start = ORIGIN(SRAM1);
sram1_end = ORIGIN(SRAM1) + LENGTH(SRAM1);
sram2_start = ORIGIN(SRAM2);
sram2_end = ORIGIN(SRAM2) + LENGTH(SRAM2);

_heap_start = ADDR(.heap);
_heap_end = ADDR(.heap) + SIZEOF(.heap);

SECTIONS {
  .flash : ALIGN(512) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(4);
    KEEP(*(.bootloader));
    *(.bootloader*);
    . = ALIGN(512);
  } >FLASH

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

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(sram1_end); /* this explicitly sets the end of the heap */
  } >SRAM1

  .stack : ALIGN(8) {
    . = 16K; /* Overflow causes UsageFault */
  } >SRAM2

}
