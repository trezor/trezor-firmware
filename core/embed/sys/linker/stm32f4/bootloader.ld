INCLUDE "./embed/sys/linker/stm32f4/memory.ld";

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)     : ORIGIN = BOOTLOADER_START, LENGTH = BOOTLOADER_MAXSIZE
  MAIN_STACK (wal)  : ORIGIN = S_MAIN_STACK_START, LENGTH = S_MAIN_STACK_SIZE
  MAIN_RAM (wal)  : ORIGIN = S_MAIN_RAM_START, LENGTH = S_MAIN_RAM_SIZE
  FB1 (wal)       : ORIGIN = S_FB1_RAM_START, LENGTH = S_FB1_RAM_SIZE
  BOOT_ARGS (wal) : ORIGIN = BOOTARGS_START, LENGTH = BOOTARGS_SIZE
  AUX1_RAM   (wal) : ORIGIN = AUX1_RAM_START, LENGTH = AUX1_RAM_SIZE
}

_stack_section_start = ADDR(.stack);
_stack_section_end = ADDR(.stack) + SIZEOF(.stack);

_data_section_loadaddr = LOADADDR(.data);
_data_section_start = ADDR(.data);
_data_section_end = ADDR(.data) + SIZEOF(.data);

_bss_section_start = ADDR(.bss);
_bss_section_end = ADDR(.bss) + SIZEOF(.bss);

_confidential_section_loadaddr = 0;
_confidential_section_start = 0;
_confidential_section_end = 0;

_accessible_ram_0_start = MCU_CCMRAM;
_accessible_ram_0_end = MCU_CCMRAM + MCU_CCMRAM_SIZE;
_accessible_ram_1_start = MCU_SRAM;
_accessible_ram_1_end = MCU_SRAM + MCU_SRAM_SIZE;

_bootargs_ram_start = BOOTARGS_START;
_bootargs_ram_end = BOOTARGS_START + BOOTARGS_SIZE;

_codelen = SIZEOF(.flash) + SIZEOF(.data);

SECTIONS {
  .header : ALIGN(4) {
    KEEP(*(.header));
  } >FLASH AT>FLASH

  .flash : ALIGN(CODE_ALIGNMENT) {
    KEEP(*(.vector_table));
    . = ALIGN(4);
    *(.text*);
    . = ALIGN(4);
    *(.rodata*);
    . = ALIGN(512);
  } >FLASH AT>FLASH

  .stack : ALIGN(8) {
    . = 16K; /* Exactly 16K allocated for stack. Overflow causes MemManage fault (when using MPU). */
  } >MAIN_STACK

  .data : ALIGN(4) {
    *(.data*);
    . = ALIGN(512);
  } >MAIN_RAM AT>FLASH

  /DISCARD/ : {
    *(.ARM.exidx*);
  }

  .bss : ALIGN(4) {
    *(.bss*);
    . = ALIGN(4);
  } >MAIN_RAM

  .fb : ALIGN(4) {
    *(.fb1*);
    . = ALIGN(4);
  } >FB1

  .buf : ALIGN(4) {
    *(.buf*);
    . = ALIGN(4);
    *(.no_dma_buffers*);
    . = ALIGN(4);
  } >AUX1_RAM

  .boot_args : ALIGN(8) {
    *(.boot_args*);
    . = ALIGN(8);
  } >BOOT_ARGS

}
