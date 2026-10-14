ENTRY(reset_handler)

/* Merkle-tree layout: manifest region, then the secmon module, then kernel+
   coreapp. See docs/core/embed-arch/firmware-merkle-tree.md. */
FW_MANIFEST_REGION = 0x400;
/* Smart-hashing chunk size stamped into the manifest entries; not a padding
   constant. Must match FW_CHUNK_SIZE in sec/boot_header.h. */
FW_CHUNK_SIZE = 0x2000;

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

/* Module code regions (offset from the firmware start + size) for the manifest
   entries emitted by manifest_header.S; headertool_pq fills the code_hash. */
_manifest_secmon_addr = ADDR(.secmon) - FIRMWARE_START;
_manifest_secmon_size = SIZEOF(.secmon);
_manifest_kernel_addr = ADDR(.padding) - FIRMWARE_START;
_manifest_kernel_size = _codelen;

SECTIONS {
  /* Manifest, padded to FW_MANIFEST_REGION by manifest_header.S. */
  .manifest : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.manifest));
  } >FLASH AT>FLASH

  /* Secmon module prefix; a separate module, excluded from _codelen. */
  .secmon : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.secmon));
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
    *(.bss*);
    . = ALIGN(4);
  } >AUX1_RAM

  .buf (NOLOAD): ALIGN(4) {
    *(.no_dma_buffers*);
    . = ALIGN(4);
    *(.buf*);
    . = ALIGN(4);
  } >AUX1_RAM

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(ORIGIN(AUX1_RAM) + LENGTH(AUX1_RAM)); /* this explicitly sets the end of the heap */
  } >AUX1_RAM

}
