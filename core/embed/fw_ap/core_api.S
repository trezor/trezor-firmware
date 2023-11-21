     #include <embed/fw_cs/svc_numbers.h>

    .syntax unified

    .text

    .global core_print
    .global core_get_secret

core_print:
    svc     #CORE_SVC_PRINT
    bx      lr

core_get_secret:
    svc     #CORE_SVC_GET_SECRET
    bx      lr


    .end
