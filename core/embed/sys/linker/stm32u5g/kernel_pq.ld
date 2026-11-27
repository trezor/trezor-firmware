ENTRY(reset_handler)

/* Merkle-tree layout: the manifest region and the secmon prefix precede the
   kernel code, so it links at its real run address. */
FW_MANIFEST_REGION = 0x400;

MEMORY {
  FLASH  (rx)    : ORIGIN = FIRMWARE_START, LENGTH = FIRMWARE_MAXSIZE
  MAIN_RAM (rw)  : ORIGIN = MAIN_RAM_START, LENGTH = MAIN_RAM_SIZE
  BOOT_ARGS (rw) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  FB1_RAM (rw)   : ORIGIN = FB1_RAM_START, LENGTH = FB1_RAM_SIZE
  FB2_RAM (rw)   : ORIGIN = FB2_RAM_START, LENGTH = FB2_RAM_SIZE
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

/* Kernel code only -- the secmon prefix is a separate module. */
_codelen = _kernel_flash_end - _kernel_flash_start;

SECTIONS {
  /* Manifest region placeholder; the firmware image emits the manifest. */
  .manifest : ALIGN(CODE_ALIGNMENT) {
    _manifest_start = .;
    . = _manifest_start + FW_MANIFEST_REGION;
  } >FLASH AT>FLASH

  /* Secmon module prefix (separate module, not in this module's hash). */
  .secmon : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.secmon));
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    _kernel_flash_start = .;
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . += 12K; /* Overflow causes UsageFault */
  } >MAIN_RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >MAIN_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.bss*);
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

  .buf (NOLOAD): ALIGN(4) {
    *(.no_dma_buffers*);
    . = ALIGN(4);
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
