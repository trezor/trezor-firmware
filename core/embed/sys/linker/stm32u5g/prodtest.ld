INCLUDE "./embed/sys/linker/stm32u5g/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = KERNEL_START, LENGTH = KERNEL_MAXSIZE

  MAIN_RAM (wal) : ORIGIN = MAIN_RAM_START, LENGTH = MAIN_RAM_SIZE
  AUX1_RAM (wal) : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  SAES_RAM (wal) : ORIGIN = SAES_RAM_START, LENGTH = SAES_RAM_SIZE
  FB1_RAM (wal) : ORIGIN = FB1_RAM_START, LENGTH = FB1_RAM_SIZE
  FB2_RAM (wal) : ORIGIN = FB2_RAM_START, LENGTH = FB2_RAM_SIZE
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

/* used by the startup code to populate variables used by the C code */
confidential_lma = LOADADDR(.confidential);
confidential_vma = ADDR(.confidential);
confidential_size = SIZEOF(.confidential);

/* used by the startup code to wipe memory */
_startup_clear_ram_0_start = MCU_SRAM1;
_startup_clear_ram_0_end = MCU_SRAM1 + MCU_SRAM1_SIZE;
_startup_clear_ram_1_start = MCU_SRAM2;
_startup_clear_ram_1_end = MCU_SRAM6 + MCU_SRAM6_SIZE;
_startup_clear_ram_2_start = MCU_SRAM4;
_startup_clear_ram_2_end = MCU_SRAM4 + MCU_SRAM4_SIZE;

/* used by the jump code to wipe memory */
_handoff_clear_ram_0_start = MCU_SRAM1;
_handoff_clear_ram_0_end = MCU_SRAM1 + MCU_SRAM1_SIZE - BOOTARGS_SIZE;
_handoff_clear_ram_1_start = MCU_SRAM2;
_handoff_clear_ram_1_end = MCU_SRAM6 + MCU_SRAM6_SIZE;
_handoff_clear_ram_2_start = MCU_SRAM4;
_handoff_clear_ram_2_end = MCU_SRAM4 + MCU_SRAM4_SIZE;

/* used by the shutdown code to wipe memory */
_shutdown_clear_ram_0_start = MCU_SRAM1;
_shutdown_clear_ram_0_end = ADDR(.fb1);
_shutdown_clear_ram_1_start = ADDR(.fb1) + SIZEOF(.fb1);
_shutdown_clear_ram_1_end = ADDR(.fb2);
_shutdown_clear_ram_2_start = ADDR(.fb2) + SIZEOF(.fb2);
_shutdown_clear_ram_2_end = MCU_SRAM6 + MCU_SRAM6_SIZE;
_shutdown_clear_ram_3_start = MCU_SRAM4;
_shutdown_clear_ram_3_end = MCU_SRAM4 + MCU_SRAM4_SIZE;


_codelen = SIZEOF(.flash) + SIZEOF(.data) + SIZEOF(.confidential);
_flash_start = ORIGIN(FLASH);
_flash_end = ORIGIN(FLASH) + LENGTH(FLASH);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    KEEP(*(.header));
    . = ALIGN(CODE_ALIGNMENT);
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
    . = 12K; /* Overflow causes UsageFault */
  } >MAIN_RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >AUX1_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >AUX1_RAM

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(512);
  } >MAIN_RAM AT>FLASH

  .fb1 : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >FB1_RAM

  .fb2 : ALIGN(4) {
    *(.fb2*);
    . = ALIGN(4);
  } >FB2_RAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >AUX1_RAM


  .boot_args : ALIGN(8) {
    *(.boot_command*);
    . = ALIGN(8);
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS
}
