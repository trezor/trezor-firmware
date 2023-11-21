    .syntax unified

    .text

    .global SVC_Handler

    .thumb_func
SVC_Handler:
    tst lr, #4
    ite eq
    mrseq r0, msp
    mrsne r0, psp
    b SVC_C_Handler

    .end
