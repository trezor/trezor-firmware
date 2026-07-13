ENTRY(reset_handler)

/* Merkle-tree layout: the firmware manifest occupies FW_MANIFEST_REGION at the
   firmware start (before the secmon prefix), so the kernel code links at its
   real, manifest-shifted run address. */
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

/* Kernel code length only -- excludes the secmon prefix and the module header,
   which are not covered by this module's chunk hashes. */
_codelen = _kernel_flash_end - _kernel_flash_start;

SECTIONS {
  /* Reserve the firmware manifest region at the firmware start (the manifest
     itself is emitted by the firmware image, not the kernel; here it only
     shifts the addresses so the kernel code links at its real run address). */
  .manifest : ALIGN(CODE_ALIGNMENT) {
    _manifest_start = .;
    . = _manifest_start + FW_MANIFEST_REGION;
  } >FLASH AT>FLASH

  /* Merkle-tree layout: the secmon binary is prefixed (excluded from the module
     hash) so the kernel links at its real run address; then the module header;
     then the kernel code. No legacy vendor header. */
  .secmon : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.secmon));
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    . += 1K;
    . = ALIGN(CODE_ALIGNMENT);
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
    *(.no_dma_buffers*);
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
