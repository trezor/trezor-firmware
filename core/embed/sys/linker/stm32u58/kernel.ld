INCLUDE "./embed/sys/linker/stm32u58/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = KERNEL_START, LENGTH = KERNEL_MAXSIZE

  MAIN_RAM (wal) : ORIGIN = MAIN_RAM_START, LENGTH = MAIN_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  SAES_RAM (wal) : ORIGIN = SAES_RAM_START, LENGTH = SAES_RAM_SIZE
  FB1_RAM (wal) : ORIGIN = FB1_RAM_START, LENGTH = FB1_RAM_SIZE
  FB2_RAM (wal) : ORIGIN = FB2_RAM_START, LENGTH = FB2_RAM_SIZE
}

_stack_section_start = ADDR(.stack);
_stack_section_end = ADDR(.stack) + SIZEOF(.stack);

ustack_base = ADDR(.udata) + 512;
_sustack = ADDR(.udata) + 256;
_eustack = ustack_base;

_data_section_loadaddr = LOADADDR(.data);
_data_section_start = ADDR(.data);
_data_section_end = ADDR(.data) + SIZEOF(.data);

_bss_section_start = ADDR(.bss);
_bss_section_end = ADDR(.bss) + SIZEOF(.bss);

_confidential_section_loadaddr = LOADADDR(.confidential);
_confidential_section_start = ADDR(.confidential);
_confidential_section_end = ADDR(.confidential) + SIZEOF(.confidential);

_accessible_ram_0_start = MCU_SRAM1;
_accessible_ram_0_end = MCU_SRAM3 + MCU_SRAM3_SIZE;
_accessible_ram_1_start = MCU_SRAM4;
_accessible_ram_1_end =  MCU_SRAM4 + MCU_SRAM4_SIZE;

_bootargs_ram_start = BOOTARGS_START;
_bootargs_ram_end = BOOTARGS_START + BOOTARGS_SIZE;

_codelen = SIZEOF(.vendorheader) + SIZEOF(.header) + SIZEOF(.flash)  + SIZEOF(.uflash) + SIZEOF(.data) + SIZEOF(.confidential);
_flash_start = ORIGIN(FLASH);
_flash_end = ORIGIN(FLASH) + LENGTH(FLASH);

_uflash_start = ADDR(.uflash);
_uflash_end = ADDR(.uflash) + SIZEOF(.uflash);

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
    . = 6K; /* Overflow causes UsageFault */
  } >MAIN_RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >MAIN_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.buf*);
    *(.bss*);
    . = ALIGN(4);
  } >MAIN_RAM

  /* unprivileged data and stack for SAES */
  .udata : ALIGN(512) {
    *(.udata*);
    . = ALIGN(256);
    . = 256; /* Overflow causes UsageFault */
  } >SAES_RAM

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(CODE_ALIGNMENT);
  } >MAIN_RAM AT>FLASH

  .uflash : ALIGN(512) {
    *(.uflash*);
    . = ALIGN(COREAPP_ALIGNMENT);
  } >FLASH AT>FLASH

  .fb1 : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >FB1_RAM

  .fb2 : ALIGN(4) {
    *(.fb2*);
    . = ALIGN(4);
  } >FB2_RAM

  .boot_args : ALIGN(8) {
    *(.boot_command*);
    . = ALIGN(8);
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS
}
