/* TREZORv2 boardloader linker script */

ENTRY(reset_handler)

MEMORY {
  FLASH  (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
  CCMRAM (wal) : ORIGIN = 0x10000000, LENGTH = 64K
  SRAM   (wal) : ORIGIN = 0x20000000, LENGTH = 128K /* note: the boardloader uses mostly CCMRAM */
}

main_stack_base = ORIGIN(CCMRAM) + LENGTH(CCMRAM); /* 8-byte aligned full descending stack */

minimum_stack_size = 4K; /* reserve a chunk for stack space */

/* used by the startup code to populate variables used by the C code */
data_lma = LOADADDR(.data);
data_vma = ADDR(.data);
data_size = SIZEOF(.data);

/* used by the startup code to wipe memory */
ccmram_start = ORIGIN(CCMRAM);
ccmram_end = ORIGIN(CCMRAM) + LENGTH(CCMRAM);

/* used by the startup code to wipe memory */
sram_start = ORIGIN(SRAM);
sram_end = ORIGIN(SRAM) + LENGTH(SRAM);

/* alignment references refer to sections in the ARM v7-M Architecture Reference Manual */

SECTIONS {
  .vector_table : ALIGN(512) { /* B1.5.3 and Table 61 of STM32F405 Reference Manual (RM0090) */
    KEEP(*(.vector_table))
  } >FLASH AT>FLASH

  .text : ALIGN(4) { /* A3.3.1 - needs at least 2 */
    KEEP(*(.text)) /* does not match all .text*, but influences their positioning */
    . = ALIGN(4); /* force the section to end on an word-aligned boundary */
  } >FLASH AT>FLASH

  .rodata : ALIGN(4) {
    KEEP(*(.rodata)) /* does not match all .rodata*, but influences their positioning */
    . = ALIGN(4); /* force the section to end on an word-aligned boundary */
  } >FLASH AT>FLASH

  .data : ALIGN(4) {
    KEEP(*(.data*)) /* combine all the .data* so that the startup code can copy it in all at once */
    . = ALIGN(4); /* force the section to end on an word-aligned boundary */
  } >CCMRAM AT>FLASH

  .bss : ALIGN(4) {
    KEEP(*(.bss)) /* does not match all .bss*, but influences their positioning */
    . = ALIGN(4); /* force the section to end on an word-aligned boundary */
  } >CCMRAM

  .stack : ALIGN(8) { /* B1.5.7 */
    . += minimum_stack_size;
    . = ALIGN(8); /* force the section to end on an double word-aligned boundary */
  } >CCMRAM

  /* todo: reduce unused stuff being linked and garbage collected  */
  /*       requires moving code around and updating build scripts. */
  /DISCARD/ : {
    */embed/extmod/modtrezorui/display.o (.text.get_glyph)
    */embed/extmod/modtrezorui/display.o (.text.display_image)
    */embed/extmod/modtrezorui/display.o (.text.display_avatar)
    */embed/extmod/modtrezorui/display.o (.text.display_icon)
    */embed/extmod/modtrezorui/display.o (.text.display_qrcode)
    */embed/extmod/modtrezorui/display.o (.text.display_loader)
    */embed/extmod/modtrezorui/display.o (.text.display_text)
    */embed/extmod/modtrezorui/display.o (.text.display_text_width)
    */embed/extmod/modtrezorui/display.o (.text.display_text_center)
    */embed/extmod/modtrezorui/display.o (.text.display_text_right)
  }
}
