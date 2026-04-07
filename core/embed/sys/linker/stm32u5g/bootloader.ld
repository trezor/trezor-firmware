ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = BOOTLOADER_START, LENGTH = BOOTLOADER_MAXSIZE
  MAIN_RAM (wal) : ORIGIN = MAIN_RAM_START, LENGTH = MAIN_RAM_SIZE
  AUX1_RAM (wal) : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
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

_bootargs_ram_start = BOOTARGS_START;
_bootargs_ram_end = BOOTARGS_START + BOOTARGS_SIZE;

_bootloader_code_size = _bootloader_code_end - ADDR(.padding);

SECTIONS {
  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH

  .padding : ALIGN(4) {
    . = ALIGN(4);
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(4);
  } >FLASH

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(4);
  } >MAIN_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >MAIN_RAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
    *(.no_dma_buffers*);
    . = ALIGN(4);
  } >AUX1_RAM

  .stack : ALIGN(8) {
    . = 16K; /* Overflow causes UsageFault */
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

  .flash : {
    /* Pad the rest of bootloader area with zeros */
    BYTE(0x00)
    FILL(0x00)
    . = ADDR(.header) + BOOTLOADER_MAXSIZE;
    _bootloader_code_end = .;
  } >FLASH
}
