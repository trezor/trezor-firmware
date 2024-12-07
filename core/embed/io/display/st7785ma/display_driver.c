
#include <sys/systick.h>
#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <sys/mpu.h>
#include <sys/trustzone.h>
#include "../backlight/backlight_pwm.h"

// Hardware requires physical frame buffer alignment
#ifdef USE_TRUSTZONE
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT TZ_SRAM_ALIGNMENT
#else
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT 32
#endif

// Size of the physical frame buffer in bytes
#define PHYSICAL_FRAME_BUFFER_SIZE               \
  ALIGN_UP_CONST(DISPLAY_RESX *DISPLAY_RESY * 2, \
                 PHYSICAL_FRAME_BUFFER_ALIGNMENT)

static
    __attribute__((section(".fb1"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
    uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE];

#if (FRAME_BUFFER_COUNT > 1)
static
    __attribute__((section(".fb2"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
    uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE];
#endif

void display_init(display_content_mode_t mode) {
  __HAL_RCC_GPIOE_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure;

  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = GPIO_PIN_2;
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, GPIO_PIN_RESET);
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

  GPIO_InitStructure.Pin = GPIO_PIN_0;
  // default to keeping display in reset
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_0, GPIO_PIN_RESET);
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

  hal_delay(100);
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, GPIO_PIN_SET);

  backlight_pwm_init(mode);
}

void display_deinit(display_content_mode_t mode) { backlight_pwm_deinit(mode); }

void display_set_unpriv_access(bool unpriv) {}

int display_set_backlight(int level) {
  return 0;
  // return backlight_pwm_set(level);
}

int display_get_backlight(void) { return backlight_pwm_get(); }

int display_set_orientation(int angle) { return angle; }
int display_get_orientation(void) { return 0; }

// Returns the pointer to the physical frame buffer (0.. FRAME_BUFFER_COUNT-1)
// Returns NULL if the framebuffer index is out of range.
static uint8_t *get_fb_ptr(uint32_t index) { return physical_frame_buffer_0; }

bool display_get_frame_buffer(display_fb_info_t *fb) {
  fb->ptr = get_fb_ptr(0);
  fb->stride = DISPLAY_RESX * sizeof(uint16_t);
  // Enable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(fb->ptr, PHYSICAL_FRAME_BUFFER_SIZE);

  return true;
}

void display_refresh(void) {}
void display_fill(const gfx_bitblt_t *bb) {}
void display_copy_rgb565(const gfx_bitblt_t *bb) {}
void display_copy_mono4(const gfx_bitblt_t *bb) {}
void display_copy_mono1p(const gfx_bitblt_t *bb) {}

#endif
