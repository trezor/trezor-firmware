INCLUDE "./embed/sys/linker/stm32u58/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = BOARDLOADER_START, LENGTH = BOARDLOADER_MAXSIZE
  BOARDCAPS (rx)  : ORIGIN = BOARDCAPS_START, LENGTH = BOARDCAPS_MAXSIZE

  MAIN_RAM (wal) : ORIGIN = MAIN_RAM_START, LENGTH = MAIN_RAM_SIZE
  AUX1_RAM (wal) : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  SAES_RAM (wal) : ORIGIN = SAES_RAM_START, LENGTH = SAES_RAM_SIZE
  FB1_RAM (wal) : ORIGIN = FB1_RAM_START, LENGTH = FB1_RAM_SIZE
  FB2_RAM (wal) : ORIGIN = FB2_RAM_START, LENGTH = FB2_RAM_SIZE
}

_stack_section_start = ADDR(.stack);
_stack_section_end = ADDR(.stack) + SIZEOF(.stack);

_data_section_loadaddr = LOADADDR(.data);
_data_section_start = ADDR(.data);
_data_section_end = ADDR(.data) + SIZEOF(.data);

_bss_section_start = ADDR(.bss);
_bss_section_end = ADDR(.bss) + SIZEOF(.bss);

_confidential_section_loadaddr = LOADADDR(.confidential);
_confidential_section_start = ADDR(.confidential);
_confidential_section_end = ADDR(.confidential) + SIZEOF(.confidential);

_accessible_ram_0_start = MCU_SRAM1;
_accessible_ram_0_end = MCU_SRAM3 + MCU_SRAM3_SIZE;
_accessible_ram_1_start = MCU_SRAM4;
_accessible_ram_1_end =  MCU_SRAM4 + MCU_SRAM4_SIZE;

_bootargs_ram_start = BOOTARGS_START;
_bootargs_ram_end = BOOTARGS_START + BOOTARGS_SIZE;

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

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(8);
  } >AUX1_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >AUX1_RAM

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
  } >AUX1_RAM

  .stack : ALIGN(8) {
    . = 16K; /* Overflow causes UsageFault */
  } >MAIN_RAM

  .confidential : ALIGN(8) {
    *(.confidential*);
    . = ALIGN(4);
  } >MAIN_RAM AT>FLASH

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

  .capabilities : ALIGN(4) {
    KEEP(*(.capabilities_section*));
    . = ALIGN(4);
  } >BOARDCAPS
}
