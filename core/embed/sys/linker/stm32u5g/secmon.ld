ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = FIRMWARE_START_S, LENGTH = FIRMWARE_MAXSIZE
  RAM (wal) : ORIGIN = SECMON_RAM_START, LENGTH = SECMON_RAM_SIZE
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

_bootargs_ram_start = BOOTARGS_START;
_bootargs_ram_end = BOOTARGS_START + BOOTARGS_SIZE;

_codelen = _secmon_flash_end - _secmon_code_start;
_secmon_size = _secmon_flash_end - ORIGIN(FLASH);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH

  .header : ALIGN(4) {
    . = 1K;
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH

  .secmon_header : ALIGN(4) {
    KEEP(*(.secmon_header));
  } >FLASH

  .padding : ALIGN(4) {
    _secmon_code_start = .;
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH AT>FLASH

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
  } >RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >RAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >RAM

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

  .flash : {
    . = ALIGN(8K) - 1;
    BYTE(0x00)
    _secmon_flash_end = .;
  } >FLASH
}
