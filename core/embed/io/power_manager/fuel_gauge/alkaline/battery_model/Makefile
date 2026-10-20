# SoC from OCV - C port for STM32H5 (Cortex-M33).
#   make test     host build with strict warnings + tests against the Python reference
#   make misra    cppcheck MISRA C:2012 addon on src/ and include/
#   make size     Cortex-M33 build (arm-none-eabi-gcc -Os): flash, RAM and stack per function
#   make data     regenerate src/soc_ocv_data.c, include/soc_ocv_data.h and test/test_vectors.h
CC      ?= gcc
SRC     := src/soc_ocv_lut.c src/soc_ocv_poly.c src/soc_ocv_temp.c src/soc_ocv_data.c
INC     := -Iinclude -Isrc
STRICT  := -std=c99 -pedantic -Wall -Wextra -Wconversion -Wsign-conversion -Wdouble-promotion -Wshadow \
           -Wcast-qual -Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations -Wundef -Werror
ARM_CPU := -mcpu=cortex-m33 -mthumb -mfloat-abi=hard -mfpu=fpv5-sp-d16
B       := build

.PHONY: test misra size data clean
test: | $(B)
	$(CC) $(STRICT) -O2 $(INC) -c src/soc_ocv_lut.c -o $(B)/lut.o
	$(CC) $(STRICT) -O2 $(INC) -c src/soc_ocv_poly.c -o $(B)/poly.o
	$(CC) $(STRICT) -O2 $(INC) -c src/soc_ocv_temp.c -o $(B)/temp.o
	$(CC) $(STRICT) -O2 $(INC) -c src/soc_ocv_data.c -o $(B)/data.o
	$(CC) -std=c99 -O2 -Wall -Wextra $(INC) -Itest test/test_soc_ocv.c $(B)/lut.o $(B)/poly.o $(B)/temp.o $(B)/data.o -lm -o $(B)/test_soc_ocv
	./$(B)/test_soc_ocv

misra:
	cppcheck --std=c99 --enable=warning,style,portability --addon=misra --inline-suppr \
	  --suppress=missingIncludeSystem --error-exitcode=1 $(INC) src include

size: | $(B)/arm
	for f in $(SRC) test/size_main.c; do \
	  arm-none-eabi-gcc $(ARM_CPU) -Os -std=c99 -ffunction-sections -fdata-sections -fstack-usage $(STRICT) \
	    $(INC) -c $$f -o $(B)/arm/$$(basename $$f .c).o || exit 1; done
	arm-none-eabi-gcc $(ARM_CPU) --specs=nano.specs --specs=nosys.specs -Wl,--gc-sections \
	  $(B)/arm/*.o -o $(B)/arm/size.elf
	arm-none-eabi-size $(B)/arm/soc_ocv_*.o
	@cat $(B)/arm/soc_ocv_*.su

data:
	cd .. && python3 c/tools/gen_soc_ocv_c.py

$(B) $(B)/arm:
	mkdir -p $@

clean:
	rm -rf $(B)
