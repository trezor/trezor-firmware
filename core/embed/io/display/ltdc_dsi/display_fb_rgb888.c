
#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>

#include <gfx/gfx_bitblt.h>
#include <io/display.h>

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_fill(&bb_new);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_copy_rgb565(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_copy_mono1p(&bb_new);
}

void display_copy_mono4(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_copy_mono4(&bb_new);
}
#endif
