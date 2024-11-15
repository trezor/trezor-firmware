INCLUDE "./embed/sys/linker/stm32u5g/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = KERNEL_START, LENGTH = FIRMWARE_MAXSIZE
  SRAM1  (wal) : ORIGIN = MCU_SRAM1, LENGTH =  0K  /* not allocated to coreapp */
  SRAM2  (wal) : ORIGIN = MCU_SRAM2, LENGTH =  0K  /* not allocated to coreapp */
  SRAM3  (wal) : ORIGIN = MCU_SRAM3, LENGTH =   0K  /* not allocated to coreapp */
  SRAM5  (wal) : ORIGIN = MCU_SRAM5, LENGTH =  MCU_SRAM5_SIZE
  SRAM6  (wal) : ORIGIN = MCU_SRAM6, LENGTH =  0K  /* not allocated to coreapp */
  SRAM4  (wal) : ORIGIN = MCU_SRAM4, LENGTH =  0K  /* not allocated to coreapp */
}

main_stack_base = ORIGIN(SRAM5) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ORIGIN(SRAM5);
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

  .stack : ALIGN(8) {
    . = 32K; /* Overflow causes UsageFault */
  } >SRAM5

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >SRAM5 AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.no_dma_buffers*);
    *(.bss*);
    . = ALIGN(4);
  } >SRAM5

  .confidential : ALIGN(512) {
    *(.confidential*);
    . = ALIGN(512);
  } >SRAM5 AT>FLASH

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >SRAM5

  .heap : ALIGN(4) {
    . = 37K; /* this acts as a build time assertion that at least this much memory is available for heap use */
    . = ABSOLUTE(ORIGIN(SRAM5) + LENGTH(SRAM5)); /* this explicitly sets the end of the heap */
  } >SRAM5

}
