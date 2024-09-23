INCLUDE "./embed/trezorhal/stm32u5/linker/u5a/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = KERNEL_START, LENGTH = KERNEL_MAXSIZE
  SRAM1  (wal) : ORIGIN = MCU_SRAM1, LENGTH = MCU_SRAM1_SIZE - BOOTARGS_SIZE
  BOOT_ARGS  (wal) : ORIGIN = MCU_SRAM2 - BOOTARGS_SIZE, LENGTH = BOOTARGS_SIZE
  SRAM2  (wal) : ORIGIN = MCU_SRAM2, LENGTH =  MCU_SRAM2_SIZE
  SRAM3  (wal) : ORIGIN = MCU_SRAM3, LENGTH =  MCU_SRAM3_SIZE
  SRAM5  (wal) : ORIGIN = MCU_SRAM5, LENGTH =  MCU_SRAM5_SIZE
  SRAM6  (wal) : ORIGIN = MCU_SRAM6, LENGTH =  MCU_SRAM6_SIZE
  SRAM4  (wal) : ORIGIN = MCU_SRAM4, LENGTH =  MCU_SRAM4_SIZE
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
_shutdown_clear_ram_0_start = ORIGIN(SRAM1);
_shutdown_clear_ram_0_end = ADDR(.fb1);
_shutdown_clear_ram_1_start = ADDR(.fb1) + SIZEOF(.fb1);
_shutdown_clear_ram_1_end = ADDR(.fb2);
_shutdown_clear_ram_2_start = ADDR(.fb2) + SIZEOF(.fb2);
_shutdown_clear_ram_2_end = ORIGIN(SRAM6)+ LENGTH(SRAM6);
_shutdown_clear_ram_3_start = ORIGIN(SRAM4);
_shutdown_clear_ram_3_end = ORIGIN(SRAM4) + LENGTH(SRAM4);


/* reserve 256 bytes for bootloader arguments */
boot_args_start = ORIGIN(BOOT_ARGS);
boot_args_end = ORIGIN(BOOT_ARGS) + LENGTH(BOOT_ARGS);
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
    . = ALIGN(4);
    KEEP(*(.bootloader));
    *(.bootloader*);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . = 12K; /* Overflow causes UsageFault */
  } >SRAM2

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >SRAM2 AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >SRAM2

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(512);
  } >SRAM2 AT>FLASH

  .fb1 : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >SRAM1

  .fb2 : ALIGN(4) {
    *(.fb2*);
    *(.gfxmmu_table*);
    *(.framebuffer_select*);
    . = ALIGN(4);
  } >SRAM3

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >SRAM2


  .boot_args : ALIGN(8) {
    *(.boot_command*);
    . = ALIGN(8);
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS
}
