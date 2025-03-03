#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <gfx/gfx_bitblt.h>
#include <io/display.h>

#ifdef KERNEL_MODE
void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_copy_rgb565(&bb_new);
}

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_fill(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 1) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_copy_mono1p(&bb_new);
}

#endif
