INCLUDE "./embed/sys/linker/stm32f4/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = KERNEL_START, LENGTH = KERNEL_MAXSIZE
  STACK (wal)     : ORIGIN = KERNEL_STACK_START, LENGTH = KERNEL_STACK_SIZE
  FB1 (wal)       : ORIGIN = KERNEL_FB1_START, LENGTH = KERNEL_FB1_SIZE
  MAIN_RAM (wal)  : ORIGIN = KERNEL_RAM_START, LENGTH = KERNEL_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  SRAM   (wal)    : ORIGIN = KERNEL_SRAM_START, LENGTH = KERNEL_SRAM_SIZE
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

_codelen = SIZEOF(.vendorheader) + SIZEOF(.header) + SIZEOF(.flash) + SIZEOF(.data) ;

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
  } >STACK

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >MAIN_RAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >MAIN_RAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >SRAM

  .fb : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >FB1

  .boot_args : ALIGN(8) {
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

}
