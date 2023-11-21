  .syntax unified

  .text

  .global reset_handler

  .type reset_handler, STT_FUNC
reset_handler:
  // setup environment for subsequent stage of code
  ldr r2, =0             // r2 - the word-sized value to be written

  ldr r0, =sram1_start   // r0 - point to beginning of SRAM
  ldr r1, =sram1_end     // r1 - point to byte after the end of SRAM

sram1_loop:
  str r2, [r0], #4
  cmp r0, r1
  bne sram1_loop

  ldr r0, =sram2_start   // r0 - point to beginning of SRAM
  ldr r1, =sram2_end     // r1 - point to byte after the end of SRAM
sram2_loop:
  str r2, [r0], #4
  cmp r0, r1
  bne sram2_loop

  // copy data in from flash
  ldr r0, =data_vma     // dst addr
  ldr r1, =data_lma     // src addr
  ldr r2, =data_size    // size in bytes
  bl memcpy

  // setup the stack protector (see build script "-fstack-protector-all") with an unpredictable value
  ldr r0, =0xF1CD3A4D
  ldr r1, = __stack_chk_guard
  str r0, [r1]

  // call static constructors
  //bl __libc_init_array

reset: // just for the nice backtrace
  // enter the application code
  bl main


loop_forever:
  b loop_forever

// ================================================================
// The minimal vector table for unprivileged application

 	.section	.vector_table,"a",%progbits

vector_table:
	.word	_estack
	.word	reset_handler


  .end
