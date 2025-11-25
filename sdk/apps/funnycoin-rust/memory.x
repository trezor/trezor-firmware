OUTPUT_ARCH(arm)
ENTRY(applet_main)

PHDRS {
  rx PT_LOAD FLAGS(5);   /* R | X */
  rw PT_LOAD FLAGS(6);   /* R | W */
  rel PT_LOAD FLAGS(4);
}

SECTIONS
{
  .text : {
    *(.text .text.*)
    *(.dynsym) *(.dynstr) *(.hash)
  } :rx

  .rodata : {
    *(.rodata .rodata.*)
    *(.data.rel.ro .data.rel.ro.*)
  } : rx

  . = ALIGN(4);
  .data : {
    *(.data .data.*)
    *(.sdata .sdata.*)
  } :rw

  .bss (NOLOAD) : {
    *(.bss .bss.* COMMON)
    *(.sbss .sbss.*)
  } :rw

  .stack (NOLOAD) : {
    _stack_section_start = .;
    . = . + 16K;
    _stack_section_end = .;
  } :rw

  .rel : {
    *(.rel.rodata)
    *(.rel.data)
  } :rel

  /DISCARD/ : {
    *(.ARM.exidx*) *(.comment*)
  }
}
