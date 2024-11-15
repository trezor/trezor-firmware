
#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>

#ifdef KERNEL_MODE
void display_init(display_content_mode_t mode) {}

void display_deinit(display_content_mode_t mode) {}

void display_set_unpriv_access(bool unpriv) {}

int display_set_backlight(int level) { return level; }

int display_get_backlight(void) { return 0; }

int display_set_orientation(int angle) { return angle; }
int display_get_orientation(void) { return 0; }
bool display_get_frame_buffer(display_fb_info_t *fb) { return true; }

void display_refresh(void) {}
void display_fill(const gfx_bitblt_t *bb) {}
void display_copy_rgb565(const gfx_bitblt_t *bb) {}
void display_copy_mono4(const gfx_bitblt_t *bb) {}
void display_copy_mono1p(const gfx_bitblt_t *bb) {}

#endif
