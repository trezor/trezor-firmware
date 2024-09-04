INCLUDE "./embed/trezorhal/stm32f4/linker/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = BOOTLOADER_START, LENGTH = BOOTLOADER_IMAGE_MAXSIZE
  CCMRAM (wal)    : ORIGIN = MCU_CCMRAM, LENGTH = MCU_CCMRAM_SIZE - BOOTARGS_SIZE
  BOOT_ARGS (wal) : ORIGIN = MCU_CCMRAM + MCU_CCMRAM_SIZE - BOOTARGS_SIZE, LENGTH = BOOTARGS_SIZE
  SRAM   (wal)    : ORIGIN = MCU_SRAM, LENGTH = MCU_SRAM_SIZE
}

main_stack_base = ORIGIN(CCMRAM) + SIZEOF(.stack) ; /* 8-byte aligned full descending stack */
_sstack = ORIGIN(CCMRAM);
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);
bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

/* used by the startup code to wipe memory */
ccmram_start = ORIGIN(CCMRAM);
ccmram_end = ORIGIN(CCMRAM) + LENGTH(CCMRAM);

/* used by the startup code to wipe memory */
sram_start = ORIGIN(SRAM);
sram_end = ORIGIN(SRAM) + LENGTH(SRAM);

/* reserve 256 bytes for bootloader arguments */
boot_args_start = ORIGIN(BOOT_ARGS);
boot_args_end = ORIGIN(BOOT_ARGS) + LENGTH(BOOT_ARGS);

_codelen = SIZEOF(.flash) + SIZEOF(.data);

SECTIONS {
  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . = 16K; /* Exactly 16K allocated for stack. Overflow causes MemManage fault (when using MPU). */
  } >CCMRAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >CCMRAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >CCMRAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
    *(.no_dma_buffers*);
    . = ALIGN(4);
  } >SRAM

  .boot_args : ALIGN(8) {
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS

}
