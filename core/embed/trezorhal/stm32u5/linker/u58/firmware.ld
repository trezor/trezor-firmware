INCLUDE "./embed/trezorhal/stm32u5/linker/u58/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = FIRMWARE_START, LENGTH = FIRMWARE_IMAGE_MAXSIZE
  SRAM1  (wal) : ORIGIN = MCU_SRAM1, LENGTH =  MCU_SRAM1_SIZE - BOOTARGS_SIZE
  BOOT_ARGS  (wal) : ORIGIN = MCU_SRAM2 - BOOTARGS_SIZE, LENGTH =  BOOTARGS_SIZE
  SRAM2  (wal) : ORIGIN = MCU_SRAM2, LENGTH =  MCU_SRAM2_SIZE
  SRAM3  (wal) : ORIGIN = MCU_SRAM3, LENGTH =  MCU_SRAM3_SIZE
  SRAM5  (wal) : ORIGIN = MCU_SRAM5, LENGTH = MCU_SRAM5_SIZE  /* SRAM5 is not available */
  SRAM6  (wal) : ORIGIN = MCU_SRAM6, LENGTH = MCU_SRAM6_SIZE  /* SRAM6 is not available */
  SRAM4  (wal) : ORIGIN = MCU_SRAM4, LENGTH = MCU_SRAM4_SIZE
}

main_stack_base = ORIGIN(SRAM2) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(SRAM2);
_estack = main_stack_base;

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

/* used by the startup/jump code to wipe memory */
_handoff_clear_ram_0_start = ORIGIN(SRAM1);
_handoff_clear_ram_0_end = ORIGIN(BOOT_ARGS);
_handoff_clear_ram_1_start = ORIGIN(BOOT_ARGS) + LENGTH(BOOT_ARGS);
_handoff_clear_ram_1_end = ORIGIN(SRAM6)+ LENGTH(SRAM6);
_handoff_clear_ram_2_start = ORIGIN(SRAM4);
_handoff_clear_ram_2_end = ORIGIN(SRAM4) + LENGTH(SRAM4);

/* used by the shutdown code to wipe memory */
_shutdown_clear_ram_0_start = ORIGIN(SRAM1);
_shutdown_clear_ram_0_end = ORIGIN(SRAM6)+ LENGTH(SRAM6);
_shutdown_clear_ram_1_start = ORIGIN(SRAM4);
_shutdown_clear_ram_1_end = ORIGIN(SRAM4) + LENGTH(SRAM4);
_shutdown_clear_ram_2_start = 0;
_shutdown_clear_ram_2_end = 0;
_shutdown_clear_ram_3_start = 0;
_shutdown_clear_ram_3_end = 0;


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

  .flash : ALIGN(CODE_ALIGNMENT) {
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

  .fb : ALIGN(4) {
   __fb_start = .;
    *(.fb1*);
    *(.fb2*);
   __fb_end = .;
    . = ALIGN(4);
  } >SRAM3

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
