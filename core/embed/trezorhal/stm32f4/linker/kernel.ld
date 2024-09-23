INCLUDE "./embed/trezorhal/stm32f4/linker/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = KERNEL_START, LENGTH = KERNEL_MAXSIZE
  CCMRAM_STACK (wal) : ORIGIN = MCU_CCMRAM, LENGTH = KERNEL_STACK_SIZE
  CCMRAM_FB (wal) : ORIGIN = MCU_CCMRAM + MCU_CCMRAM_SIZE - KERNEL_CCMRAM_SIZE - KERNEL_FRAMEBUFFER_SIZE, LENGTH = KERNEL_FRAMEBUFFER_SIZE
  CCMRAM (wal)    : ORIGIN = MCU_CCMRAM + MCU_CCMRAM_SIZE - KERNEL_CCMRAM_SIZE, LENGTH = KERNEL_CCMRAM_SIZE - BOOTARGS_SIZE
  BOOT_ARGS (wal) : ORIGIN = MCU_CCMRAM + MCU_CCMRAM_SIZE - BOOTARGS_SIZE, LENGTH = BOOTARGS_SIZE
  SRAM   (wal)    : ORIGIN = MCU_SRAM + MCU_SRAM_SIZE - KERNEL_SRAM_SIZE, LENGTH = KERNEL_SRAM_SIZE
}

main_stack_base = ORIGIN(CCMRAM_STACK) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(CCMRAM_STACK);
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);
bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

/* reserve 256 bytes for bootloader arguments */
boot_args_start = ORIGIN(BOOT_ARGS);
boot_args_end = ORIGIN(BOOT_ARGS) + LENGTH(BOOT_ARGS);

/* used by the startup code to wipe memory */
_startup_clear_ram_0_start = MCU_CCMRAM;
_startup_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_startup_clear_ram_1_start = MCU_SRAM;
_startup_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* used by the jump code to wipe memory */
_handoff_clear_ram_0_start = MCU_CCMRAM;
_handoff_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE - BOOTARGS_SIZE;
_handoff_clear_ram_1_start = MCU_SRAM;
_handoff_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* used by the shutdown code to wipe memory */
_shutdown_clear_ram_0_start = MCU_CCMRAM;
_shutdown_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_shutdown_clear_ram_1_start = MCU_SRAM;
_shutdown_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* used by applet cleaning code */
_coreapp_clear_ram_0_start = MCU_CCMRAM + KERNEL_STACK_SIZE;
_coreapp_clear_ram_0_size = MCU_CCMRAM_SIZE - KERNEL_CCMRAM_SIZE - KERNEL_FRAMEBUFFER_SIZE - KERNEL_STACK_SIZE;
_coreapp_clear_ram_1_start = MCU_SRAM;
_coreapp_clear_ram_1_size = MCU_SRAM_SIZE - KERNEL_SRAM_SIZE;


_codelen = SIZEOF(.vendorheader) + SIZEOF(.header) + SIZEOF(.flash) + SIZEOF(.data) ;
_flash_start = ORIGIN(FLASH);
_flash_end = ORIGIN(FLASH) + LENGTH(FLASH);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    . = 1K;
    . = ALIGN(CODE_ALIGNMENT);
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

  .stack : ALIGN(8) {
    . = 8K; /* Exactly 6k allocated for stack. Overflow causes MemManage fault (when using MPU). */
  } >CCMRAM_STACK

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >CCMRAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >CCMRAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >SRAM

  .fb : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >CCMRAM_FB

  .boot_args : ALIGN(8) {
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

}
