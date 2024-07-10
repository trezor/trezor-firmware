/* TREZORv2 firmware linker script */

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = 0x0C050000, LENGTH = 3648K
  SRAM1  (wal) : ORIGIN = 0x30000000, LENGTH =  768K - 0x100
  BOOT_ARGS  (wal) : ORIGIN = 0x300BFF00, LENGTH =  0x100
  SRAM2  (wal) : ORIGIN = 0x300C0000, LENGTH =  64K
  SRAM3  (wal) : ORIGIN = 0x300D0000, LENGTH =  832K
  SRAM5  (wal) : ORIGIN = 0x301A0000, LENGTH =  832K
  SRAM6  (wal) : ORIGIN = 0x30270000, LENGTH =  0
  SRAM4  (wal) : ORIGIN = 0x38000000, LENGTH =  16K
}

main_stack_base = ORIGIN(SRAM2) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(SRAM2);
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

/* used by the startup code to populate variables used by the C code */
confidential_lma = LOADADDR(.confidential);
confidential_vma = ADDR(.confidential);
confidential_size = SIZEOF(.confidential);

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

/* reserve 256 bytes for bootloader arguments */
boot_args_start = ORIGIN(BOOT_ARGS);
boot_args_end = ORIGIN(BOOT_ARGS) + LENGTH(BOOT_ARGS);
_codelen = SIZEOF(.flash) + SIZEOF(.data) + SIZEOF(.confidential);
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

  .flash : ALIGN(1024) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(4);
    KEEP(*(.bootloader));
    *(.bootloader*);
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

  .data_ccm : ALIGN(4) {
    *(.no_dma_buffers*);
    . = ALIGN(4);
  } >SRAM1

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(sram1_end); /* this explicitly sets the end of the heap */
  } >SRAM1

  .stack : ALIGN(8) {
    . = 16K; /* Overflow causes UsageFault */
  } >SRAM2

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(512);
  } >SRAM2 AT>FLASH

  .fb1 : ALIGN(4) {
   __fb_start = .;
    *(.fb1*);
    *(.gfxmmu_table*);
    *(.framebuffer_select*);
    . = ALIGN(4);
  } >SRAM3

  .fb2 : ALIGN(4) {
    *(.fb2*);
   __fb_end = .;
    . = ALIGN(4);
  } >SRAM5

  .boot_args : ALIGN(8) {
    *(.boot_command*);
    . = ALIGN(8);
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS
}
