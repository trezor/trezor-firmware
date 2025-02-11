use crate::{trezorhal::display, ui::geometry::Offset};
/// This is a simple and fast blurring algorithm that uses a box filter -
/// a square kernel with all coefficients set to 1.
///
/// The `BlurFilter` structure holds the context of a simple 2D window averaging
/// filter - a sliding window and the sum of all rows in the sliding window.
///
/// The `BlurFilter` implements only five public functions - `new`, `push`,
/// `push_read`, `pop` and `pop_ready`.
///
/// The `new()` function creates a blur filter context.
///   - The `size` argument specifies the size of the blurred area.
///   - The `radius` argument specifies the length of the kernel side.
///
/// ```rust
/// let blur = BlurFilter::new(size, radius);
/// ```
///
/// The `push_ready()` function returns the row from the source bitmap
/// needed to be pushed
///
/// The `push()` function pushes source row data into the sliding window and
/// performs all necessary calculations.
///
/// ```rust
/// if let Some(y) = blur.push_ready() {
///     blur.push(&src_bitmap.row(y)[x0..x1]);
/// }
/// ```
///
/// The `pop_ready()` function returns the row from the destination bitmap
/// that can be popped out
///
/// The `pop()` function pops the blurred row from the sliding window.
///
/// ```rust
/// if let Some(y) = blur.pop_ready() {
///     blur.pop(&mut dst_bitmap.row(y)[x0..x1]);
/// }
/// ```
use core::mem::size_of;

const MAX_RADIUS: usize = 4;
const MAX_SIDE: usize = 1 + MAX_RADIUS * 2;
const MAX_WIDTH: usize = display::DISPLAY_RESX as usize;

pub type BlurBuff = [u8; MAX_WIDTH * (MAX_SIDE * 3 + size_of::<u16>() * 3) + 8];

#[derive(Default, Copy, Clone)]
pub struct Rgb<T> {
    pub r: T,
    pub g: T,
    pub b: T,
}

impl Rgb<u16> {
    #[inline(always)]
    fn mulshift(&self, multiplier: u32, shift: u8) -> Rgb<u8> {
        Rgb::<u8> {
            r: ((self.r as u32 * multiplier) >> shift) as u8,
            g: ((self.g as u32 * multiplier) >> shift) as u8,
            b: ((self.b as u32 * multiplier) >> shift) as u8,
        }
    }
}

impl From<u16> for Rgb<u16> {
    #[inline(always)]
    fn from(value: u16) -> Self {
        Self {
            r: (value >> 8) & 0xF8,
            g: (value >> 3) & 0xFC,
            b: (value << 3) & 0xF8,
        }
    }
}

impl From<u32> for Rgb<u16> {
    #[inline(always)]
    fn from(value: u32) -> Self {
        Self {
            r: ((value >> 16) & 0xFF) as u16,
            g: ((value >> 8) & 0xFF) as u16,
            b: (value & 0xFF) as u16,
        }
    }
}

impl core::ops::AddAssign<u16> for Rgb<u16> {
    #[inline(always)]
    fn add_assign(&mut self, rhs: u16) {
        let rgb: Self = rhs.into();
        *self += rgb;
    }
}

impl core::ops::AddAssign<u32> for Rgb<u16> {
    #[inline(always)]
    fn add_assign(&mut self, rhs: u32) {
        let rgb: Self = rhs.into();
        *self += rgb;
    }
}

impl core::ops::SubAssign<u16> for Rgb<u16> {
    #[inline(always)]
    fn sub_assign(&mut self, rhs: u16) {
        let rgb: Self = rhs.into();
        *self -= rgb;
    }
}

impl core::ops::SubAssign<u32> for Rgb<u16> {
    #[inline(always)]
    fn sub_assign(&mut self, rhs: u32) {
        let rgb: Self = rhs.into();
        *self -= rgb;
    }
}

impl core::ops::AddAssign for Rgb<u16> {
    #[inline(always)]
    fn add_assign(&mut self, rhs: Self) {
        self.r += rhs.r;
        self.g += rhs.g;
        self.b += rhs.b;
    }
}

impl core::ops::SubAssign for Rgb<u16> {
    #[inline(always)]
    fn sub_assign(&mut self, rhs: Self) {
        self.r -= rhs.r;
        self.g -= rhs.g;
        self.b -= rhs.b;
    }
}

impl From<Rgb<u8>> for u16 {
    #[inline(always)]
    fn from(value: Rgb<u8>) -> u16 {
        let r = (value.r as u16 & 0xF8) << 8;
        let g = (value.g as u16 & 0xFC) << 3;
        let b = (value.b as u16 & 0xF8) >> 3;
        r | g | b
    }
}

impl From<Rgb<u8>> for u32 {
    #[inline(always)]
    fn from(value: Rgb<u8>) -> u32 {
        let r = (value.r as u32) << 16;
        let g = (value.g as u32) << 8;
        let b = value.b as u32;
        let alpha = 0xFF000000;
        alpha | r | g | b
    }
}

impl From<Rgb<u16>> for Rgb<u8> {
    #[inline(always)]
    fn from(value: Rgb<u16>) -> Self {
        Self {
            r: value.r as u8,
            g: value.g as u8,
            b: value.b as u8,
        }
    }
}

impl core::ops::AddAssign<Rgb<u8>> for Rgb<u16> {
    #[inline(always)]
    fn add_assign(&mut self, rhs: Rgb<u8>) {
        self.r += rhs.r as u16;
        self.g += rhs.g as u16;
        self.b += rhs.b as u16;
    }
}

impl core::ops::SubAssign<Rgb<u8>> for Rgb<u16> {
    #[inline(always)]
    fn sub_assign(&mut self, rhs: Rgb<u8>) {
        self.r -= rhs.r as u16;
        self.g -= rhs.g as u16;
        self.b -= rhs.b as u16;
    }
}

pub struct BlurAlgorithm<'a> {
    size: Offset,
    radius: usize,
    row: usize,
    totals: &'a mut [Rgb<u16>],
    window: &'a mut [Rgb<u8>],
    row_count: usize,
}

impl<'a> BlurAlgorithm<'a> {
    /// Constraints:
    ///   width <= MAX_WIDTH
    ///   radius <= MAX_RADIUS
    ///   width >= radius
    pub fn new(size: Offset, radius: usize, memory: &'a mut BlurBuff) -> Result<Self, ()> {
        assert!(size.x as usize <= MAX_WIDTH);
        assert!(radius <= MAX_RADIUS);
        assert!(size.x as usize > 2 * radius - 1);

        // Split buffer into two parts
        let window_size = size.x as usize * (1 + radius * 2);
        let (window_buff, total_buff) =
            memory.split_at_mut(window_size * core::mem::size_of::<Rgb<u8>>());

        // Allocate `window` from the beginning of the buffer
        let (_, window_buff, _) = unsafe { window_buff.align_to_mut() };
        if window_buff.len() < window_size {
            return Err(());
        }
        let window = &mut window_buff[..window_size];
        window.iter_mut().for_each(|it| *it = Rgb::<u8>::default());

        // Allocate `totals` from the rest of the buffer
        let (_, totals_buff, _) = unsafe { total_buff.align_to_mut() };
        if totals_buff.len() < size.x as usize {
            return Err(());
        }
        let totals = &mut totals_buff[..size.x as usize];
        totals.iter_mut().for_each(|it| *it = Rgb::<u16>::default());

        Ok(Self {
            size,
            radius,
            row: 0,
            window,
            totals,
            row_count: 0,
        })
    }

    /// Returns the length of the box filter side.
    fn box_side(&self) -> usize {
        1 + self.radius * 2
    }

    /// Takes an input row and calculates the same-sized vector
    /// as the floating average of n subsequent elements where n = 2 * radius +
    /// 1. Finally, it stores it into the specifed row in the  sliding
    /// window.
    fn average_to_row<T>(&mut self, inp: &[T], row: usize)
    where
        T: Copy + Into<Rgb<u16>>,
    {
        let radius = self.radius;
        let offset = self.size.x as usize * row;
        let row = &mut self.window[offset..offset + self.size.x as usize];

        let mut sum = Rgb::<u16>::default();

        let divisor = (radius * 2 + 1) as u16;
        let shift = 10;
        let multiplier = (1 << shift) as u32 / divisor as u32;

        // Prepare before averaging
        for i in 0..radius {
            sum += inp[0].into(); // Duplicate pixels on the left
            sum += inp[i].into(); // Add first radius pixels
        }

        // Process the first few pixels of the row
        for i in 0..radius {
            sum += inp[i + radius].into();
            row[i] = sum.mulshift(multiplier, shift);
            sum -= inp[0].into();
        }

        // Process the inner part of the row
        for i in radius..row.len() - radius {
            sum += inp[i + radius].into();
            row[i] = sum.mulshift(multiplier, shift);
            sum -= inp[i - radius].into();
        }

        // Process the last few pixels of the row
        for i in (row.len() - radius)..row.len() {
            sum += inp[inp.len() - 1].into();
            row[i] = sum.mulshift(multiplier, shift);
            sum -= inp[i - radius].into(); // Duplicate pixels on the right
        }
    }

    /// Copy one row from the window to the another row.
    fn copy_row(&mut self, from_row: usize, to_row: usize) {
        let from_offset = self.size.x as usize * from_row;
        let to_offset = self.size.x as usize * to_row;
        for i in 0..self.size.x as usize {
            self.window[to_offset + i] = self.window[from_offset + i];
        }
    }

    /// Subtracts the specified row of sliding window from `totals[]`.
    fn subtract_row(&mut self, row: usize) {
        let offset = self.size.x as usize * row;
        let row = &self.window[offset..offset + self.size.x as usize];

        for (i, item) in row.iter().enumerate() {
            self.totals[i] -= *item;
        }
    }

    /// Adds the specified row of sliding window to `totals[]`.
    fn add_row(&mut self, row: usize) {
        let offset = self.size.x as usize * row;
        let row = &self.window[offset..offset + self.size.x as usize];

        for (i, item) in row.iter().enumerate() {
            self.totals[i] += *item;
        }
    }

    /// Pushes the most recently pushed row again.
    fn push_last_row(&mut self) {
        let to_row = self.row;
        let from_row = if to_row > 0 {
            to_row - 1
        } else {
            self.box_side() - 1
        };

        self.subtract_row(to_row);
        self.copy_row(from_row, to_row);
        self.add_row(to_row);

        self.row = (to_row + 1) % self.box_side();
        self.row_count += 1;
    }

    /// Returns the index of the row needed to be pushed into.
    pub fn push_ready(&self) -> Option<i16> {
        let y = core::cmp::max(0, self.row_count as i16 - self.radius as i16);
        if y < self.size.y {
            Some(y)
        } else {
            None
        }
    }

    /// Takes the source row and pushes it into the sliding window.
    pub fn push<T>(&mut self, input: &[T])
    where
        T: Copy + Into<Rgb<u16>>,
    {
        let row = self.row;

        self.subtract_row(row);
        self.average_to_row(input, row);
        self.add_row(row);

        self.row = (row + 1) % self.box_side();
        self.row_count += 1;

        while self.row_count <= self.radius {
            self.push_last_row();
        }
    }

    /// Returns the index of row ready to be popped out.
    pub fn pop_ready(&self) -> Option<i16> {
        let y = self.row_count as i16 - self.box_side() as i16;
        if y < 0 {
            None
        } else {
            Some(y)
        }
    }

    /// Copies the current content of `totals[]` to the output buffer.
    pub fn pop<T>(&mut self, output: &mut [T], dim: Option<u8>)
    where
        T: Copy + Into<Rgb<u16>> + From<Rgb<u8>>,
    {
        let divisor = match dim {
            Some(dim) => {
                if dim > 0 {
                    (self.box_side() as u16 * 255) / dim as u16
                } else {
                    65535u16
                }
            }
            None => self.box_side() as u16,
        };

        let shift = 10;
        let multiplier = (1 << shift) as u32 / divisor as u32;

        for (i, item) in output.iter_mut().enumerate() {
            *item = self.totals[i].mulshift(multiplier, shift).into();
        }

        if self.push_ready().is_none() {
            self.push_last_row();
        }
    }
}
