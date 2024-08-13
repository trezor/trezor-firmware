  .syntax unified

  .text

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:

  // set the stack protection
  ldr r0, =_sstack
  add r0, r0, #128      // safety margin for the exception frame
  msr PSPLIM, r0

  ldr r0, =bss_start
  ldr r1, =bss_end
  ldr r2, =0
  bl memset_reg

  // copy data in from flash
  ldr r0, =data_vma     // dst addr
  ldr r1, =data_lma     // src addr
  ldr r2, =data_size    // size in bytes
  bl memcpy

  // copy confidential data in from flash
  ldr r0, =confidential_vma     // dst addr
  ldr r1, =confidential_lma     // src addr
  ldr r2, =confidential_size    // size in bytes
  bl memcpy

  // setup the stack protector (see build script "-fstack-protector-all") with an unpredictable value
  bl rng_get
  ldr r1, = __stack_chk_guard
  str r0, [r1]

  // enter the application code
  bl main

  b secure_shutdown


memset_reg:
  // call with the following (note that the arguments are not validated prior to use):
  // r0 - address of first word to write (inclusive)
  // r1 - address of first word following the address in r0 to NOT write (exclusive)
  // r2 - word value to be written
  // both addresses in r0 and r1 needs to be divisible by 4!
  cmp r0, r1
  beq .L_loop_end
  .L_loop_begin:
    str r2, [r0], 4 // store the word in r2 to the address in r0, post-indexed
    cmp r0, r1
  bne .L_loop_begin
  .L_loop_end:
  bx lr


  .end
