ENTRY(reset_handler)

/* Merkle-tree layout: the firmware manifest occupies FW_MANIFEST_REGION at the
   firmware start (reserved in SECTIONS below, mirroring kernel_pq.ld), so the
   secmon (the first module) runs that many bytes later. _secmon_size spans from
   ORIGIN (the manifest region) through the secmon code, so the secmon MPU region
   [SECMON_START = FIRMWARE_START_S, +_secmon_size] covers both. */
FW_MANIFEST_REGION = 0x400;

MEMORY {
  FLASH (rx)     : ORIGIN = FIRMWARE_START_S, LENGTH = FIRMWARE_MAXSIZE
  RAM (rw)       : ORIGIN = SECMON_RAM_START, LENGTH = SECMON_RAM_SIZE
  BOOT_ARGS (rw) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  FB1_RAM (rw)   : ORIGIN = FB1_RAM_START, LENGTH = FB1_RAM_SIZE
  FB2_RAM (rw)   : ORIGIN = FB2_RAM_START, LENGTH = FB2_RAM_SIZE
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
  /* Reserve the firmware manifest region at the firmware start (the manifest
     itself is emitted by the firmware image, not the secmon; here it only shifts
     the addresses so the secmon runs at its real address). Mirrors kernel_pq.ld.
     Excluded from secmon.bin via the project's elf_sections, so the module image
     is just [header | code]. */
  .manifest : ALIGN(CODE_ALIGNMENT) {
    _manifest_start = .;
    . = _manifest_start + FW_MANIFEST_REGION;
  } >FLASH AT>FLASH

  /* Merkle-tree layout (pq_secure_boot feature): the secmon module header
     (TRZM, see module_header.S) at the module start; no legacy vendor/TSEC
     header. The tree signer fills its chunk hashes over the secmon code. */
  .header : ALIGN(4) {
    KEEP(*(.header));
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
    . = ALIGN(4);
  } >FLASH

  /* .data and .bss are intentionally placed before the .stack
     section to ensure they are located in SRAM2, which is
     cleared on security events */

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(4);
  } >RAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >RAM

  .stack : ALIGN(8) {
    . = 80K; /* Overflow causes UsageFault */
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
    BYTE(0x00)
    FILL(0x00)
    . = ALIGN(8K);
    _secmon_flash_end = .;
  } >FLASH
}
