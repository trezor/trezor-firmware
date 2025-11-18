OUTPUT_ARCH(arm)
ENTRY(applet_main)

PHDRS {
  rx PT_LOAD FLAGS(5);   /* R | X */
  rw PT_LOAD FLAGS(6);   /* R | W */
  rel PT_LOAD FLAGS(4);
}

SECTIONS
{
  . = 0;

  .text : {
    *(.text .text.*)
    *(.rodata .rodata.*)
    *(.dynsym) *(.dynstr) *(.hash)
  } :rx

  . = ALIGN(4);
  .data : {
    *(.data .data.*)
  } :rw

  .bss (NOLOAD) : {
    *(.bss .bss.* COMMON)
  } :rw

  .stack (NOLOAD) : {
    _stack_section_start = .;
    . = . + 16K;
    _stack_section_end = .;
  } :rw

  .rel.data : {
    *(.rel.data)
  } :rel

  /DISCARD/ : { *(.ARM.exidx*) *(.comment*) }
}
