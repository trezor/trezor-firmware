/* STM32F205RE - 512K Flash, 128K RAM */
MEMORY
{
	rom (rx)  : ORIGIN = 0x20000000, LENGTH = 20K
	ram (rwx) : ORIGIN = ORIGIN(rom) + LENGTH(rom),
		    LENGTH = 128K - LENGTH(rom)
}

INCLUDE libopencm3_stm32f2.ld
