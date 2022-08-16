use crate::{
    trezorhal::uzlib::UzlibContext,
    ui::{
        constant, display,
        display::{Color, ToifFormat},
        geometry::{Offset, Point, Rect},
    },
};
use core::slice::from_raw_parts;

#[cfg(feature = "dma2d")]
use crate::trezorhal::{
    buffers::{get_buffer_16bpp, get_buffer_4bpp},
    dma2d::{dma2d_setup_4bpp_over_4bpp, dma2d_start_blend, dma2d_wait_for_transfer},
};

use crate::ui::{
    constant::{screen, LOADER_OUTER},
    display::toif_info_ensure,
};

pub const LOADER_MIN: u16 = 0;
pub const LOADER_MAX: u16 = 1000;

const LOADER_SIZE: i32 = (LOADER_OUTER * 2.0) as i32;

const OUTER: f32 = constant::LOADER_OUTER;
const INNER: f32 = constant::LOADER_INNER;
const ICON_MAX_SIZE: i16 = constant::LOADER_ICON_MAX_SIZE;

const IN_INNER_ANTI: i32 = ((INNER - 0.5) * (INNER - 0.5)) as i32;
const INNER_MIN: i32 = ((INNER + 0.5) * (INNER + 0.5)) as i32;
const INNER_MAX: i32 = ((INNER + 1.5) * (INNER + 1.5)) as i32;
const INNER_OUTER_ANTI: i32 = ((INNER + 2.5) * (INNER + 2.5)) as i32;
const OUTER_OUT_ANTI: i32 = ((OUTER - 1.5) * (OUTER - 1.5)) as i32;
const OUTER_MAX: i32 = ((OUTER - 0.5) * (OUTER - 0.5)) as i32;

pub fn loader_uncompress(
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    progress: u16,
    indeterminate: bool,
    icon: Option<(&[u8], Color)>,
) {
    const ICON_MAX_SIZE: i16 = constant::LOADER_ICON_MAX_SIZE;

    if let Some((data, color)) = icon {
        let (toif_size, toif_data) = toif_info_ensure(data, ToifFormat::GrayScaleEH);
        if toif_size.x <= ICON_MAX_SIZE && toif_size.y <= ICON_MAX_SIZE {
            let mut icon_data = [0_u8; ((ICON_MAX_SIZE * ICON_MAX_SIZE) / 2) as usize];
            let mut ctx = UzlibContext::new(toif_data, None);
            unwrap!(ctx.uncompress(&mut icon_data), "Decompression failed");
            let i = Some((icon_data.as_ref(), color, toif_size));
            loader_rust(y_offset, fg_color, bg_color, progress, indeterminate, i);
        } else {
            loader_rust(y_offset, fg_color, bg_color, progress, indeterminate, None);
        }
    } else {
        loader_rust(y_offset, fg_color, bg_color, progress, indeterminate, None);
    }
}

#[no_mangle]
pub extern "C" fn loader_uncompress_r(
    y_offset: cty::int32_t,
    fg_color: cty::uint16_t,
    bg_color: cty::uint16_t,
    icon_color: cty::uint16_t,
    progress: cty::int32_t,
    indeterminate: cty::int32_t,
    icon_data: cty::uintptr_t,
    icon_data_size: cty::uint32_t,
) {
    let fg = Color::from_u16(fg_color);
    let bg = Color::from_u16(bg_color);
    let ic_color = Color::from_u16(icon_color);

    let i = if icon_data != 0 {
        let data_slice = unsafe { from_raw_parts(icon_data as _, icon_data_size as _) };
        Some((data_slice, ic_color))
    } else {
        None
    };

    loader_uncompress(y_offset as _, fg, bg, progress as _, indeterminate != 0, i);
}

#[inline(always)]
fn get_loader_vectors(indeterminate: bool, progress: u16) -> (Point, Point) {
    let (start_progress, end_progress) = if indeterminate {
        const LOADER_INDETERMINATE_WIDTH: u16 = 100;
        (
            progress - LOADER_INDETERMINATE_WIDTH,
            progress + LOADER_INDETERMINATE_WIDTH,
        )
    } else {
        (0, progress)
    };

    let start = ((360 * start_progress as i32) / 1000) % 360;
    let end = ((360 * end_progress as i32) / 1000) % 360;

    let start_vector;
    let end_vector;

    if indeterminate {
        start_vector = display::get_vector(start as _);
        end_vector = display::get_vector(end as _);
    } else if progress >= 1000 {
        start_vector = Point::zero();
        end_vector = Point::zero();
    } else if progress > 500 {
        start_vector = display::get_vector(end as _);
        end_vector = display::get_vector(start as _);
    } else {
        start_vector = display::get_vector(start as _);
        end_vector = display::get_vector(end as _);
    }

    (start_vector, end_vector)
}

#[inline(always)]
fn loader_get_pixel_color_idx(
    show_all: bool,
    inverted: bool,
    end_vector: Point,
    n_start: Point,
    x_c: i16,
    y_c: i16,
    center: Point,
) -> u8 {
    let y_p = -(y_c - center.y);
    let x_p = x_c - center.x;

    let vx = Point::new(x_p, y_p);
    let n_vx = Point::new(-y_p, x_p);

    let d = y_p as i32 * y_p as i32 + x_p as i32 * x_p as i32;

    let included = if inverted {
        !display::is_clockwise_or_equal(n_start, vx)
            || !display::is_clockwise_or_equal_inc(n_vx, end_vector)
    } else {
        display::is_clockwise_or_equal(n_start, vx)
            && display::is_clockwise_or_equal_inc(n_vx, end_vector)
    };

    // The antialiasing calculation below uses simplified distance difference
    // calculation. Optimally, SQRT should be used, but assuming
    // diameter large enough and antialiasing over distance
    // r_outer-r_inner = 1, the difference between simplified:
    // (d^2-r_inner^2)/(r_outer^2-r_inner^2) and precise: (sqrt(d^2)
    // - r_inner)/(r_outer-r_inner) is negligible
    if show_all || included {
        //active part
        if d <= IN_INNER_ANTI {
            0
        } else if d <= INNER_MIN {
            ((15 * (d - IN_INNER_ANTI)) / (INNER_MIN - IN_INNER_ANTI)) as u8
        } else if d <= OUTER_OUT_ANTI {
            15
        } else if d <= OUTER_MAX {
            (15 - ((15 * (d - OUTER_OUT_ANTI)) / (OUTER_MAX - OUTER_OUT_ANTI))) as u8
        } else {
            0
        }
    } else {
        //inactive part
        if d <= IN_INNER_ANTI {
            0
        } else if d <= INNER_MIN {
            ((15 * (d - IN_INNER_ANTI)) / (INNER_MIN - IN_INNER_ANTI)) as u8
        } else if d <= INNER_MAX {
            15
        } else if d <= INNER_OUTER_ANTI {
            (15 - ((10 * (d - INNER_MAX)) / (INNER_OUTER_ANTI - INNER_MAX))) as u8
        } else if d <= OUTER_OUT_ANTI {
            5
        } else if d <= OUTER_MAX {
            5 - ((5 * (d - OUTER_OUT_ANTI)) / (OUTER_MAX - OUTER_OUT_ANTI)) as u8
        } else {
            0
        }
    }
}

#[cfg(not(feature = "dma2d"))]
pub fn loader_rust(
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    progress: u16,
    indeterminate: bool,
    icon: Option<(&[u8], Color, Offset)>,
) {
    let center = screen().center() + Offset::new(0, y_offset);
    let r = Rect::from_center_and_size(center, Offset::uniform(LOADER_OUTER as i16 * 2));
    let clamped = r.clamp(constant::screen());
    display::set_window(clamped);

    let center = r.center();

    let colortable = display::get_color_table(fg_color, bg_color);
    let mut icon_colortable = colortable;

    let mut use_icon = false;
    let mut icon_area = Rect::zero();
    let mut icon_area_clamped = Rect::zero();
    let mut icon_width = 0;
    let mut icon_data = [].as_ref();

    if let Some((data, color, size)) = icon {
        if size.x <= ICON_MAX_SIZE && size.y <= ICON_MAX_SIZE {
            icon_width = size.x;
            icon_area = Rect::from_center_and_size(center, size);
            icon_area_clamped = icon_area.clamp(constant::screen());
            icon_data = data;
            use_icon = true;
            icon_colortable = display::get_color_table(color, bg_color);
        }
    }

    let show_all = !indeterminate && progress >= 1000;
    let inverted = !indeterminate && progress > 500;
    let (start_vector, end_vector) = get_loader_vectors(indeterminate, progress);

    let n_start = Point::new(-start_vector.y, start_vector.x);

    for y_c in r.y0..r.y1 {
        for x_c in r.x0..r.x1 {
            let p = Point::new(x_c, y_c);
            let mut icon_pixel = false;

            let mut underlying_color = bg_color;

            if use_icon && icon_area_clamped.contains(p) {
                let x = x_c - center.x;
                let y = y_c - center.y;
                if (x as i32 * x as i32 + y as i32 * y as i32) <= IN_INNER_ANTI {
                    let x_i = x_c - icon_area.x0;
                    let y_i = y_c - icon_area.y0;

                    let data = icon_data[(((x_i & 0xFE) + (y_i * icon_width)) / 2) as usize];
                    if (x_i & 0x01) == 0 {
                        underlying_color = icon_colortable[(data & 0xF) as usize];
                    } else {
                        underlying_color = icon_colortable[(data >> 4) as usize];
                    }
                    icon_pixel = true;
                }
            }

            if clamped.contains(p) && !icon_pixel {
                let pix_c_idx = loader_get_pixel_color_idx(
                    show_all, inverted, end_vector, n_start, x_c, y_c, center,
                );
                underlying_color = colortable[pix_c_idx as usize];
            }

            display::pixeldata(underlying_color);
        }
    }

    display::pixeldata_dirty();
}

#[cfg(feature = "dma2d")]
pub fn loader_rust(
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    progress: u16,
    indeterminate: bool,
    icon: Option<(&[u8], Color, Offset)>,
) {
    let center = screen().center() + Offset::new(0, y_offset);
    let r = Rect::from_center_and_size(center, Offset::uniform(LOADER_OUTER as i16 * 2));
    let clamped = r.clamp(constant::screen());
    display::set_window(clamped);

    let center = r.center();

    let mut use_icon = false;
    let mut icon_area = Rect::zero();
    let mut icon_area_clamped = Rect::zero();
    let mut icon_width = 0;
    let mut icon_offset = 0;
    let mut icon_color = Color::from_u16(0);
    let mut icon_data = [].as_ref();

    if let Some((data, color, size)) = icon {
        if size.x <= ICON_MAX_SIZE && size.y <= ICON_MAX_SIZE {
            icon_width = size.x;
            icon_area = Rect::from_center_and_size(center, size);
            icon_area_clamped = icon_area.clamp(constant::screen());
            icon_offset = (icon_area_clamped.x0 - r.x0) / 2;
            icon_color = color;
            icon_data = data;
            use_icon = true;
        }
    }

    let show_all = !indeterminate && progress >= 1000;
    let inverted = !indeterminate && progress > 500;
    let (start_vector, end_vector) = get_loader_vectors(indeterminate, progress);

    let n_start = Point::new(-start_vector.y, start_vector.x);

    let b1 = unsafe { get_buffer_16bpp(0, false) };
    let b2 = unsafe { get_buffer_16bpp(1, false) };
    let ib1 = unsafe { get_buffer_4bpp(0, true) };
    let ib2 = unsafe { get_buffer_4bpp(1, true) };
    let empty_line = unsafe { get_buffer_4bpp(2, true) };

    dma2d_setup_4bpp_over_4bpp(fg_color.into(), bg_color.into(), icon_color.into());

    for y_c in r.y0..r.y1 {
        let mut icon_buffer = &mut *empty_line;
        let icon_buffer_used;
        let loader_buffer;

        if y_c % 2 == 0 {
            icon_buffer_used = &mut *ib1;
            loader_buffer = &mut *b1;
        } else {
            icon_buffer_used = &mut *ib2;
            loader_buffer = &mut *b2;
        }

        if use_icon && y_c >= icon_area_clamped.y0 && y_c < icon_area_clamped.y1 {
            let y_i = y_c - icon_area.y0;

            // Optimally, we should cut corners of the icon if it happens to be large enough
            // to invade loader area. but this would require calculation of circle chord
            // length (since we need to limit data copied to the buffer),
            // which requires expensive SQRT. Therefore, when using this method of loader
            // drawing, special care needs to be taken to ensure that the icons
            // have transparent corners.

            icon_buffer_used.buffer[icon_offset as usize..(icon_offset + icon_width / 2) as usize]
                .copy_from_slice(
                    &icon_data[(y_i * (icon_width / 2)) as usize
                        ..((y_i + 1) * (icon_width / 2)) as usize],
                );
            icon_buffer = icon_buffer_used;
        }

        let mut pix_c_idx_prev: u8 = 0;

        for x_c in r.x0..r.x1 {
            let p = Point::new(x_c, y_c);

            let pix_c_idx = if clamped.contains(p) {
                loader_get_pixel_color_idx(
                    show_all, inverted, end_vector, n_start, x_c, y_c, center,
                )
            } else {
                0
            };

            let x = x_c - r.x0;
            if x % 2 == 0 {
                pix_c_idx_prev = pix_c_idx;
            } else {
                loader_buffer.buffer[(x >> 1) as usize] = pix_c_idx_prev | pix_c_idx << 4;
            }
        }

        dma2d_wait_for_transfer();
        dma2d_start_blend(&icon_buffer.buffer, &loader_buffer.buffer, clamped.width());
    }

    dma2d_wait_for_transfer();
}

pub fn loader(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(&[u8], Color)>,
) {
    loader_uncompress(y_offset, fg_color, bg_color, progress, false, icon);
}

pub fn loader_indeterminate(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(&[u8], Color)>,
) {
    loader_uncompress(y_offset, fg_color, bg_color, progress, true, icon);
}
