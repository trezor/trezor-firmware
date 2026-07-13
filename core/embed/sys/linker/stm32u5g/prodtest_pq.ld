ENTRY(reset_handler)

/* Merkle-tree layout (pq_secure_boot feature): prodtest is a single secure module
   (its own variant). The firmware manifest ("firmware directory") occupies
   FW_MANIFEST_REGION at the image start, before the module header + code. This is
   prodtest.ld with ONLY the FLASH header layout swapped to the tree format
   (manifest + TRZM module header, replacing the legacy vendor/image/secmon
   headers); the RAM layout, stack and prodtest-specific sections are unchanged. */
FW_MANIFEST_REGION = 0x400;

MEMORY {
  FLASH  (rx)    : ORIGIN = FIRMWARE_START, LENGTH = FIRMWARE_MAXSIZE
  MAIN_RAM (rw)  : ORIGIN = MAIN_RAM_START, LENGTH = MAIN_RAM_SIZE
  AUX1_RAM (rw)  : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
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

/* Tree module code size -- what the TRZM header's code_size / code_hash cover:
   everything after the 1K module header region. Mirrors firmware_pq.ld. */
_codelen = SIZEOF(.padding) + SIZEOF(.flash) + SIZEOF(.data);

SECTIONS {
  /* Firmware manifest ("firmware directory") at the image start -- prodtest's
     single-module variant leaf (see manifest_header.S). Padded to
     FW_MANIFEST_REGION there; the post-build step fills the entry
     addr/size/header_hash. */
  .manifest : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.manifest));
  } >FLASH AT>FLASH

  /* The prodtest module header (TRZM, see module_header.S), replacing the legacy
     vendor + image + secmon headers. */
  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH AT>FLASH

  .padding : ALIGN(4) {
    . = ALIGN(4);
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(4);

    _prodtest_cli_cmd_section_start = .;
    KEEP(*(.prodtest_cli_cmd))
    _prodtest_cli_cmd_section_end = .;
    . = ALIGN(4);

    _unit_test_section_start = .;
    KEEP(*(.unit_test))
    _unit_test_section_end = .;

    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . += 128K; /* Overflow causes UsageFault */
  } >AUX1_RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >AUX1_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  /* End of code/data in FLASH */
  _image_flash_end = LOADADDR(.data) + SIZEOF(.data);

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >AUX1_RAM

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
