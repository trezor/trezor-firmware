/* STM32F205RE - 512K Flash, 128K RAM */

MEMORY
{
	rom (rx) : ORIGIN = 0x08000000, LENGTH = 512K
	ram (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

SECTIONS
{
	.confidential (NOLOAD) : {
		*(confidential)
		ASSERT ((SIZEOF(.confidential) <= 33K), "Error: Confidential section too big!");
	} >ram
}

INCLUDE libopencm3_stm32f2.ld

_ram_start = ORIGIN(ram);
_ram_end = ORIGIN(ram) + LENGTH(ram);

_data_size = SIZEOF(.data);
