INCLUDE "./embed/sys/linker/stm32f4/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = BOARDLOADER_START, LENGTH = BOARDLOADER_MAXSIZE - BOARDCAPS_MAXSIZE
  BOARDCAPS (rx)  : ORIGIN = BOARDCAPS_START, LENGTH = BOARDCAPS_MAXSIZE
  MAIN_STACK (wal)  : ORIGIN = S_MAIN_STACK_START, LENGTH = S_MAIN_STACK_SIZE
  MAIN_RAM (wal)  : ORIGIN = S_MAIN_RAM_START, LENGTH = S_MAIN_RAM_SIZE
  FB1 (wal)       : ORIGIN = S_FB1_RAM_START, LENGTH = S_FB1_RAM_SIZE
  AUX1_RAM (wal)  : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
}

main_stack_base = ADDR(.stack) + SIZEOF(.stack); /* 8-byte aligned full descending stack */
_sstack = ADDR(.stack);
_estack = main_stack_base;

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);
bss_start = ADDR(.bss);
bss_end = ADDR(.bss) + SIZEOF(.bss);

/* used by the startup code to wipe memory */
_startup_clear_ram_0_start = MCU_CCMRAM;
_startup_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_startup_clear_ram_1_start = MCU_SRAM;
_startup_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* used by the startup/jump code to wipe memory */
_handoff_clear_ram_0_start = MCU_CCMRAM;
_handoff_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_handoff_clear_ram_1_start = MCU_SRAM;
_handoff_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

/* used by the shutdown code to wipe memory */
_shutdown_clear_ram_0_start = MCU_CCMRAM;
_shutdown_clear_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_shutdown_clear_ram_1_start = MCU_SRAM;
_shutdown_clear_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

SECTIONS {
  .vector_table : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.vector_table));
  } >FLASH AT>FLASH

  .text : ALIGN(4) {
    *(.text*);
    . = ALIGN(4); /* make the section size a multiple of the word size */
  } >FLASH AT>FLASH

  .rodata : ALIGN(4) {
    *(.rodata*);
    . = ALIGN(4); /* make the section size a multiple of the word size */
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . = 16K; /* this acts as a build time assertion that at least this much memory is available for stack use */
  } >MAIN_STACK

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(4); /* make the section size a multiple of the word size */
  } >MAIN_RAM AT>FLASH

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4); /* make the section size a multiple of the word size */
  } >MAIN_RAM

  .fb : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >FB1

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >AUX1_RAM

  .capabilities : ALIGN(4) {
    KEEP(*(.capabilities_section*));
    . = ALIGN(4);
  } >BOARDCAPS

}
