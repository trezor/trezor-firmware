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

  .global jump_to
  .type jump_to, STT_FUNC
jump_to:
  mov r4, r0            // save input argument r0 (the address of the next stage's vector table) (r4 is callee save)
  // this subroutine re-points the exception handlers before the C code
  // that comprises them has been given a good environment to run.
  // therefore, this code needs to disable interrupts before the VTOR
  // update. then, the reset_handler of the next stage needs to re-enable interrupts.
  // the following prevents activation of all exceptions except Non-Maskable Interrupt (NMI).
  // according to "ARM Cortex-M Programming Guide to Memory Barrier Instructions" Application Note 321, section 4.8:
  // "there is no requirement to insert memory barrier instructions after CPSID".
  cpsid f
  // wipe memory at the end of the current stage of code
  bl clear_otg_hs_memory
  ldr r0, =ccmram_start // r0 - point to beginning of CCMRAM
  ldr r1, =ccmram_end   // r1 - point to byte after the end of CCMRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg
  ldr r0, =sram_start   // r0 - point to beginning of SRAM
  ldr r1, =sram_end     // r1 - point to byte after the end of SRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg
  mov lr, r4
  // clear out the general purpose registers before the next stage's code can run (even the NMI exception handler)
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
  // give the next stage a fresh main stack pointer
  ldr r0, [lr]          // set r0 to the main stack pointer in the next stage's vector table
  msr msp, r0           // give the next stage its main stack pointer
  // point to the next stage's exception handlers
  // AN321, section 4.11: "a memory barrier is not required after a VTOR update"
  .set SCB_VTOR, 0xE000ED08 // reference "Cortex-M4 Devices Generic User Guide" section 4.3
  ldr r0, =SCB_VTOR
  str lr, [r0]
  mov r0, r1            // zero out r0
  // go on to the next stage
  ldr lr, [lr, 4]       // set lr to the next stage's reset_handler
  bx lr

  .global jump_to_unprivileged
  .type jump_to_unprivileged, STT_FUNC
jump_to_unprivileged:
  mov r4, r0            // save input argument r0 (the address of the next stage's vector table) (r4 is callee save)
  // this subroutine re-points the exception handlers before the C code
  // that comprises them has been given a good environment to run.
  // therefore, this code needs to disable interrupts before the VTOR
  // update. then, the reset_handler of the next stage needs to re-enable interrupts.
  // the following prevents activation of all exceptions except Non-Maskable Interrupt (NMI).
  // according to "ARM Cortex-M Programming Guide to Memory Barrier Instructions" Application Note 321, section 4.8:
  // "there is no requirement to insert memory barrier instructions after CPSID".
  cpsid f
  // wipe memory at the end of the current stage of code
  bl clear_otg_hs_memory
  ldr r0, =ccmram_start // r0 - point to beginning of CCMRAM
  ldr r1, =ccmram_end   // r1 - point to byte after the end of CCMRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg
  ldr r0, =sram_start   // r0 - point to beginning of SRAM
  ldr r1, =sram_end     // r1 - point to byte after the end of SRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg
  mov lr, r4
  // clear out the general purpose registers before the next stage's code can run (even the NMI exception handler)
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
  // give the next stage a fresh main stack pointer
  ldr r0, [lr]          // set r0 to the main stack pointer in the next stage's vector table
  msr msp, r0           // give the next stage its main stack pointer
  // point to the next stage's exception handlers
  // AN321, section 4.11: "a memory barrier is not required after a VTOR update"
  .set SCB_VTOR, 0xE000ED08 // reference "Cortex-M4 Devices Generic User Guide" section 4.3
  ldr r0, =SCB_VTOR
  str lr, [r0]
  mov r0, r1            // zero out r0
  // go on to the next stage
  ldr lr, [lr, 4]       // set lr to the next stage's reset_handler
  // switch to unprivileged mode
  ldr r0, =1
  msr control, r0
  isb
  // jump
  bx lr

  .global shutdown_privileged
  .type shutdown_privileged, STT_FUNC
  // The function must be called from the privileged mode
shutdown_privileged:
  cpsid f // disable all exceptions (except for NMI), the instruction is ignored in unprivileged mode
  // if the exceptions weren't disabled, an exception handler (for example systick handler)
  // could be called after the memory is erased, which would lead to another exception
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
  ldr r0, =ccmram_start
  ldr r1, =ccmram_end
  // set to value in r2
  bl memset_reg
  ldr r0, =sram_start
  ldr r1, =sram_end
  // set to value in r2
  bl memset_reg
  bl clear_otg_hs_memory
  ldr r0, =1
  msr control, r0 // jump to unprivileged mode
  ldr r0, =0
  b . // loop forever

  .end
