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
        lerp::Lerp,
    },
};
use heapless::Vec;

use crate::ui::{
    component::text::TextStyle,
    constant::{HEIGHT, WIDTH},
    model_tt::{theme, theme::BLACK},
    util::icon_text_center,
};

pub type HomescreenText<'a> = (&'a str, TextStyle, Offset, Option<&'static [u8]>);
pub type HomescreenNotification<'a> = (&'a str, &'static [u8], Color);
type HomescreenTextInfo = (Rect, i16, Color, Option<Rect>);

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

fn homescreen_get_fg_text(
    y_tmp: i16,
    text_info: HomescreenTextInfo,
    text_buffer: &BufferText,
    fg_buffer: &mut LineBuffer4Bpp,
) -> bool {
    if y_tmp >= text_info.0.y0 && y_tmp < text_info.0.y1 {
        let y_pos = y_tmp - text_info.0.y0;
        position_buffer(
            &mut fg_buffer.buffer,
            &text_buffer.buffer[(y_pos * WIDTH / 2) as usize..((y_pos + 1) * WIDTH / 2) as usize],
            4,
            text_info.0.x0,
            text_info.1,
        );
    }

    y_tmp == (text_info.0.y1 - 1)
}

fn homescreen_get_fg_icon(
    y_tmp: i16,
    text_info: HomescreenTextInfo,
    icon_data: &[u8],
    fg_buffer: &mut LineBuffer4Bpp,
) {
    if let Some(icon_area) = text_info.3 {
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
    text: HomescreenText,
    buffer: &mut BufferText,
    icon_buffer: &mut [u8],
) -> HomescreenTextInfo {
    let (text, text_style, text_offset, icon) = text;

    let text_width = display::text_width(text, text_style.text_font.into());
    let font_max_height = display::text_max_height(text_style.text_font.into());
    let font_baseline = display::text_baseline(text_style.text_font.into());
    let text_width_clamped = text_width.clamp(0, screen().width());

    let icon_size = if let Some(icon) = icon {
        let (icon_size, icon_data) = toif_info_ensure(icon, ToifFormat::GrayScaleEH);

        assert!(icon_size.x < HOMESCREEN_MAX_ICON_SIZE);
        assert!(icon_size.y < HOMESCREEN_MAX_ICON_SIZE);
        let mut ctx = UzlibContext::new(icon_data, None);
        unwrap!(ctx.uncompress(icon_buffer), "Decompression failed");

        icon_size
    } else {
        Offset::zero()
    };

    let text_top = screen().y0 + text_offset.y - font_max_height + font_baseline;
    let text_bottom = screen().y0 + text_offset.y + font_baseline;
    let icon_left = screen().center().x - (text_width_clamped + icon_size.x + TEXT_ICON_SPACE) / 2;
    let text_left = icon_left + icon_size.x + TEXT_ICON_SPACE;
    let text_right = screen().center().x + (text_width_clamped + icon_size.x + TEXT_ICON_SPACE) / 2;

    let text_area = Rect::new(
        Point::new(text_left, text_top),
        Point::new(text_right, text_bottom),
    );

    let icon_area = if icon.is_some() {
        Some(Rect::from_top_left_and_size(
            Point::new(icon_left, text_bottom - icon_size.y - font_baseline),
            icon_size,
        ))
    } else {
        None
    };

    display::text_into_buffer(text, text_style.text_font.into(), buffer, 0);

    (text_area, text_width, text_style.text_color, icon_area)
}

fn homscreen_line(
    icon_data: &mut [u8],
    text_buffer: &mut BufferText,
    text_info: HomescreenTextInfo,
    image_data: &mut [u8; (HOMESCREEN_IMAGE_SIZE * 2) as usize],
    y_tmp: i16,
) -> bool {
    let t_buffer = unsafe { get_buffer_4bpp((y_tmp % 2) as u16, true) };
    let mut img_buffer = unsafe { get_buffer_16bpp((y_tmp % 2) as u16, false) };

    for x in 0..HOMESCREEN_IMAGE_SIZE {
        let x0 = (2 * x) as usize;
        let x1 = (2 * x + 1) as usize;
        let hi = image_data[x1];
        let lo = image_data[x0];
        let mut c0 = Color::from_u16((hi as u16) << 8 | lo as u16);

        if y_tmp > HOMESCREEN_DIM_START {
            c0 = Color::lerp(
                c0,
                BLACK,
                ((y_tmp - HOMESCREEN_DIM_START) as f32 / HOMESCREEN_DIM_HIEGHT as f32)
                    * HOMESCREEN_DIM,
            );
        }

        for i in 0..HOMESCREEN_IMAGE_SCALE {
            let idx = (HOMESCREEN_IMAGE_SCALE * x + i) as usize;
            img_buffer.buffer[2 * idx + 1] = c0.hi_byte();
            img_buffer.buffer[2 * idx] = c0.lo_byte();
        }
    }

    let done = homescreen_get_fg_text(y_tmp, text_info, text_buffer, t_buffer);
    homescreen_get_fg_icon(y_tmp, text_info, icon_data, t_buffer);

    dma2d_wait_for_transfer();
    dma2d_setup_4bpp_over_16bpp(text_info.2.into());
    dma2d_start_blend(&t_buffer.buffer, &img_buffer.buffer, WIDTH);

    done
}

fn homescreen_next_text(
    texts: &Vec<Option<HomescreenText>, 4>,
    text_buffer: &mut BufferText,
    icon_data: &mut [u8],
    text_info: HomescreenTextInfo,
    text_idx: usize,
) -> (HomescreenTextInfo, usize) {
    let mut next_text_idx = text_idx;
    let mut next_text_info = text_info;

    if next_text_idx < texts.len() {
        if let Some(txt) = texts[next_text_idx] {
            unsafe { get_text_buffer(0, true) };
            next_text_info = homescreen_position_text(txt, text_buffer, icon_data);
            next_text_idx += 1;
        }
    }

    (next_text_info, next_text_idx)
}

pub fn homescreen(
    data: &[u8],
    texts: Vec<Option<HomescreenText>, 4>,
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
        let width = WIDTH;
        let color = notification.2;
        let icon = None;
        (area, width, color, icon)
    } else {
        next_text_idx += 1;
        homescreen_position_text(unwrap!(texts[0]), text_buffer, &mut icon_data)
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
                for i in &mut dest {
                    *i = 0;
                }
            }

            for i in 0..HOMESCREEN_IMAGE_SCALE {
                let done = homscreen_line(
                    &mut icon_data,
                    text_buffer,
                    text_info,
                    &mut dest,
                    HOMESCREEN_IMAGE_SCALE * y + i,
                );

                if done {
                    if notification.is_some() && next_text_idx == 0 {
                        //finished notification area, let interrupt and draw the text
                        let notification = unwrap!(notification);

                        let style = TextStyle {
                            background_color: notification.2,
                            ..theme::TEXT_BOLD
                        };

                        dma2d_wait_for_transfer();

                        icon_text_center(
                            text_info.0.center(),
                            notification.1,
                            8,
                            notification.0,
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
