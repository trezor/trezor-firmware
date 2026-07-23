/*
 * xip_demo_fn.S — Thumb-2 function executed from external flash via OTFDEC XIP.
 *
 * Demonstrates calling a function resident in internal flash (0x08000000) from
 * code running in the OCTOSPI1 memory-mapped window (0x90000000+).  A direct
 * BL instruction cannot bridge the ~2.1 GB gap between the two regions; instead
 * the function pointer is loaded from a context struct in SRAM and called via BLX.
 *
 * Called by prodtest ext-flash-otfdec-exec as:  void xip_demo_fn(xip_ctx_t *ctx)
 *
 * xip_ctx_t layout (prodtest_ext_flash.c, filled before the call):
 *   +0   uint32_t magic              0xD0C0DE00 — written by host
 *   +4   uint32_t (*compute)(x)      fn ptr into internal flash — written by host
 *   +8   uint32_t result             written by THIS function; read after return
 *   +12  uint32_t input              argument for compute() — written by host
 *
 * Build (ARM bare-metal toolchain required):
 *   arm-none-eabi-as -march=armv8-m.main -mthumb \
 *       -o /tmp/xip_demo_fn.o xip_demo_fn.S
 *   arm-none-eabi-objcopy -O binary \
 *       --only-section=.text /tmp/xip_demo_fn.o /tmp/xip_demo_fn.bin
 *   python3 -c "print(open('/tmp/xip_demo_fn.bin','rb').read().hex())"
 *   # Expected: 10b5044601 68e1 6862 6808 4690 47a0 6010bd
 *   # Readable: 10b5 0446 e168 6268 0846 9047 a060 10bd
 *
 * The 16 bytes above are embedded verbatim as THUMB_FN in otfdec_demo.py.
 */

    .syntax unified
    .thumb
    .text

    .global xip_demo_fn
    .type   xip_demo_fn, %function
    .align  2                           /* 4-byte aligned (OTFDEC block boundary) */

xip_demo_fn:
    push    {r4, lr}        /* save LR and callee-saved R4 */
    mov     r4, r0          /* r4 = ctx (R0 is arg-passing, must save early) */
    ldr     r1, [r4, #12]   /* r1 = ctx->input */
    ldr     r2, [r4, #4]    /* r2 = ctx->compute (function pointer in internal flash) */
    mov     r0, r1           /* first argument = input */
    blx     r2               /* call compute(input) — crosses OSPI→internal-flash gap */
    str     r0, [r4, #8]    /* ctx->result = return value */
    pop     {r4, pc}         /* restore R4 and return */

    .size   xip_demo_fn, . - xip_demo_fn
