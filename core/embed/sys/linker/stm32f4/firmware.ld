INCLUDE "./embed/sys/linker/stm32f4/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = FIRMWARE_P1_START, LENGTH = FIRMWARE_P1_MAXSIZE
  FLASH2 (r)      : ORIGIN = FIRMWARE_P2_START, LENGTH = FIRMWARE_P2_MAXSIZE
  AUX1_RAM (wal)  : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
  AUX2_RAM (wal)  : ORIGIN = AUX2_RAM_START, LENGTH = AUX2_RAM_SIZE
}

_stack_section_start = ADDR(.stack);
_stack_section_end = ADDR(.stack) + SIZEOF(.stack);
_stack_section_size = SIZEOF(.stack);

_data_section_loadaddr = LOADADDR(.data);
_data_section_start = ADDR(.data);
_data_section_end = ADDR(.data) + SIZEOF(.data);

_bss_section_start = ADDR(.bss);
_bss_section_end = ADDR(.bss) + SIZEOF(.bss);

_confidential_section_loadaddr = 0;
_confidential_section_start = 0;
_confidential_section_end = 0;

_codelen = LENGTH(FLASH) - SIZEOF(.vendorheader) - SIZEOF(.header) + SIZEOF(.flash2);
_heap_start = ADDR(.heap);
_heap_end = ADDR(.heap) + SIZEOF(.heap);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH AT>FLASH

  .flash2 : ALIGN(CODE_ALIGNMENT) {
    build/firmware/frozen_mpy.o(.rodata*);
    . = ALIGN(4);
    */libtrezor_lib.a:(.text*);
    . = ALIGN(4);
    */libtrezor_lib.a:(.rodata*);
    . = ALIGN(512);
  } >FLASH2 AT>FLASH2

  .flash : ALIGN(512) {
    KEEP(*(.kernel));
    . = ALIGN(COREAPP_ALIGNMENT);
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(4);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . = 16K; /* Exactly 16K allocated for stack. Overflow causes MemManage fault (when using MPU). */
  } >AUX1_RAM

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >AUX1_RAM AT>FLASH

  .bss : ALIGN(4) {
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

  .data_ccm : ALIGN(4) {
    *(.no_dma_buffers*);
    . = ALIGN(4);
  } >AUX2_RAM


  /DISCARD/ : {
    *(.ARM.exidx*);
  }

}
