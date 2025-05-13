ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = SECMON_START, LENGTH = SECMON_MAXSIZE
  MAIN_RAM (wal) : ORIGIN = SECMON_RAM_START, LENGTH = SECMON_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  FB1_RAM (wal) : ORIGIN = FB1_RAM_START, LENGTH = FB1_RAM_SIZE
  FB2_RAM (wal) : ORIGIN = FB2_RAM_START, LENGTH = FB2_RAM_SIZE
}

_sgstubs_section_start = ADDR(.gnu.sgstubs);
_sgstubs_section_end = ADDR(.gnu.sgstubs) + SIZEOF(.gnu.sgstubs);

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

_codelen = SIZEOF(.vendorheader) + SIZEOF(.header) + SIZEOF(.gnu.sgstubs) +
           SIZEOF(.flash) + SIZEOF(.data) + SIZEOF(.confidential);

_flash_start = ORIGIN(FLASH);
_flash_end = ORIGIN(FLASH) + LENGTH(FLASH);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH

  .header : ALIGN(4) {
    . = 1K;
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
  } >FLASH

  .gnu.sgstubs : ALIGN (32) {
    . = ALIGN(32);
    KEEP(*(.gnu.sgstubs*));
    . = ALIGN(32);
  } >FLASH

  .flash : {
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(512);
  } >FLASH

  .stack : ALIGN(8) {
    . = 12K; /* Overflow causes UsageFault */
  } >MAIN_RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >MAIN_RAM AT>FLASH

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(4);
  } >MAIN_RAM AT>FLASH

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >MAIN_RAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >MAIN_RAM

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

  /DISCARD/ : {
    *(.ARM.exidx*);
  }
}
