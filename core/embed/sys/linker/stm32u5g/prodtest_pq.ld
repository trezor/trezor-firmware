ENTRY(reset_handler)

/* Merkle-tree layout: prodtest is a single module, preceded by the manifest
   region. Same as prodtest.ld apart from the FLASH header layout. */
FW_MANIFEST_REGION = 0x400;
/* Smart-hashing chunk size stamped into the manifest entry; not a padding
   constant. Must match FW_CHUNK_SIZE in sec/boot_header.h. */
FW_CHUNK_SIZE = 0x2000;

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

/* Module code size covered by the manifest entry; mirrors firmware_pq.ld. */
_codelen = SIZEOF(.padding) + SIZEOF(.flash) + SIZEOF(.data);

/* The single module's code region, for the manifest_header.S entry. */
_manifest_module_addr = ADDR(.padding) - FIRMWARE_START;
_manifest_module_size = _codelen;

SECTIONS {
  /* Manifest, padded to FW_MANIFEST_REGION by manifest_header.S. */
  .manifest : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.manifest));
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

  .buf (NOLOAD) : ALIGN(4) {
    *(.no_dma_buffers*);
    . = ALIGN(4);
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
