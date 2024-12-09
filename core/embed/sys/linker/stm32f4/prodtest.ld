INCLUDE "./embed/sys/linker/stm32f4/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = FIRMWARE_P1_START, LENGTH = FIRMWARE_P1_MAXSIZE
  MAIN_STACK (wal)  : ORIGIN = S_MAIN_STACK_START, LENGTH = S_MAIN_STACK_SIZE
  MAIN_RAM (wal)  : ORIGIN = S_MAIN_RAM_START, LENGTH = S_MAIN_RAM_SIZE
  FB1 (wal)       : ORIGIN = S_FB1_RAM_START, LENGTH = S_FB1_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  AUX1_RAM   (wal) : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
}

main_stack_base = ADDR(.stack) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ADDR(.stack);
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);
bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

/* used by the startup code to wipe memory */
_startup_clear_ram_0_start = MCU_CCMRAM;
_startup_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_startup_clear_ram_1_start = MCU_SRAM;
_startup_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* used by the startup/jump code to wipe memory */
_handoff_clear_ram_0_start = MCU_CCMRAM;
_handoff_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE - BOOTARGS_SIZE;
_handoff_clear_ram_1_start = MCU_SRAM;
_handoff_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* used by the shutdown code to wipe memory */
_shutdown_clear_ram_0_start = MCU_CCMRAM;
_shutdown_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_shutdown_clear_ram_1_start = MCU_SRAM;
_shutdown_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* reserve 256 bytes for bootloader arguments */
boot_args_start = ORIGIN(BOOT_ARGS);
boot_args_end = ORIGIN(BOOT_ARGS) + LENGTH(BOOT_ARGS);

_codelen = SIZEOF(.flash) + SIZEOF(.data);
_flash_start = ORIGIN(FLASH);
_flash_end = ORIGIN(FLASH) + LENGTH(FLASH);

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
    . = ALIGN(128K);
  } >FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .stack : ALIGN(8) {
    . = 16K; /* this acts as a build time assertion that at least this much memory is available for stack use */
  } >MAIN_STACK

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >AUX1_RAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >AUX1_RAM

  .fb : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >FB1

  .boot_args : ALIGN(8) {
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS
}
