
#include "core_api.h"
#include "svc_numbers.h"

#include <stdint.h>
#include <cmsis_gcc.h>

#define APP_FIRMWARE_VTBL 0x080D0000

extern void jump_unprivileged(uint32_t location);


// !!! SVC_Handler should have the second lowest priority in the system (just after PendSV_Handler)
//     => SVC_Handler can be prememted by any interrupt
// !!! PendSV_Handler should be used for task switching (entering into app modules)


void SVC_C_Handler(uint32_t *svc_args) {
  // Stack contains:
  //  r0, r1, r2, r3, r12, r14, the return address and xPSR
  //  First argument (r0) is svc_args[0]

  // __LDRT(), __STRT() instrinsic function should be used to access unprivileged memory

  uint8_t svc_number = ((uint8_t *)svc_args[6])[-2];

  switch (svc_number) {
    case CORE_SVC_PRINT:
      core_print((char *)svc_args[0]);
      break;

    case CORE_SVC_GET_SECRET:
      svc_args[0] = core_get_secret();
      break;

    case CORE_SVC_START_APP:
      jump_unprivileged(APP_FIRMWARE_VTBL);
      break;
  }
}
