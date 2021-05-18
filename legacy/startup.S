  .syntax unified

  .text

  .global memset_reg
  .type memset_reg, STT_FUNC
memset_reg:
  // call with the following (note that the arguments are not validated prior to use):
  // r0 - address of first word to write (inclusive)
  // r1 - address of first word following the address in r0 to NOT write (exclusive)
  // r2 - word value to be written
  // both addresses in r0 and r1 needs to be divisible by 4!
  .L_loop_begin:
    str r2, [r0], 4 // store the word in r2 to the address in r0, post-indexed
    cmp r0, r1
  bne .L_loop_begin
  bx lr

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:

#if MEMORY_PROTECT
// we need to perform this in case an old bootloader (<1.8.0)
// is starting the new firmware, these will be set incorrectly
  ldr r0, =0xE000ED08  // r0 = VTOR address
  ldr r1, =0x08010400  // r1 = FLASH_APP_START
  str r1, [r0]         // assign
  ldr r0, =_stack      // r0 = stack pointer
  msr msp, r0          // set stack pointer
  dsb
  isb
#endif

  ldr r0, =_stay_in_bootloader_flag_addr  // r0 - address of storage for "stay in bootloader" flag
  ldr r11, [r0]        // r11 - keep in register and hope it gets to main

  ldr r0, =_ram_start // r0 - point to beginning of SRAM
  ldr r1, =_ram_end   // r1 - point to byte after the end of SRAM
  ldr r2, =0          // r2 - the byte-sized value to be written
  bl memset_reg

  // copy .data section from flash to SRAM
  ldr r0, =_data          // dst addr
  ldr r1, =_data_loadaddr // src addr
  ldr r2, =_data_size     // length in bytes
  bl memcpy

  // enter the application code
  bl main

  // shutdown if the application code returns
  b shutdown

  .global shutdown
  .type shutdown, STT_FUNC
shutdown:
  cpsid f
  ldr r0, =0
  mov r1, r0
  mov r2, r0
  mov r3, r0
  mov r4, r0
  mov r5, r0
  mov r6, r0
  mov r7, r0
  mov r8, r0
  mov r9, r0
  mov r10, r0
  mov r11, r0
  mov r12, r0
  ldr lr, =0xffffffff
  ldr r0, =_ram_start
  ldr r1, =_ram_end
  // set to value in r2
  bl memset_reg
  b . // loop forever

  .ltorg // dump literal pool (for the ldr ...,=... commands above)

  .global sv_call_handler
  .type sv_call_handler, STT_FUNC

sv_call_handler:
  tst lr, #4
  ite eq
  mrseq r0, msp
  mrsne r0, psp
  b svc_handler_main

  .end
