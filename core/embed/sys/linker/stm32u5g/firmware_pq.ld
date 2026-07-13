ENTRY(reset_handler)

/* Merkle-tree layout: the firmware manifest occupies FW_MANIFEST_REGION at the
   firmware start, before the secmon (first module). */
FW_MANIFEST_REGION = 0x400;

MEMORY {
  FLASH  (rx)   : ORIGIN = FIRMWARE_START, LENGTH = FIRMWARE_MAXSIZE
  AUX1_RAM (rw) : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
}

_stack_section_start = ADDR(.stack);
_stack_section_end = ADDR(.stack) + SIZEOF(.stack);
_stack_section_size = SIZEOF(.stack);

_data_section_loadaddr = LOADADDR(.data);
_data_section_start = ADDR(.data);
_data_section_end = ADDR(.data) + SIZEOF(.data);

_bss_section_start = ADDR(.bss);
_bss_section_end = ADDR(.bss) + SIZEOF(.bss);

_tls_section_start = ADDR(.tls);
_tls_section_size = SIZEOF(.tls);

_codelen = SIZEOF(.padding) + SIZEOF(.flash) + SIZEOF(.data);

_heap_start = ADDR(.heap);
_heap_end = ADDR(.heap) + SIZEOF(.heap);

SECTIONS {
  /* Merkle-tree layout (pq_secure_boot feature). The secmon binary is prefixed
     (its own module -- excluded from this module's hash and from _codelen) so
     the kernel+coreapp code links at its real run address. The .header section
     then holds the kernel+coreapp module header (TRZM, see module_header.S),
     replacing the legacy vendor header + image header. */
  /* Firmware manifest ("firmware directory") at the very start of the image,
     before the modules. Its static fields come from manifest_header.S; the
     post-build step (headertool_pq) fills the per-entry addr/size/header_hash.
     The section is padded to FW_MANIFEST_REGION by manifest_header.S. */
  .manifest : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.manifest));
  } >FLASH AT>FLASH

  .secmon : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.secmon));
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH AT>FLASH

  .padding : ALIGN(4) {
    . = ALIGN(4);
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.kernel));
    . = ALIGN(COREAPP_ALIGNMENT);
    KEEP(*(.coreapp_header));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(4);
    KEEP(*(.nrf_app));
    *(.nrf_app*);
    . = ALIGN(4);
    KEEP(*(.bootloader));
    *(.bootloader*);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . += 32K; /* Overflow causes UsageFault */
  } >AUX1_RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >AUX1_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .tls : ALIGN(32) {
    *(.tls*);  /* 32-byte alignment required by MPU */
    . = ALIGN(32);
  } > AUX1_RAM

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >AUX1_RAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >AUX1_RAM

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(ORIGIN(AUX1_RAM) + LENGTH(AUX1_RAM)); /* this explicitly sets the end of the heap */
  } >AUX1_RAM

}
