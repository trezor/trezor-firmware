ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = FIRMWARE_START, LENGTH = FIRMWARE_MAXSIZE

  MAIN_RAM (wal) : ORIGIN = MAIN_RAM_START, LENGTH = MAIN_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  FB1_RAM (wal) : ORIGIN = FB1_RAM_START, LENGTH = FB1_RAM_SIZE
  FB2_RAM (wal) : ORIGIN = FB2_RAM_START, LENGTH = FB2_RAM_SIZE
}

_stack_section_start = ADDR(.stack);
_stack_section_end = ADDR(.stack) + SIZEOF(.stack);

_data_section_loadaddr = LOADADDR(.data);
_data_section_start = ADDR(.data);
_data_section_end = ADDR(.data) + SIZEOF(.data);

_bss_section_start = ADDR(.bss);
_bss_section_end = ADDR(.bss) + SIZEOF(.bss);

_confidential_section_loadaddr = LOADADDR(.confidential);
_confidential_section_start = ADDR(.confidential);
_confidential_section_end = ADDR(.confidential) + SIZEOF(.confidential);

_bootargs_ram_start = BOOTARGS_START;
_bootargs_ram_end = BOOTARGS_START + BOOTARGS_SIZE;

_codelen = _kernel_flash_end - ORIGIN(FLASH);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    . = 1K;
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    _kernel_flash_start = .;
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
    *(.bss*);
    . = ALIGN(4);
  } >MAIN_RAM

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
  } >MAIN_RAM

  .boot_args : ALIGN(8) {
    *(.boot_command*);
    . = ALIGN(8);
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS

  .flash : ALIGN(4) {
    _kernel_flash_end = .;
  } >FLASH
}
