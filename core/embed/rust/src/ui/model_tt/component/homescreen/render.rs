#[cfg(feature = "dma2d")]
use crate::trezorhal::{
    buffers::{get_buffer_16bpp, get_buffer_4bpp, get_text_buffer, BufferText, LineBuffer4Bpp},
    dma2d::{dma2d_setup_4bpp_over_16bpp, dma2d_start_blend, dma2d_wait_for_transfer},
};
use crate::{
    trezorhal::{
        buffers::{get_blurring_buffer, get_jpeg_buffer, get_jpeg_work_buffer, BufferJpeg},
        display,
        display::bar_radius_buffer,
    },
    ui::{
        constant::screen,
        display::{position_buffer, set_window, Color},
        geometry::{Offset, Point, Rect},
    },
};

use crate::ui::{
    component::text::TextStyle,
    constant::{HEIGHT, WIDTH},
    display::{
        tjpgd::{BufferInput, BufferOutput, JDEC},
        Icon,
    },
    model_tt::theme,
    util::icon_text_center,
};

#[derive(Clone, Copy)]
pub struct HomescreenText<'a> {
    pub text: &'a str,
    pub style: TextStyle,
    pub offset: Offset,
    pub icon: Option<Icon>,
}

#[derive(Clone, Copy)]
pub struct HomescreenNotification<'a> {
    pub text: &'a str,
    pub icon: Icon,
    pub color: Color,
}

#[derive(Clone, Copy)]
struct HomescreenTextInfo {
    pub text_area: Rect,
    pub text_width: i16,
    pub text_color: Color,
    pub icon_area: Option<Rect>,
}

pub const HOMESCREEN_IMAGE_SIZE: i16 = 240;

const HOMESCREEN_MAX_ICON_SIZE: i16 = 20;
const NOTIFICATION_HEIGHT: i16 = 32;
const NOTIFICATION_BORDER: i16 = 8;
const NOTIFICATION_ICON_SPACE: i16 = 8;
const NOTIFICATION_TEXT_OFFSET: Offset = Offset::new(1, -2);
const TEXT_ICON_SPACE: i16 = 2;

const HOMESCREEN_DIM_HIEGHT: i16 = 30;
const HOMESCREEN_DIM_START: i16 = 195;
const HOMESCREEN_DIM: f32 = 0.85;
const HOMESCREEN_DIM_BORDER: i16 = 20;

const LOCKSCREEN_DIM: f32 = 0.85;
const LOCKSCREEN_DIM_BG: f32 = 0.0;

const BLUR_SIZE: usize = 9;
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
        let size = icon.toif.size();
        assert!(size.x <= HOMESCREEN_MAX_ICON_SIZE);
        assert!(size.y <= HOMESCREEN_MAX_ICON_SIZE);
        icon.toif.uncompress(icon_buffer);
        size
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

#[inline(always)]
fn homescreen_dim_area(x: i16, y: i16) -> bool {
    y >= HOMESCREEN_DIM_START
        && (y > HOMESCREEN_DIM_START + 1
            && y < (HOMESCREEN_DIM_START + HOMESCREEN_DIM_HIEGHT - 1)
            && x > HOMESCREEN_DIM_BORDER
            && x < WIDTH - HOMESCREEN_DIM_BORDER)
        || (y > HOMESCREEN_DIM_START
            && y < (HOMESCREEN_DIM_START + HOMESCREEN_DIM_HIEGHT)
            && x > HOMESCREEN_DIM_BORDER + 1
            && x < WIDTH - (HOMESCREEN_DIM_BORDER + 1))
        || ((HOMESCREEN_DIM_START..=(HOMESCREEN_DIM_START + HOMESCREEN_DIM_HIEGHT)).contains(&y)
            && x > HOMESCREEN_DIM_BORDER + 2
            && x < WIDTH - (HOMESCREEN_DIM_BORDER + 2))
}

fn homescreen_line_blurred(
    icon_data: &[u8],
    text_buffer: &mut BufferText,
    text_info: HomescreenTextInfo,
    blurring: &BlurringContext,
    y: i16,
) -> bool {
    let t_buffer = unsafe { get_buffer_4bpp((y & 0x1) as u16, true) };
    let mut img_buffer = unsafe { get_buffer_16bpp((y & 0x1) as u16, false) };

    for x in 0..HOMESCREEN_IMAGE_SIZE {
        let c = if homescreen_dim_area(x, y) {
            let x = x as usize;

            let coef = (65536_f32 * LOCKSCREEN_DIM) as u32;

            let r = (blurring.totals[RED_IDX][x] as u32 * BLUR_DIV) >> 16;
            let g = (blurring.totals[GREEN_IDX][x] as u32 * BLUR_DIV) >> 16;
            let b = (blurring.totals[BLUE_IDX][x] as u32 * BLUR_DIV) >> 16;

            let r = (((coef * r) >> 8) & 0xF800) as u16;
            let g = (((coef * g) >> 13) & 0x07E0) as u16;
            let b = (((coef * b) >> 19) & 0x001F) as u16;

            r | g | b
        } else {
            let x = x as usize;

            let r = (((blurring.totals[RED_IDX][x] as u32 * BLUR_DIV) >> 8) & 0xF800) as u16;
            let g = (((blurring.totals[GREEN_IDX][x] as u32 * BLUR_DIV) >> 13) & 0x07E0) as u16;
            let b = (((blurring.totals[BLUE_IDX][x] as u32 * BLUR_DIV) >> 19) & 0x001F) as u16;
            r | g | b
        };

        let j = (2 * x) as usize;
        img_buffer.buffer[j + 1] = (c >> 8) as u8;
        img_buffer.buffer[j] = (c & 0xFF) as u8;
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
    data_buffer: &mut BufferJpeg,
    mcu_height: i16,
    y: i16,
) -> bool {
    let t_buffer = unsafe { get_buffer_4bpp((y & 0x1) as u16, true) };
    let mut img_buffer = unsafe { get_buffer_16bpp((y & 0x1) as u16, false) };

    let image_data = get_data(data_buffer, y, mcu_height);

    for x in 0..HOMESCREEN_IMAGE_SIZE {
        let d = image_data[x as usize];

        let c = if homescreen_dim_area(x, y) {
            let coef = (65536_f32 * HOMESCREEN_DIM) as u32;

            let r = (d & 0xF800) >> 8;
            let g = (d & 0x07E0) >> 3;
            let b = (d & 0x001F) << 3;

            let r = (((coef * r as u32) >> 8) & 0xF800) as u16;
            let g = (((coef * g as u32) >> 13) & 0x07E0) as u16;
            let b = (((coef * b as u32) >> 19) & 0x001F) as u16;
            r | g | b
        } else {
            d
        };

        let j = 2 * x as usize;
        img_buffer.buffer[j + 1] = (c >> 8) as u8;
        img_buffer.buffer[j] = (c & 0xFF) as u8;
    }

    let done = homescreen_get_fg_text(y, text_info, text_buffer, t_buffer);
    homescreen_get_fg_icon(y, text_info, icon_data, t_buffer);

    dma2d_wait_for_transfer();
    dma2d_setup_4bpp_over_16bpp(text_info.text_color.into());
    dma2d_start_blend(&t_buffer.buffer, &img_buffer.buffer, WIDTH);

    done
}

fn homescreen_next_text(
    texts: &[HomescreenText],
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
fn update_accs_add(data: &[u16], idx: usize, acc_r: &mut u16, acc_g: &mut u16, acc_b: &mut u16) {
    let d = data[idx];
    let r = (d & 0xF800) >> 8;
    let g = (d & 0x07E0) >> 3;
    let b = (d & 0x001F) << 3;
    *acc_r += r;
    *acc_g += g;
    *acc_b += b;
}

#[inline(always)]
fn update_accs_sub(data: &[u16], idx: usize, acc_r: &mut u16, acc_g: &mut u16, acc_b: &mut u16) {
    let d = data[idx];
    let r = (d & 0xF800) >> 8;
    let g = (d & 0x07E0) >> 3;
    let b = (d & 0x001F) << 3;
    *acc_r -= r;
    *acc_g -= g;
    *acc_b -= b;
}

struct BlurringContext {
    pub lines: &'static mut [[[u16; 240usize]; 3usize]],
    pub totals: [[u16; HOMESCREEN_IMAGE_SIZE as usize]; COLORS],
    line_num: i16,
    add_idx: usize,
    rem_idx: usize,
}

impl BlurringContext {
    pub fn new() -> Self {
        let mem = unsafe { get_blurring_buffer(0, true) };
        Self {
            lines: &mut mem.buffer[0..DECOMP_LINES],
            totals: [[0; HOMESCREEN_IMAGE_SIZE as usize]; COLORS],
            line_num: 0,
            add_idx: 0,
            rem_idx: 0,
        }
    }

    fn clear(&mut self) {
        for (i, total) in self.totals.iter_mut().enumerate() {
            for line in self.lines.iter_mut() {
                line[i].fill(0);
            }
            total.fill(0);
        }
    }

    // computes color averages for one line of image data
    fn compute_line_avgs(&mut self, buffer: &mut BufferJpeg, mcu_height: i16) {
        let mut acc_r = 0;
        let mut acc_g = 0;
        let mut acc_b = 0;
        let data = get_data(buffer, self.line_num, mcu_height);

        for i in -BLUR_RADIUS..=BLUR_RADIUS {
            let ic = i.clamp(0, HOMESCREEN_IMAGE_SIZE as i16 - 1) as usize;
            update_accs_add(data, ic, &mut acc_r, &mut acc_g, &mut acc_b);
        }

        for i in 0..HOMESCREEN_IMAGE_SIZE {
            self.lines[self.add_idx][RED_IDX][i as usize] = acc_r;
            self.lines[self.add_idx][GREEN_IDX][i as usize] = acc_g;
            self.lines[self.add_idx][BLUE_IDX][i as usize] = acc_b;

            // clamping handles left and right edges
            let ic = (i - BLUR_RADIUS).clamp(0, HOMESCREEN_IMAGE_SIZE as i16 - 1) as usize;
            let ic2 = (i + BLUR_SIZE as i16 - BLUR_RADIUS)
                .clamp(0, HOMESCREEN_IMAGE_SIZE as i16 - 1) as usize;
            update_accs_add(data, ic2, &mut acc_r, &mut acc_g, &mut acc_b);
            update_accs_sub(data, ic, &mut acc_r, &mut acc_g, &mut acc_b);
        }
        self.line_num += 1;
    }

    // adds one line of averages to sliding total averages
    fn vertical_avg_add(&mut self) {
        for i in 0..HOMESCREEN_IMAGE_SIZE as usize {
            self.totals[RED_IDX][i] += self.lines[self.add_idx][RED_IDX][i];
            self.totals[GREEN_IDX][i] += self.lines[self.add_idx][GREEN_IDX][i];
            self.totals[BLUE_IDX][i] += self.lines[self.add_idx][BLUE_IDX][i];
        }
    }

    // adds one line and removes one line of averages to/from sliding total averages
    fn vertical_avg(&mut self) {
        for i in 0..HOMESCREEN_IMAGE_SIZE as usize {
            self.totals[RED_IDX][i] +=
                self.lines[self.add_idx][RED_IDX][i] - self.lines[self.rem_idx][RED_IDX][i];
            self.totals[GREEN_IDX][i] +=
                self.lines[self.add_idx][GREEN_IDX][i] - self.lines[self.rem_idx][GREEN_IDX][i];
            self.totals[BLUE_IDX][i] +=
                self.lines[self.add_idx][BLUE_IDX][i] - self.lines[self.rem_idx][BLUE_IDX][i];
        }
    }

    fn inc_add(&mut self) {
        self.add_idx += 1;
        if self.add_idx >= DECOMP_LINES {
            self.add_idx = 0;
        }
    }

    fn inc_rem(&mut self) {
        self.rem_idx += 1;
        if self.rem_idx >= DECOMP_LINES {
            self.rem_idx = 0;
        }
    }

    fn get_line_num(&self) -> i16 {
        self.line_num
    }
}

#[inline(always)]
fn get_data(buffer: &mut BufferJpeg, line_num: i16, mcu_height: i16) -> &mut [u16] {
    let data_start = ((line_num % mcu_height) * WIDTH) as usize;
    let data_end = (((line_num % mcu_height) + 1) * WIDTH) as usize;
    &mut buffer.buffer[data_start..data_end]
}

pub fn homescreen_blurred(data: &[u8], texts: &[HomescreenText]) {
    let mut icon_data = [0_u8; (HOMESCREEN_MAX_ICON_SIZE * HOMESCREEN_MAX_ICON_SIZE / 2) as usize];

    let text_buffer = unsafe { get_text_buffer(0, true) };

    let mut next_text_idx = 1;
    let mut text_info =
        homescreen_position_text(unwrap!(texts.get(0)), text_buffer, &mut icon_data);

    let jpeg_pool = unsafe { get_jpeg_work_buffer(0, true).buffer.as_mut_slice() };
    let jpeg_buffer = unsafe { get_jpeg_buffer(0, true) };
    let mut jpeg_input = BufferInput(data);
    let mut jpeg_output = BufferOutput::new(jpeg_buffer, WIDTH, 16);
    let mut mcu_height = 8;
    let mut jd: Option<JDEC> = JDEC::new(&mut jpeg_input, jpeg_pool).ok();

    if let Some(dec) = &jd {
        mcu_height = dec.mcu_height();
        if !(dec.width() == WIDTH && dec.height() == HEIGHT && mcu_height <= 16) {
            jd = None
        }
    }
    jd.as_mut().map(|dec| dec.decomp(&mut jpeg_output));

    set_window(screen());

    let mut blurring = BlurringContext::new();

    // handling top edge case: preload the edge value N+1 times
    blurring.compute_line_avgs(jpeg_output.buffer(), mcu_height);

    for _ in 0..=BLUR_RADIUS {
        blurring.vertical_avg_add();
    }
    blurring.inc_add();

    // load enough values to be able to compute first line averages
    for _ in 0..BLUR_RADIUS {
        blurring.compute_line_avgs(jpeg_output.buffer(), mcu_height);
        blurring.vertical_avg_add();
        blurring.inc_add();

        if (blurring.get_line_num() % mcu_height) == 0 {
            jd.as_mut().map(|dec| dec.decomp(&mut jpeg_output));
        }
    }

    for y in 0..HEIGHT {
        // several lines have been already decompressed before this loop, adjust for
        // that
        if y < HOMESCREEN_IMAGE_SIZE - (BLUR_RADIUS + 1) {
            blurring.compute_line_avgs(jpeg_output.buffer(), mcu_height);
        }

        let done = homescreen_line_blurred(&icon_data, text_buffer, text_info, &blurring, y);

        if done {
            (text_info, next_text_idx) =
                homescreen_next_text(texts, text_buffer, &mut icon_data, text_info, next_text_idx);
        }

        blurring.vertical_avg();

        // handling bottom edge case: stop incrementing counter, adding the edge value
        // for the rest of image
        // the extra -1 is to indicate that this was the last decompressed line,
        // in the next pass the docompression and compute_line_avgs won't happen
        if y < HOMESCREEN_IMAGE_SIZE - (BLUR_RADIUS + 1) - 1 {
            blurring.inc_add();
        }

        if y == HOMESCREEN_IMAGE_SIZE {
            // reached end of image, clear avgs (display black)
            blurring.clear();
        }

        // only start incrementing remove index when enough lines have been loaded
        if y >= (BLUR_RADIUS) {
            blurring.inc_rem();
        }

        if (blurring.get_line_num() % mcu_height) == 0 && (blurring.get_line_num() < HEIGHT) {
            jd.as_mut().map(|dec| dec.decomp(&mut jpeg_output));
        }
    }
    dma2d_wait_for_transfer();
}

pub fn homescreen(
    data: &[u8],
    texts: &[HomescreenText],
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

    let jpeg_pool = unsafe { get_jpeg_work_buffer(0, true).buffer.as_mut_slice() };
    let jpeg_buffer = unsafe { get_jpeg_buffer(0, true) };
    let mut jpeg_input = BufferInput(data);
    let mut jpeg_output = BufferOutput::new(jpeg_buffer, WIDTH, 16);
    let mut mcu_height = 8;
    let mut jd: Option<JDEC> = JDEC::new(&mut jpeg_input, jpeg_pool).ok();

    if let Some(dec) = &jd {
        mcu_height = dec.mcu_height();
        if !(dec.width() == WIDTH && dec.height() == HEIGHT && mcu_height <= 16) {
            jd = None
        }
    }

    set_window(screen());

    let mcu_height = mcu_height as i16;

    for y in 0..HEIGHT {
        if (y % mcu_height) == 0 {
            jd.as_mut().map(|dec| dec.decomp(&mut jpeg_output));
        }

        let done = homescreen_line(
            &icon_data,
            text_buffer,
            text_info,
            jpeg_output.buffer(),
            mcu_height,
            y,
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

            (text_info, next_text_idx) =
                homescreen_next_text(texts, text_buffer, &mut icon_data, text_info, next_text_idx);
        }
    }
    dma2d_wait_for_transfer();
}
