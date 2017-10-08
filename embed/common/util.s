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

  .set SCB_VTOR, 0xE000ED08 // reference "Cortex-M4 Devices Generic User Guide" section 4.3

  .global jump_to
  .type jump_to, STT_FUNC
jump_to:
  mov r4, r0            // save input argument r0
  // todo: this subroutine re-points the exception handlers before the C code
  //       that comprises them have been given a good environment to run.
  //       so, the this needs to disable interrupts before the VTOR
  //       switch and then the reset_handler of the next stage needs to re-enable interrupts.
  // todo: CPSID f
  // wipe memory at the end of the current stage of code
  ldr r0, =ccmram_start // r0 - point to beginning of CCMRAM
  ldr r1, =ccmram_end   // r1 - point to byte after the end of CCMRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg
  ldr r0, =sram_start   // r0 - point to beginning of SRAM
  ldr r1, =sram_end     // r1 - point to byte after the end of SRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg
  // todo: need to think through exception handler races for the VTOR and MSP change below
  //       there are probably corner cases still.
  // use the next stage's exception handlers
  ldr r0, =SCB_VTOR
  str r4, [r0]
  // give the next stage a fresh main stack pointer
  ldr r0, [r4]
  msr msp, r0
  // go on to the next stage
  ldr r0, [r4, 4]
  bx r0

  .end
