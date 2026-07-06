OUTPUT_ARCH(arm)
ENTRY(applet_main)

PHDRS {
  rx PT_LOAD FLAGS(5);   /* R | X */
  rw PT_LOAD FLAGS(6);   /* R | W */
  rel PT_LOAD FLAGS(4);
}

SECTIONS
{
  . = 0xC0000000;

  .text : {
    *(.text .text.*)
    *(.dynsym) *(.dynstr) *(.hash)
  } :rx

  .rodata : {
    *(.rodata .rodata.*)
  } : rx

  . = 0xD0000000;

  .data : ALIGN(32) {
    *(.data .data.*)
    *(.sdata .sdata.*)
  } :rw

  .bss (NOLOAD) : {
    *(.bss .bss.* COMMON)
    *(.sbss .sbss.*)
  } :rw

  .rel : {
    *(.rel.text)
    *(.rel.rodata)
    *(.rel.data)
  } :rel

  /DISCARD/ : {
    *(.ARM.exidx*) *(.comment*)
  }
}
