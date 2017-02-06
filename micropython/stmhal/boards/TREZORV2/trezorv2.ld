/*
    TREZORv2 linker script
    based on common.ld and stm32f405.ld
*/

/* Specify the memory areas */
MEMORY
{
    FLASH (rx)      : ORIGIN = 0x08000000, LENGTH = 0x100000 /* entire flash, 1 MiB */
    FLASH_ISR (rx)  : ORIGIN = 0x08000000, LENGTH = 0x004000 /* sector 0, 16 KiB */
    FLASH_TEXT (rx) : ORIGIN = 0x08020000, LENGTH = 0x0E0000 /* sectors 5,6,7,8,9,10,11 7*128KiB = 896 KiB */
    CCMRAM (xrw)    : ORIGIN = 0x10000000, LENGTH = 0x010000 /* 64 KiB */
    RAM (xrw)       : ORIGIN = 0x20000000, LENGTH = 0x020000 /* 128 KiB */
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
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector)) /* Startup code */

        /* This first flash block is 16K annd the isr vectors only take up
           about 400 bytes. So we pull in a couple of object files to pad it
           out. */

        . = ALIGN(4);

        /* NOTE: If you update the list of files contained in .isr_vector,
                 then be sure to also update smhal/Makefile where it forcibly
           builds each of these files with -Os */

        */ff.o(.text*)
        */vfs_fat_*.o(.text*)
        */py/formatfloat.o(.text*)
        */py/parsenum.o(.text*)
        */py/mpprint.o(.text*)

        . = ALIGN(4);
    } >FLASH_ISR

    /* The program code and other data goes into FLASH */
    .text :
    {
        . = ALIGN(4);
        *(.text*)          /* .text* sections (code) */
        *(.rodata*)        /* .rodata* sections (constants, strings, etc.) */
    /*  *(.glue_7)   */    /* glue arm to thumb code */
    /*  *(.glue_7t)  */    /* glue thumb to arm code */

        . = ALIGN(4);
        _etext = .;        /* define a global symbol at end of code */
    } >FLASH_TEXT

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
    } >RAM AT> FLASH_TEXT

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
