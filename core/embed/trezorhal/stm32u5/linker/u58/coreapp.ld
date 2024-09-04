INCLUDE "./embed/trezorhal/stm32u5/linker/u58/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = KERNEL_START, LENGTH = FIRMWARE_IMAGE_MAXSIZE
  SRAM1  (wal) : ORIGIN = MCU_SRAM1, LENGTH =  MCU_SRAM1_SIZE - KERNEL_SRAM1_SIZE
  BOOT_ARGS  (wal) : ORIGIN = MCU_SRAM2 - BOOTARGS_SIZE, LENGTH =  BOOTARGS_SIZE
  SRAM2  (wal) : ORIGIN = MCU_SRAM2 + KERNEL_SRAM2_SIZE, LENGTH =  MCU_SRAM2_SIZE - KERNEL_SRAM2_SIZE
  SRAM3  (wal) : ORIGIN = MCU_SRAM3 + KERNEL_SRAM3_SIZE, LENGTH =  MCU_SRAM3_SIZE - KERNEL_SRAM3_SIZE
  SRAM5  (wal) : ORIGIN = MCU_SRAM5, LENGTH =  0K  /* SRAM5 is not available */
  SRAM6  (wal) : ORIGIN = MCU_SRAM6, LENGTH =  0K  /* SRAM6 is not available */
  SRAM4  (wal) : ORIGIN = MCU_SRAM4, LENGTH =  0K  /* not allocated to coreapp */
}

main_stack_base = ORIGIN(SRAM2) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(SRAM2);
_estack = main_stack_base;
_stack_size = SIZEOF(.stack);

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);
bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

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
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.kernel));
    . = ALIGN(512);
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
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >SRAM1

  .stack : ALIGN(8) {
    . = 32K; /* Overflow causes UsageFault */
  } >SRAM2

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(512);
  } >SRAM2 AT>FLASH

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >SRAM3

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(sram3_end); /* this explicitly sets the end of the heap */
  } >SRAM3

  .boot_args : ALIGN(8) {
    *(.boot_command*);
    . = ALIGN(8);
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS
}
