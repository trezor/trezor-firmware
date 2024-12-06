INCLUDE "./embed/sys/linker/stm32u58/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = KERNEL_START, LENGTH = FIRMWARE_MAXSIZE
  COREAPP_RAM (wal) : ORIGIN = AUX_RAM_START, LENGTH = AUX_RAM_SIZE
  COREAPP_RAM2 (wal) : ORIGIN = COREAPP_RAM2_START, LENGTH = COREAPP_RAM2_SIZE
}

main_stack_base = ADDR(.stack) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ADDR(.stack);
_estack = main_stack_base;
_stack_size = SIZEOF(.stack);

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);
bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

/* used by the startup code to populate variables used by the C code */
confidential_lma = LOADADDR(.confidential);
confidential_vma = ADDR(.confidential);
confidential_size = SIZEOF(.confidential);

_codelen = SIZEOF(.flash) + SIZEOF(.data) + SIZEOF(.confidential);
_flash_start = ORIGIN(FLASH);
_flash_end = ORIGIN(FLASH) + LENGTH(FLASH);
_heap_start = ADDR(.heap);
_heap_end = ADDR(.heap) + SIZEOF(.heap);

SECTIONS {
  .vendorheader : ALIGN(4) {
    KEEP(*(.vendorheader))
  } >FLASH AT>FLASH

  .header : ALIGN(4) {
    KEEP(*(.header));
    . = ALIGN(CODE_ALIGNMENT);
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.kernel));
    . = ALIGN(COREAPP_ALIGNMENT);
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >COREAPP_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >COREAPP_RAM

  .stack : ALIGN(8) {
    . = 32K; /* Overflow causes UsageFault */
  } >COREAPP_RAM2

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(512);
  } >COREAPP_RAM2 AT>FLASH

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >COREAPP_RAM2

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(ORIGIN(COREAPP_RAM2) + LENGTH(COREAPP_RAM2)); /* this explicitly sets the end of the heap */
  } >COREAPP_RAM2
}
