// supervisor call functions

#define SVC_ENABLE_IRQ 0
#define SVC_DISABLE_IRQ 1
#define SVC_SET_PRIORITY 2

static inline uint32_t is_mode_unprivileged(void) {
  uint32_t r0;
  __asm__ volatile("mrs %0, control" : "=r"(r0));
  return r0 & 1;
}

static inline void svc_enableIRQ(uint32_t IRQn) {
  if (is_mode_unprivileged()) {
    register uint32_t r0 __asm__("r0") = IRQn;
    __asm__ __volatile__("svc %0" ::"i"(SVC_ENABLE_IRQ), "r"(r0) : "memory");
  } else {
    HAL_NVIC_EnableIRQ(IRQn);
  }
}

static inline void svc_disableIRQ(uint32_t IRQn) {
  if (is_mode_unprivileged()) {
    register uint32_t r0 __asm__("r0") = IRQn;
    __asm__ __volatile__("svc %0" ::"i"(SVC_DISABLE_IRQ), "r"(r0) : "memory");
  } else {
    HAL_NVIC_DisableIRQ(IRQn);
  }
}

static inline void svc_setpriority(uint32_t IRQn, uint32_t priority) {
  if (is_mode_unprivileged()) {
    register uint32_t r0 __asm__("r0") = IRQn;
    register uint32_t r1 __asm__("r1") = priority;
    __asm__ __volatile__("svc %0" ::"i"(SVC_SET_PRIORITY), "r"(r0), "r"(r1)
                         : "memory");
  } else {
    NVIC_SetPriority(IRQn, priority);
  }
}
