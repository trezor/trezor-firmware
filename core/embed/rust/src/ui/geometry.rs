use core::ops::{Add, Sub};

/// Relative offset in 2D space, used for representing translation and
/// dimensions of objects. Absolute positions on the screen are represented by
/// the `Point` type.
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Offset {
    pub x: i32,
    pub y: i32,
}

impl Offset {
    pub const fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }

    pub const fn uniform(a: i32) -> Self {
        Self::new(a, a)
    }

    pub const fn zero() -> Self {
        Self::new(0, 0)
    }

    pub fn on_axis(axis: Axis, a: i32) -> Self {
        match axis {
            Axis::Horizontal => Self::new(a, 0),
            Axis::Vertical => Self::new(0, a),
        }
    }

    pub fn abs(self) -> Self {
        Self::new(self.x.abs(), self.y.abs())
    }
}

impl Add<Offset> for Offset {
    type Output = Offset;

    fn add(self, rhs: Offset) -> Self::Output {
        Self::new(self.x + rhs.x, self.y + rhs.y)
    }
}

impl Sub<Offset> for Offset {
    type Output = Offset;

    fn sub(self, rhs: Offset) -> Self::Output {
        Self::new(self.x - rhs.x, self.y - rhs.y)
    }
}

/// A point in 2D space defined by the the `x` and `y` coordinate. Relative
/// coordinates, vectors, and offsets are represented by the `Offset` type.
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Point {
    pub x: i32,
    pub y: i32,
}

impl Point {
    pub const fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }

    pub const fn zero() -> Self {
        Self::new(0, 0)
    }

    pub fn center(self, rhs: Self) -> Self {
        Self::new((self.x + rhs.x) / 2, (self.y + rhs.y) / 2)
    }
}

impl Add<Offset> for Point {
    type Output = Point;

    fn add(self, rhs: Offset) -> Self::Output {
        Self::new(self.x + rhs.x, self.y + rhs.y)
    }
}

impl Sub<Offset> for Point {
    type Output = Point;

    fn sub(self, rhs: Offset) -> Self::Output {
        Self::new(self.x - rhs.x, self.y - rhs.y)
    }
}

impl Sub<Point> for Point {
    type Output = Offset;

    fn sub(self, rhs: Point) -> Self::Output {
        Offset::new(self.x - rhs.x, self.y - rhs.y)
    }
}

/// A rectangle in 2D space defined by the top-left point `x0`,`y0` and the
/// bottom-right point `x1`,`y1`.
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Rect {
    pub x0: i32,
    pub y0: i32,
    pub x1: i32,
    pub y1: i32,
}

impl Rect {
    pub const fn new(p0: Point, p1: Point) -> Self {
        Self {
            x0: p0.x,
            y0: p0.y,
            x1: p1.x,
            y1: p1.y,
        }
    }

    pub const fn zero() -> Self {
        Self::new(Point::zero(), Point::zero())
    }

    pub fn from_top_left_and_size(p0: Point, size: Offset) -> Self {
        Self::new(p0, p0 + size)
    }

    pub fn from_center_and_size(p: Point, size: Offset) -> Self {
        Self {
            x0: p.x - size.x / 2,
            y0: p.y - size.y / 2,
            x1: p.x + size.x / 2,
            y1: p.y + size.y / 2,
        }
    }

    pub fn width(&self) -> i32 {
        self.x1 - self.x0
    }

    pub fn height(&self) -> i32 {
        self.y1 - self.y0
    }

    pub fn top_left(&self) -> Point {
        Point::new(self.x0, self.y0)
    }

    pub fn top_right(&self) -> Point {
        Point::new(self.x1, self.y0)
    }

    pub fn bottom_left(&self) -> Point {
        Point::new(self.x0, self.y1)
    }

    pub fn bottom_right(&self) -> Point {
        Point::new(self.x1, self.y1)
    }

    pub fn center(&self) -> Point {
        self.top_left().center(self.bottom_right())
    }

    pub fn contains(&self, point: Point) -> bool {
        point.x >= self.x0 && point.x < self.x1 && point.y >= self.y0 && point.y < self.y1
    }

    pub fn inset(&self, uniform: i32) -> Self {
        Self {
            x0: self.x0 + uniform,
            y0: self.y0 + uniform,
            x1: self.x1 - uniform,
            y1: self.y1 - uniform,
        }
    }

    pub fn cut_from_left(&self, width: i32) -> Self {
        Self {
            x0: self.x0,
            y0: self.y0,
            x1: self.x0 + width,
            y1: self.y1,
        }
    }

    pub fn cut_from_right(&self, width: i32) -> Self {
        Self {
            x0: self.x1 - width,
            y0: self.y0,
            x1: self.x1,
            y1: self.y1,
        }
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Alignment {
    Start,
    Center,
    End,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Axis {
    Horizontal,
    Vertical,
}

impl Axis {
    pub fn main<T>(self, x: T, y: T) -> T {
        match self {
            Axis::Horizontal => x,
            Axis::Vertical => y,
        }
    }

    pub fn cross(self) -> Self {
        match self {
            Axis::Horizontal => Axis::Vertical,
            Axis::Vertical => Axis::Horizontal,
        }
    }
}

pub struct Grid {
    /// Number of rows (cells on the y-axis) in the grid.
    pub rows: usize,
    /// Number of columns (cells on the x-axis) in the grid.
    pub cols: usize,
    /// Padding between cells.
    pub spacing: i32,
    /// Total area covered by this grid.
    pub area: Rect,
}

impl Grid {
    pub fn new(area: Rect, rows: usize, cols: usize) -> Self {
        Self {
            rows,
            cols,
            spacing: 0,
            area,
        }
    }

    pub fn row_col(&self, row: usize, col: usize) -> Rect {
        let cell_width = self.area.width() / self.cols as i32;
        let cell_height = self.area.height() / self.rows as i32;
        let x = col as i32 * cell_width;
        let y = row as i32 * cell_height;
        Rect {
            x0: self.area.x0 + x,
            y0: self.area.y0 + y,
            x1: self.area.x0 + x + (cell_width - self.spacing),
            y1: self.area.y0 + y + (cell_height - self.spacing),
        }
    }

    pub fn cell(&self, index: usize) -> Rect {
        self.row_col(index / self.cols, index % self.cols)
    }
}

#[derive(Copy, Clone)]
pub struct LinearLayout {
    axis: Axis,
    align: Alignment,
    spacing: i32,
}

impl LinearLayout {
    pub fn horizontal() -> Self {
        Self {
            axis: Axis::Horizontal,
            align: Alignment::Start,
            spacing: 0,
        }
    }

    pub fn vertical() -> Self {
        Self {
            axis: Axis::Vertical,
            align: Alignment::Start,
            spacing: 0,
        }
    }

    pub fn align_at_start(mut self) -> Self {
        self.align = Alignment::Start;
        self
    }

    pub fn align_at_center(mut self) -> Self {
        self.align = Alignment::Center;
        self
    }

    pub fn align_at_end(mut self) -> Self {
        self.align = Alignment::End;
        self
    }

    pub fn with_spacing(mut self, spacing: i32) -> Self {
        self.spacing = spacing;
        self
    }

    /// Arranges all `items` by parameters configured in `self` into `area`.
    /// Does not change the size of the items (only the position), but it needs
    /// to iterate (and ask for the size) twice.
    pub fn arrange(&self, area: Rect, items: &mut [impl Dimensions]) {
        let item_sum: i32 = items
            .iter_mut()
            .map(|i| {
                let size = i.get_size();
                self.axis.main(size.x, size.y)
            })
            .sum();
        let spacing_count = items.len().saturating_sub(1);
        let spacing_sum = spacing_count as i32 * self.spacing;
        let total_size = item_sum + spacing_sum;

        let available_space = match self.axis {
            Axis::Horizontal => area.width(),
            Axis::Vertical => area.height(),
        };
        let mut cursor = match self.align {
            Alignment::Start => 0,
            Alignment::Center => available_space / 2 - total_size / 2,
            Alignment::End => available_space - total_size,
        };

        for item in items {
            let top_left = area.top_left() + Offset::on_axis(self.axis, cursor);
            let size = item.get_size();
            item.set_area(Rect::from_top_left_and_size(top_left, size));
            cursor += self.axis.main(size.x, size.y);
            cursor += self.spacing;
        }
    }
}

/// Types that have a size and a position.
pub trait Dimensions {
    fn get_size(&mut self) -> Offset;
    fn set_area(&mut self, area: Rect);
}
