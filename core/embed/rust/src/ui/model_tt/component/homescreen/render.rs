#[cfg(feature = "dma2d")]
use crate::trezorhal::{
    buffers::{get_buffer_16bpp, get_buffer_4bpp, get_text_buffer, BufferText, LineBuffer4Bpp},
    dma2d::{dma2d_setup_4bpp_over_16bpp, dma2d_start_blend, dma2d_wait_for_transfer},
};
use crate::{
    trezorhal::{
        display,
        display::{bar_radius_buffer, ToifFormat},
        uzlib::{UzlibContext, UZLIB_WINDOW_SIZE},
    },
    ui::{
        constant::screen,
        display::{position_buffer, set_window, toif_info, toif_info_ensure, Color},
        geometry::{Offset, Point, Rect},
    },
};
use heapless::Vec;

use crate::ui::{
    component::text::TextStyle,
    constant::{HEIGHT, WIDTH},
    model_tt::theme,
    util::icon_text_center,
};

#[derive(Clone, Copy)]
pub struct HomescreenText<'a> {
    pub text: &'a str,
    pub style: TextStyle,
    pub offset: Offset,
    pub icon: Option<&'static [u8]>,
}

#[derive(Clone, Copy)]
pub struct HomescreenNotification<'a> {
    pub text: &'a str,
    pub icon: &'static [u8],
    pub color: Color,
}

#[derive(Clone, Copy)]
struct HomescreenTextInfo {
    pub text_area: Rect,
    pub text_width: i16,
    pub text_color: Color,
    pub icon_area: Option<Rect>,
}

const HOMESCREEN_MAX_ICON_SIZE: i16 = 20;
const HOMESCREEN_IMAGE_SCALE: i16 = 2;
const HOMESCREEN_IMAGE_SIZE: i16 = WIDTH / HOMESCREEN_IMAGE_SCALE;
const NOTIFICATION_HEIGHT: i16 = 32;
const NOTIFICATION_BORDER: i16 = 8;
const NOTIFICATION_ICON_SPACE: i16 = 8;
const NOTIFICATION_TEXT_OFFSET: Offset = Offset::new(1, -2);
const TEXT_ICON_SPACE: i16 = 2;

const HOMESCREEN_DIM_HIEGHT: i16 = 95;
const HOMESCREEN_DIM_START: i16 = HEIGHT - HOMESCREEN_DIM_HIEGHT;
const HOMESCREEN_DIM: f32 = 0.63;

const LOCKSCREEN_DIM_HIEGHT: i16 = 95;
const LOCKSCREEN_DIM_START: i16 = HEIGHT - LOCKSCREEN_DIM_HIEGHT;
const LOCKSCREEN_DIM: f32 = 0.63;
const LOCKSCREEN_DIM_BG: f32 = 0.33;

const BLUR_SIZE: usize = 7;
const BLUR_DIV: u32 =
    ((65536_f32 * (1_f32 - LOCKSCREEN_DIM_BG)) as u32) / ((BLUR_SIZE * BLUR_SIZE) as u32);
const DECOMP_LINES: usize = BLUR_SIZE + 1;
const BLUR_RADIUS: i16 = (BLUR_SIZE / 2) as i16;

const COLORS: usize = 3;
const RED_IDX: usize = 0;
const GREEN_IDX: usize = 1;
const BLUE_IDX: usize = 2;

fn homescreen_get_fg_text(
    y_tmp: i16,
    text_info: HomescreenTextInfo,
    text_buffer: &BufferText,
    fg_buffer: &mut LineBuffer4Bpp,
) -> bool {
    if y_tmp >= text_info.text_area.y0 && y_tmp < text_info.text_area.y1 {
        let y_pos = y_tmp - text_info.text_area.y0;
        position_buffer(
            &mut fg_buffer.buffer,
            &text_buffer.buffer[(y_pos * WIDTH / 2) as usize..((y_pos + 1) * WIDTH / 2) as usize],
            4,
            text_info.text_area.x0,
            text_info.text_width,
        );
    }

    y_tmp == (text_info.text_area.y1 - 1)
}

fn homescreen_get_fg_icon(
    y_tmp: i16,
    text_info: HomescreenTextInfo,
    icon_data: &[u8],
    fg_buffer: &mut LineBuffer4Bpp,
) {
    if let Some(icon_area) = text_info.icon_area {
        let icon_size = icon_area.size();
        if y_tmp >= icon_area.y0 && y_tmp < icon_area.y1 {
            let y_pos = y_tmp - icon_area.y0;
            position_buffer(
                &mut fg_buffer.buffer,
                &icon_data
                    [(y_pos * icon_size.x / 2) as usize..((y_pos + 1) * icon_size.x / 2) as usize],
                4,
                icon_area.x0,
                icon_size.x,
            );
        }
    }
}

fn homescreen_position_text(
    text: &HomescreenText,
    buffer: &mut BufferText,
    icon_buffer: &mut [u8],
) -> HomescreenTextInfo {
    let text_width = display::text_width(text.text, text.style.text_font.into());
    let font_max_height = display::text_max_height(text.style.text_font.into());
    let font_baseline = display::text_baseline(text.style.text_font.into());
    let text_width_clamped = text_width.clamp(0, screen().width());

    let icon_size = if let Some(icon) = text.icon {
        let (icon_size, icon_data) = toif_info_ensure(icon, ToifFormat::GrayScaleEH);
        assert!(icon_size.x <= HOMESCREEN_MAX_ICON_SIZE);
        assert!(icon_size.y <= HOMESCREEN_MAX_ICON_SIZE);
        let mut ctx = UzlibContext::new(icon_data, None);
        unwrap!(ctx.uncompress(icon_buffer), "Decompression failed");
        icon_size
    } else {
        Offset::zero()
    };

    let text_top = screen().y0 + text.offset.y - font_max_height + font_baseline;
    let text_bottom = screen().y0 + text.offset.y + font_baseline;
    let icon_left = screen().center().x - (text_width_clamped + icon_size.x + TEXT_ICON_SPACE) / 2;
    let text_left = icon_left + icon_size.x + TEXT_ICON_SPACE;
    let text_right = screen().center().x + (text_width_clamped + icon_size.x + TEXT_ICON_SPACE) / 2;

    let text_area = Rect::new(
        Point::new(text_left, text_top),
        Point::new(text_right, text_bottom),
    );

    let icon_area = if text.icon.is_some() {
        Some(Rect::from_top_left_and_size(
            Point::new(icon_left, text_bottom - icon_size.y - font_baseline),
            icon_size,
        ))
    } else {
        None
    };

    display::text_into_buffer(text.text, text.style.text_font.into(), buffer, 0);

    HomescreenTextInfo {
        text_area,
        text_width,
        text_color: text.style.text_color,
        icon_area,
    }
}

fn homescreen_line_blurred(
    icon_data: &[u8],
    text_buffer: &mut BufferText,
    text_info: HomescreenTextInfo,
    totals: &[[u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS],
    y: i16,
) -> bool {
    let t_buffer = unsafe { get_buffer_4bpp((y & 0x1) as u16, true) };
    let mut img_buffer = unsafe { get_buffer_16bpp((y & 0x1) as u16, false) };

    for x in 0..HOMESCREEN_IMAGE_SIZE as usize {
        let c0 = if y > LOCKSCREEN_DIM_START {
            let coef = 65536
                - (((y - LOCKSCREEN_DIM_START) as u32)
                    * ((65536_f32 * LOCKSCREEN_DIM) as u32 / LOCKSCREEN_DIM_HIEGHT as u32));

            let r = (totals[RED_IDX][x] as u32 * BLUR_DIV) >> 16;
            let g = (totals[GREEN_IDX][x] as u32 * BLUR_DIV) >> 16;
            let b = (totals[BLUE_IDX][x] as u32 * BLUR_DIV) >> 16;

            let r = (((coef * r) >> 8) & 0xF800) as u16;
            let g = (((coef * g) >> 13) & 0x07E0) as u16;
            let b = (((coef * b) >> 19) & 0x001F) as u16;

            r | g | b
        } else {
            let r = (((totals[RED_IDX][x] as u32 * BLUR_DIV) >> 8) & 0xF800) as u16;
            let g = (((totals[GREEN_IDX][x] as u32 * BLUR_DIV) >> 13) & 0x07E0) as u16;
            let b = (((totals[BLUE_IDX][x] as u32 * BLUR_DIV) >> 19) & 0x001F) as u16;
            r | g | b
        };

        for i in 0..HOMESCREEN_IMAGE_SCALE as usize {
            let j = 2 * (HOMESCREEN_IMAGE_SCALE as usize * x + i) as usize;
            img_buffer.buffer[j + 1] = (c0 >> 8) as u8;
            img_buffer.buffer[j] = (c0 & 0xFF) as u8;
        }
    }

    let done = homescreen_get_fg_text(y, text_info, text_buffer, t_buffer);
    homescreen_get_fg_icon(y, text_info, icon_data, t_buffer);

    dma2d_wait_for_transfer();
    dma2d_setup_4bpp_over_16bpp(text_info.text_color.into());
    dma2d_start_blend(&t_buffer.buffer, &img_buffer.buffer, WIDTH);

    done
}

fn homescreen_line(
    icon_data: &[u8],
    text_buffer: &mut BufferText,
    text_info: HomescreenTextInfo,
    image_data: &[u8; (HOMESCREEN_IMAGE_SIZE * 2) as usize],
    y: i16,
) -> bool {
    let t_buffer = unsafe { get_buffer_4bpp((y & 0x1) as u16, true) };
    let mut img_buffer = unsafe { get_buffer_16bpp((y & 0x1) as u16, false) };

    for x in 0..HOMESCREEN_IMAGE_SIZE {
        let x0 = (2 * x) as usize;
        let x1 = x0 + 1;
        let hi = image_data[x1];
        let lo = image_data[x0];

        let c = if y > HOMESCREEN_DIM_START {
            let coef = 65536
                - (((y - HOMESCREEN_DIM_START) as u32)
                    * ((65536_f32 * HOMESCREEN_DIM) as u32 / HOMESCREEN_DIM_HIEGHT as u32));

            let r = hi & 0xF8;
            let g = ((hi & 0x07) << 5) | ((lo & 0xE0) >> 3);
            let b = (lo & 0x1F) << 3;

            let r = (((coef * r as u32) >> 8) & 0xF800) as u16;
            let g = (((coef * g as u32) >> 13) & 0x07E0) as u16;
            let b = (((coef * b as u32) >> 19) & 0x001F) as u16;
            r | g | b
        } else {
            (hi as u16) << 8 | lo as u16
        };

        for i in 0..HOMESCREEN_IMAGE_SCALE {
            let j = 2 * (HOMESCREEN_IMAGE_SCALE * x + i) as usize;
            img_buffer.buffer[j + 1] = (c >> 8) as u8;
            img_buffer.buffer[j] = (c & 0xFF) as u8;
        }
    }

    let done = homescreen_get_fg_text(y, text_info, text_buffer, t_buffer);
    homescreen_get_fg_icon(y, text_info, icon_data, t_buffer);

    dma2d_wait_for_transfer();
    dma2d_setup_4bpp_over_16bpp(text_info.text_color.into());
    dma2d_start_blend(&t_buffer.buffer, &img_buffer.buffer, WIDTH);

    done
}

fn homescreen_next_text(
    texts: &Vec<HomescreenText, 4>,
    text_buffer: &mut BufferText,
    icon_data: &mut [u8],
    text_info: HomescreenTextInfo,
    text_idx: usize,
) -> (HomescreenTextInfo, usize) {
    let mut next_text_idx = text_idx;
    let mut next_text_info = text_info;

    if next_text_idx < texts.len() {
        if let Some(txt) = texts.get(next_text_idx) {
            text_buffer.buffer.fill(0);
            next_text_info = homescreen_position_text(txt, text_buffer, icon_data);
            next_text_idx += 1;
        }
    }

    (next_text_info, next_text_idx)
}

#[inline(always)]
fn update_accs_add(
    data: &[u8; (HOMESCREEN_IMAGE_SIZE * 2) as usize],
    idx: usize,
    acc_r: &mut u16,
    acc_g: &mut u16,
    acc_b: &mut u16,
) {
    let lo = data[2_usize * idx];
    let hi = data[2_usize * idx + 1];
    let r = hi & 0xF8;
    let g = ((hi & 0x07) << 5) | ((lo & 0xE0) >> 3);
    let b = (lo & 0x1F) << 3;
    *acc_r += r as u16;
    *acc_g += g as u16;
    *acc_b += b as u16;
}

#[inline(always)]
fn update_accs_sub(
    data: &[u8; (HOMESCREEN_IMAGE_SIZE * 2) as usize],
    idx: usize,
    acc_r: &mut u16,
    acc_g: &mut u16,
    acc_b: &mut u16,
) {
    let lo = data[2_usize * idx];
    let hi = data[2_usize * idx + 1];
    let r = hi & 0xF8;
    let g = ((hi & 0x07) << 5) | ((lo & 0xE0) >> 3);
    let b = (lo & 0x1F) << 3;
    *acc_r -= r as u16;
    *acc_g -= g as u16;
    *acc_b -= b as u16;
}

// computes color averages for one line of image data
fn compute_line_avgs(
    data: &[u8; (HOMESCREEN_IMAGE_SIZE * 2) as usize],
    avg_dest: &mut [[u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS],
) {
    let mut acc_r = 0;
    let mut acc_g = 0;
    let mut acc_b = 0;
    for i in -BLUR_RADIUS..=BLUR_RADIUS {
        let ic = i.clamp(0, HOMESCREEN_IMAGE_SIZE as i16 - 1) as usize;
        update_accs_add(data, ic, &mut acc_r, &mut acc_g, &mut acc_b);
    }

    for i in 0..HOMESCREEN_IMAGE_SIZE {
        avg_dest[RED_IDX][i as usize] = acc_r;
        avg_dest[GREEN_IDX][i as usize] = acc_g;
        avg_dest[BLUE_IDX][i as usize] = acc_b;

        // clamping handles left and right edges
        let ic = (i - BLUR_RADIUS).clamp(0, HOMESCREEN_IMAGE_SIZE as i16 - 1) as usize;
        let ic2 = (i + BLUR_SIZE as i16 - BLUR_RADIUS).clamp(0, HOMESCREEN_IMAGE_SIZE as i16 - 1)
            as usize;
        update_accs_add(data, ic2, &mut acc_r, &mut acc_g, &mut acc_b);
        update_accs_sub(data, ic, &mut acc_r, &mut acc_g, &mut acc_b);
    }
}

// adds one line of averages to sliding total averages
fn vertical_avg_add(
    totals: &mut [[u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS],
    lines: &[[u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS],
) {
    for i in 0..HOMESCREEN_IMAGE_SIZE as usize {
        totals[RED_IDX][i] += lines[RED_IDX][i];
        totals[GREEN_IDX][i] += lines[GREEN_IDX][i];
        totals[BLUE_IDX][i] += lines[BLUE_IDX][i];
    }
}

// adds one line and removes one line of averages to/from sliding total averages
fn vertical_avg(
    totals: &mut [[u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS],
    lines: &[[[u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS]; DECOMP_LINES],
    add_idx: usize,
    rem_idx: usize,
) {
    for i in 0..HOMESCREEN_IMAGE_SIZE as usize {
        totals[RED_IDX][i] += lines[add_idx][RED_IDX][i] - lines[rem_idx][RED_IDX][i];
        totals[GREEN_IDX][i] += lines[add_idx][GREEN_IDX][i] - lines[rem_idx][GREEN_IDX][i];
        totals[BLUE_IDX][i] += lines[add_idx][BLUE_IDX][i] - lines[rem_idx][BLUE_IDX][i];
    }
}

pub fn homescreen_blurred(data: &[u8], texts: Vec<HomescreenText, 4>) {
    let mut icon_data = [0_u8; (HOMESCREEN_MAX_ICON_SIZE * HOMESCREEN_MAX_ICON_SIZE / 2) as usize];

    let text_buffer = unsafe { get_text_buffer(0, true) };

    let mut next_text_idx = 1;
    let mut text_info =
        homescreen_position_text(unwrap!(texts.get(0)), text_buffer, &mut icon_data);

    let toif = toif_info(data);

    if let Some((size, format)) = toif {
        set_window(screen());

        let mut dest = [0_u8; (HOMESCREEN_IMAGE_SIZE * 2) as usize];
        let mut avgs = [[[0_u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS]; DECOMP_LINES];
        let mut avgs_totals = [[0_u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS];

        let mut dest_idx = 0;
        let mut rem_idx = 0;
        let mut window = [0; UZLIB_WINDOW_SIZE];
        let mut ctx = UzlibContext::new(&data[12..], Some(&mut window));

        ctx.uncompress(&mut dest).unwrap();

        // handling top edge case: preload the edge value N+1 times
        compute_line_avgs(&dest, &mut avgs[dest_idx]);
        for _ in 0..=BLUR_RADIUS {
            vertical_avg_add(&mut avgs_totals, &avgs[dest_idx]);
        }
        dest_idx += 1;

        // load enough values to be able to compute first line averages
        for _ in 0..BLUR_RADIUS {
            ctx.uncompress(&mut dest).unwrap();
            compute_line_avgs(&dest, &mut avgs[dest_idx]);
            vertical_avg_add(&mut avgs_totals, &avgs[dest_idx]);
            dest_idx += 1;
        }

        for y in 0..HOMESCREEN_IMAGE_SIZE {
            let clear_bg = if size.x == HOMESCREEN_IMAGE_SIZE
                && size.y == HOMESCREEN_IMAGE_SIZE
                && format == ToifFormat::FullColorLE
            {
                // several lines have been already decompressed before this loop, adjust for
                // that
                if y < HOMESCREEN_IMAGE_SIZE - (BLUR_RADIUS + 1) {
                    ctx.uncompress(&mut dest).unwrap_or(true)
                } else {
                    false
                }
            } else {
                true
            };

            if clear_bg {
                dest.fill(0);
            }

            for i in 0..HOMESCREEN_IMAGE_SCALE {
                let done = homescreen_line_blurred(
                    &icon_data,
                    text_buffer,
                    text_info,
                    &avgs_totals,
                    HOMESCREEN_IMAGE_SCALE * y + i,
                );

                if done {
                    (text_info, next_text_idx) = homescreen_next_text(
                        &texts,
                        text_buffer,
                        &mut icon_data,
                        text_info,
                        next_text_idx,
                    );
                }
            }

            if y < HOMESCREEN_IMAGE_SIZE - (BLUR_RADIUS + 1) as i16 {
                compute_line_avgs(&dest, &mut avgs[dest_idx]);
            }

            vertical_avg(&mut avgs_totals, &avgs, dest_idx, rem_idx);

            // handling bottom edge case: stop incrementing counter, adding the edge value
            // for the rest of image
            if y < HOMESCREEN_IMAGE_SIZE - (BLUR_RADIUS + 1) as i16 {
                dest_idx += 1;
                if dest_idx >= DECOMP_LINES {
                    dest_idx = 0;
                }
            }

            // only start incrementing remove index when enough lines have been loaded
            if y >= (BLUR_RADIUS) as i16 {
                rem_idx += 1;
                if rem_idx >= DECOMP_LINES {
                    rem_idx = 0;
                }
            }
        }
    }
    dma2d_wait_for_transfer();
}

pub fn homescreen(
    data: &[u8],
    texts: Vec<HomescreenText, 4>,
    notification: Option<HomescreenNotification>,
    notification_only: bool,
) {
    let mut icon_data = [0_u8; (HOMESCREEN_MAX_ICON_SIZE * HOMESCREEN_MAX_ICON_SIZE / 2) as usize];

    let text_buffer = unsafe { get_text_buffer(0, true) };

    let mut next_text_idx = 0;
    let mut text_info = if let Some(notification) = notification {
        bar_radius_buffer(
            NOTIFICATION_BORDER,
            0,
            WIDTH - NOTIFICATION_BORDER * 2,
            NOTIFICATION_HEIGHT,
            2,
            text_buffer,
        );
        let area = Rect::new(
            Point::new(0, NOTIFICATION_BORDER),
            Point::new(WIDTH, NOTIFICATION_HEIGHT + NOTIFICATION_BORDER),
        );
        HomescreenTextInfo {
            text_area: area,
            text_width: WIDTH,
            text_color: notification.color,
            icon_area: None,
        }
    } else {
        next_text_idx += 1;
        homescreen_position_text(unwrap!(texts.get(0)), text_buffer, &mut icon_data)
    };

    let toif = toif_info(data);

    if let Some((size, format)) = toif {
        set_window(screen());

        let mut dest = [0_u8; (HOMESCREEN_IMAGE_SIZE * 2) as usize];
        let mut window = [0; UZLIB_WINDOW_SIZE];
        let mut ctx = UzlibContext::new(&data[12..], Some(&mut window));

        for y in 0..(HEIGHT / HOMESCREEN_IMAGE_SCALE) {
            let clear_bg = if size.x == HOMESCREEN_IMAGE_SIZE
                && size.y == HOMESCREEN_IMAGE_SIZE
                && format == ToifFormat::FullColorLE
            {
                ctx.uncompress(&mut dest).unwrap_or(true)
            } else {
                true
            };

            if clear_bg {
                dest.fill(0);
            }

            for i in 0..HOMESCREEN_IMAGE_SCALE {
                let done = homescreen_line(
                    &icon_data,
                    text_buffer,
                    text_info,
                    &dest,
                    HOMESCREEN_IMAGE_SCALE * y + i,
                );

                if done {
                    if notification.is_some() && next_text_idx == 0 {
                        //finished notification area, let interrupt and draw the text
                        let notification = unwrap!(notification);

                        let style = TextStyle {
                            background_color: notification.color,
                            ..theme::TEXT_BOLD
                        };

                        dma2d_wait_for_transfer();

                        icon_text_center(
                            text_info.text_area.center(),
                            notification.icon,
                            8,
                            notification.text,
                            style,
                            Offset::new(1, -2),
                        );
                        set_window(
                            screen()
                                .split_top(NOTIFICATION_HEIGHT + NOTIFICATION_BORDER)
                                .1,
                        );
                    }

                    if notification_only && next_text_idx == 0 {
                        dma2d_wait_for_transfer();
                        return;
                    }

                    (text_info, next_text_idx) = homescreen_next_text(
                        &texts,
                        text_buffer,
                        &mut icon_data,
                        text_info,
                        next_text_idx,
                    );
                }
            }
        }
    }
    dma2d_wait_for_transfer();
}
