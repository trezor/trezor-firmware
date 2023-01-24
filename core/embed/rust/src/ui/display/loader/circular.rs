use crate::ui::{
    constant,
    constant::{screen, LOADER_INNER, LOADER_OUTER},
    display,
    display::{toif::Icon, Color},
    geometry::{Offset, Point, Rect},
};

#[cfg(feature = "dma2d")]
use crate::trezorhal::{
    buffers,
    dma2d::{dma2d_setup_4bpp_over_4bpp, dma2d_start_blend, dma2d_wait_for_transfer},
};

const ICON_MAX_SIZE: i16 = constant::LOADER_ICON_MAX_SIZE;

#[derive(Clone, Copy)]
pub struct LoaderDimensions {
    in_inner_anti: i32,
    inner_min: i32,
    inner_max: i32,
    inner_outer_anti: i32,
    outer_out_anti: i32,
    outer_max: i32,
}

impl LoaderDimensions {
    pub fn new(outer: i16, inner: i16) -> Self {
        let outer: f32 = outer.into();
        let inner: f32 = inner.into();
        Self {
            in_inner_anti: ((inner - 0.5) * (inner - 0.5)) as i32,
            inner_min: ((inner + 0.5) * (inner + 0.5)) as i32,
            inner_max: ((inner + 1.5) * (inner + 1.5)) as i32,
            inner_outer_anti: ((inner + 2.5) * (inner + 2.5)) as i32,
            outer_out_anti: ((outer - 1.5) * (outer - 1.5)) as i32,
            outer_max: ((outer - 0.5) * (outer - 0.5)) as i32,
        }
    }
}

pub fn loader_circular_uncompress(
    dim: LoaderDimensions,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    progress: u16,
    indeterminate: bool,
    icon: Option<(Icon, Color)>,
) {
    if let Some((icon, color)) = icon {
        let toif_size = icon.toif.size();
        if toif_size.x <= ICON_MAX_SIZE && toif_size.y <= ICON_MAX_SIZE {
            let mut icon_data = [0_u8; ((ICON_MAX_SIZE * ICON_MAX_SIZE) / 2) as usize];
            icon.toif.uncompress(&mut icon_data);
            let i = Some((icon_data.as_ref(), color, toif_size));
            loader_rust(
                dim,
                y_offset,
                fg_color,
                bg_color,
                progress,
                indeterminate,
                i,
            );
        } else {
            loader_rust(
                dim,
                y_offset,
                fg_color,
                bg_color,
                progress,
                indeterminate,
                None,
            );
        }
    } else {
        loader_rust(
            dim,
            y_offset,
            fg_color,
            bg_color,
            progress,
            indeterminate,
            None,
        );
    }
}

pub fn loader_circular(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    loader_circular_uncompress(
        LoaderDimensions::new(LOADER_OUTER, LOADER_INNER),
        y_offset,
        fg_color,
        bg_color,
        progress,
        false,
        icon,
    );
}

pub fn loader_circular_indeterminate(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    loader_circular_uncompress(
        LoaderDimensions::new(LOADER_OUTER, LOADER_INNER),
        y_offset,
        fg_color,
        bg_color,
        progress,
        true,
        icon,
    );
}

#[inline(always)]
fn get_loader_vectors(indeterminate: bool, progress: u16) -> (Point, Point) {
    let (start_progress, end_progress) = if indeterminate {
        const LOADER_INDETERMINATE_WIDTH: u16 = 100;
        (
            (progress + 1000 - LOADER_INDETERMINATE_WIDTH) % 1000,
            (progress + LOADER_INDETERMINATE_WIDTH) % 1000,
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
    c: Point,
    center: Point,
    dim: LoaderDimensions,
) -> u8 {
    let y_p = -(c.y - center.y);
    let x_p = c.x - center.x;

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
        if d <= dim.in_inner_anti {
            0
        } else if d <= dim.inner_min {
            ((15 * (d - dim.in_inner_anti)) / (dim.inner_min - dim.in_inner_anti)) as u8
        } else if d <= dim.outer_out_anti {
            15
        } else if d <= dim.outer_max {
            (15 - ((15 * (d - dim.outer_out_anti)) / (dim.outer_max - dim.outer_out_anti))) as u8
        } else {
            0
        }
    } else {
        //inactive part
        if d <= dim.in_inner_anti {
            0
        } else if d <= dim.inner_min {
            ((15 * (d - dim.in_inner_anti)) / (dim.inner_min - dim.in_inner_anti)) as u8
        } else if d <= dim.inner_max {
            15
        } else if d <= dim.inner_outer_anti {
            (15 - ((10 * (d - dim.inner_max)) / (dim.inner_outer_anti - dim.inner_max))) as u8
        } else if d <= dim.outer_out_anti {
            5
        } else if d <= dim.outer_max {
            5 - ((5 * (d - dim.outer_out_anti)) / (dim.outer_max - dim.outer_out_anti)) as u8
        } else {
            0
        }
    }
}

#[cfg(not(feature = "dma2d"))]
pub fn loader_rust(
    dim: LoaderDimensions,
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
                if (x as i32 * x as i32 + y as i32 * y as i32) <= dim.in_inner_anti {
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
                    show_all,
                    inverted,
                    end_vector,
                    n_start,
                    Point::new(x_c, y_c),
                    center,
                    dim,
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
    dim: LoaderDimensions,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    progress: u16,
    indeterminate: bool,
    icon: Option<(&[u8], Color, Offset)>,
) {
    let center = screen().center() + Offset::new(0, y_offset);
    let r = Rect::from_center_and_size(center, Offset::uniform(LOADER_OUTER * 2));
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

    let mut b1 = buffers::BufferLine16bpp::get();
    let mut b2 = buffers::BufferLine16bpp::get();
    let mut ib1 = buffers::BufferLine4bpp::get_cleared();
    let mut ib2 = buffers::BufferLine4bpp::get_cleared();
    let mut empty_line = buffers::BufferLine4bpp::get_cleared();

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
                    show_all,
                    inverted,
                    end_vector,
                    n_start,
                    Point::new(x_c, y_c),
                    center,
                    dim,
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
        unsafe {
            dma2d_start_blend(&icon_buffer.buffer, &loader_buffer.buffer, clamped.width());
        }
    }

    dma2d_wait_for_transfer();
}
