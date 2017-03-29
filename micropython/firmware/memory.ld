/*
    TREZORv2 linker script
    based on common.ld and stm32f405.ld
*/

/* Specify the memory areas */
MEMORY
{
    FLASH (rx)      : ORIGIN = 0x08020000, LENGTH =  896K
    CCMRAM (xrw)    : ORIGIN = 0x10000000, LENGTH =   64K
    RAM (xrw)       : ORIGIN = 0x20000000, LENGTH =  128K
}

/* produce a link error if there is not this amount of RAM for these sections */
_minimum_stack_size = 2K;
_minimum_heap_size = 16K;

/* Define tho top end of the stack.  The stack is full descending so begins just
   above last byte of RAM.  Note that EABI requires the stack to be 8-byte
   aligned for a call. */
_estack = ORIGIN(RAM) + LENGTH(RAM);

ENTRY(Reset_Handler)

/* define output sections */
SECTIONS
{
    /* The startup code goes first into FLASH */
    .flash :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector)) /* Startup code */
        . = ALIGN(4);
        *(.text*)          /* .text* sections (code) */
        *(.rodata*)        /* .rodata* sections (constants, strings, etc.) */
        . = ALIGN(4);
        _etext = .;        /* define a global symbol at end of code */
    } >FLASH

    /* used by the startup to initialize data */
    _sidata = LOADADDR(.data);

    /* This is the initialized data section
    The program executes knowing that the data is in the RAM
    but the loader puts the initial values in the FLASH (inidata).
    It is one task of the startup to copy the initial values from FLASH to RAM. */
    .data :
    {
        . = ALIGN(4);
        _sdata = .;        /* create a global symbol at data start; used by startup code in order to initialise the .data section in RAM */
        *(.data*)          /* .data* sections */

        . = ALIGN(4);
        _edata = .;        /* define a global symbol at data end; used by startup code in order to initialise the .data section in RAM */
    } >RAM AT> FLASH

    /* Uninitialized data section */
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;         /* define a global symbol at bss start; used by startup code */
        *(.bss*)
        *(COMMON)

        . = ALIGN(4);
        _ebss = .;         /* define a global symbol at bss end; used by startup code and GC */
    } >RAM

    /* this is to define the start of the heap, and make sure we have a minimum size */
    .heap :
    {
        . = ALIGN(4);
        . = . + _minimum_heap_size;
        . = ALIGN(4);
    } >RAM

    /* this just checks there is enough RAM for the stack */
    .stack :
    {
        . = ALIGN(4);
        . = . + _minimum_stack_size;
        . = ALIGN(4);
    } >RAM

    .ARM.attributes 0 : { *(.ARM.attributes) }
}

/* RAM extents for the garbage collector */
_ram_start = ORIGIN(RAM);
_ram_end = ORIGIN(RAM) + LENGTH(RAM);
_heap_start = _ebss; /* heap starts just after statically allocated memory */
_heap_end = 0x2001c000; /* tunable */
