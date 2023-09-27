// supervisor call functions

#define SVC_ENABLE_IRQ 0
#define SVC_DISABLE_IRQ 1
#define SVC_SET_PRIORITY 2
#define SVC_SHUTDOWN 4
#define SVC_REBOOT_TO_BOOTLOADER 5
#define SVC_REBOOT_COPY_IMAGE_HEADER 6
#define SVC_GET_SYSTICK_VAL 7

#include <string.h>
#include "common.h"
#include "image.h"

// from common.c
extern uint32_t systick_val_copy;

// from util.s
extern void shutdown_privileged(void);
extern void reboot_to_bootloader(void);
extern void copy_image_header_for_bootloader(const uint8_t *image_header);
extern void ensure_compatible_settings(void);

static inline uint32_t is_mode_unprivileged(void) {
  uint32_t r0;
  __asm__ volatile("mrs %0, control" : "=r"(r0));
  return r0 & 1;
}

static inline uint32_t is_mode_handler(void) {
  uint32_t r0;
  __asm__ volatile("mrs %0, ipsr" : "=r"(r0));
  return (r0 & 0x1FF) != 0;
}

static inline void svc_enableIRQ(uint32_t IRQn) {
  if (is_mode_unprivileged() && !is_mode_handler()) {
    register uint32_t r0 __asm__("r0") = IRQn;
    __asm__ __volatile__("svc %0" ::"i"(SVC_ENABLE_IRQ), "r"(r0) : "memory");
  } else {
    HAL_NVIC_EnableIRQ(IRQn);
  }
}

static inline void svc_disableIRQ(uint32_t IRQn) {
  if (is_mode_unprivileged() && !is_mode_handler()) {
    register uint32_t r0 __asm__("r0") = IRQn;
    __asm__ __volatile__("svc %0" ::"i"(SVC_DISABLE_IRQ), "r"(r0) : "memory");
  } else {
    HAL_NVIC_DisableIRQ(IRQn);
  }
}

static inline void svc_setpriority(uint32_t IRQn, uint32_t priority) {
  if (is_mode_unprivileged() && !is_mode_handler()) {
    register uint32_t r0 __asm__("r0") = IRQn;
    register uint32_t r1 __asm__("r1") = priority;
    __asm__ __volatile__("svc %0" ::"i"(SVC_SET_PRIORITY), "r"(r0), "r"(r1)
                         : "memory");
  } else {
    NVIC_SetPriority(IRQn, priority);
  }
}

static inline void svc_shutdown(void) {
  if (is_mode_unprivileged() && !is_mode_handler()) {
    __asm__ __volatile__("svc %0" ::"i"(SVC_SHUTDOWN) : "memory");
  } else {
    shutdown_privileged();
  }
}

static inline void svc_reboot_to_bootloader(void) {
  explicit_bzero(&firmware_header_start, IMAGE_HEADER_SIZE);
  if (is_mode_unprivileged() && !is_mode_handler()) {
    __asm__ __volatile__("svc %0" ::"i"(SVC_REBOOT_TO_BOOTLOADER) : "memory");
  } else {
    ensure_compatible_settings();
    reboot_to_bootloader();
  }
}

static inline void svc_reboot_copy_image_header(const uint8_t *image_address) {
  if (is_mode_unprivileged() && !is_mode_handler()) {
    register const uint8_t *r0 __asm__("r0") = image_address;
    __asm__ __volatile__("svc %0" ::"i"(SVC_REBOOT_COPY_IMAGE_HEADER), "r"(r0)
                         : "memory");
  } else {
    copy_image_header_for_bootloader(image_address);
    ensure_compatible_settings();
    reboot_to_bootloader();
  }
}

static inline uint32_t svc_get_systick_val(void) {
  if (is_mode_unprivileged() && !is_mode_handler()) {
    __asm__ __volatile__("svc %0" ::"i"(SVC_GET_SYSTICK_VAL) : "memory");
    return systick_val_copy;
  } else {
    systick_val_copy = SysTick->VAL;
    return systick_val_copy;
  }
}
