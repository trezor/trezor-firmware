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

    pub const fn x(x: i32) -> Self {
        Self::new(x, 0)
    }

    pub const fn y(y: i32) -> Self {
        Self::new(0, y)
    }

    pub fn on_axis(axis: Axis, a: i32) -> Self {
        match axis {
            Axis::Horizontal => Self::new(a, 0),
            Axis::Vertical => Self::new(0, a),
        }
    }

    pub fn axis(&self, axis: Axis) -> i32 {
        match axis {
            Axis::Horizontal => self.x,
            Axis::Vertical => self.y,
        }
    }

    pub fn abs(self) -> Self {
        Self::new(self.x.abs(), self.y.abs())
    }

    /// With `self` representing a rectangle size, returns top-left corner of
    /// the rectangle such that it is aligned relative to the `point`.
    pub fn snap(self, point: Point, x: Alignment, y: Alignment) -> Point {
        let x_off = match x {
            Alignment::Start => 0,
            Alignment::Center => self.x / 2,
            Alignment::End => self.x,
        };
        let y_off = match y {
            Alignment::Start => 0,
            Alignment::Center => self.y / 2,
            Alignment::End => self.y,
        };
        point - Self::new(x_off, y_off)
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

    pub fn size(&self) -> Offset {
        Offset::new(self.width(), self.height())
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

    pub fn bottom_center(&self) -> Point {
        self.bottom_left().center(self.bottom_right())
    }

    pub fn contains(&self, point: Point) -> bool {
        point.x >= self.x0 && point.x < self.x1 && point.y >= self.y0 && point.y < self.y1
    }

    pub fn inset(&self, insets: Insets) -> Self {
        Self {
            x0: self.x0 + insets.left,
            y0: self.y0 + insets.top,
            x1: self.x1 - insets.right,
            y1: self.y1 - insets.bottom,
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

    pub fn split_top(self, height: i32) -> (Self, Self) {
        let height = height.clamp(0, self.height());

        let top = Self {
            y1: self.y0 + height,
            ..self
        };
        let bottom = Self {
            y0: self.y0 + height,
            ..self
        };
        (top, bottom)
    }

    pub fn split_bottom(self, height: i32) -> (Self, Self) {
        self.split_top(self.height() - height)
    }

    pub fn split_left(self, width: i32) -> (Self, Self) {
        let width = width.clamp(0, self.width());

        let left = Self {
            x1: self.x0 + width,
            ..self
        };
        let right = Self {
            x0: self.x0 + width,
            ..self
        };
        (left, right)
    }

    pub fn split_right(self, width: i32) -> (Self, Self) {
        self.split_left(self.width() - width)
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Insets {
    pub top: i32,
    pub right: i32,
    pub bottom: i32,
    pub left: i32,
}

impl Insets {
    pub const fn new(top: i32, right: i32, bottom: i32, left: i32) -> Self {
        Self {
            top,
            right,
            bottom,
            left,
        }
    }

    pub const fn uniform(d: i32) -> Self {
        Self::new(d, d, d, d)
    }

    pub const fn top(d: i32) -> Self {
        Self::new(d, 0, 0, 0)
    }

    pub const fn right(d: i32) -> Self {
        Self::new(0, d, 0, 0)
    }

    pub const fn bottom(d: i32) -> Self {
        Self::new(0, 0, d, 0)
    }

    pub const fn left(d: i32) -> Self {
        Self::new(0, 0, 0, d)
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

    pub fn with_spacing(mut self, spacing: i32) -> Self {
        self.spacing = spacing;
        self
    }

    pub fn row_col(&self, row: usize, col: usize) -> Rect {
        let ncols = self.cols as i32;
        let nrows = self.rows as i32;
        let col = (col as i32).min(ncols - 1);
        let row = (row as i32).min(nrows - 1);

        // Total number of horizontal pixels used for spacing.
        let spacing_width = self.spacing * (ncols - 1);
        let spacing_height = self.spacing * (nrows - 1);

        // Divide what is left by number of cells to obtain width of each cell.
        let cell_width = (self.area.width() - spacing_width) / ncols;
        let cell_height = (self.area.height() - spacing_height) / nrows;

        // Not every area can be fully covered by equal-sized cells and spaces, there
        // might be serveral pixels left unused. We'll distribute them by 1px to
        // the leftmost cells.
        let leftover_width = (self.area.width() - spacing_width) % ncols;
        let leftover_height = (self.area.height() - spacing_height) % nrows;

        let mut top_left = self.area.top_left()
            + Offset::new(
                col * (cell_width + self.spacing),
                row * (cell_height + self.spacing),
            );
        // Some previous cells were 1px wider.
        top_left.x += leftover_width.min(col);
        top_left.y += leftover_height.min(row);

        let mut size = Offset::new(cell_width, cell_height);
        // This cell might be 1px wider.
        if col < leftover_width {
            size.x += 1
        }
        if row < leftover_height {
            size.y += 1
        }

        Rect::from_top_left_and_size(top_left, size)
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

    fn compute_spacing(&self, area: Rect, count: usize, size_sum: i32) -> (i32, i32) {
        let spacing_count = count.saturating_sub(1);
        let spacing_sum = spacing_count as i32 * self.spacing;
        let naive_size = size_sum + spacing_sum;
        let available_space = area.size().axis(self.axis);

        // scale down spacing to fit everything into area
        let (total_size, spacing) = if naive_size > available_space {
            let scaled_space = (available_space - size_sum) / spacing_count as i32;
            // forbid negative spacing
            (available_space, scaled_space.max(0))
        } else {
            (naive_size, self.spacing)
        };

        let init_cursor = match self.align {
            Alignment::Start => 0,
            Alignment::Center => available_space / 2 - total_size / 2,
            Alignment::End => available_space - total_size,
        };

        (init_cursor, spacing)
    }

    /// Arranges all `items` by parameters configured in `self` into `area`.
    /// Does not change the size of the items (only the position), but it needs
    /// to iterate (and ask for the size) twice.
    pub fn arrange(&self, area: Rect, items: &mut [impl Dimensions]) {
        let item_sum: i32 = items.iter_mut().map(|i| i.get_size().axis(self.axis)).sum();
        let (mut cursor, spacing) = self.compute_spacing(area, items.len(), item_sum);

        for item in items {
            let top_left = area.top_left() + Offset::on_axis(self.axis, cursor);
            let size = item.get_size();
            item.set_area(Rect::from_top_left_and_size(top_left, size));
            cursor += size.axis(self.axis);
            cursor += spacing;
        }
    }

    /// Arranges number of items of the same size into `area`. The `sink`
    /// closure is called `count` times with top left point of each item as
    /// argument. Items are centered along the cross axis.
    pub fn arrange_uniform(
        &self,
        area: Rect,
        count: usize,
        size: Offset,
        sink: &mut dyn FnMut(Point),
    ) {
        let item_size = size.axis(self.axis);
        let (mut cursor, spacing) = self.compute_spacing(area, count, (count as i32) * item_size);
        let cross_coord =
            area.size().axis(self.axis.cross()) / 2 - size.axis(self.axis.cross()) / 2;

        for _ in 0..count {
            let top_left = area.top_left()
                + Offset::on_axis(self.axis, cursor)
                + Offset::on_axis(self.axis.cross(), cross_coord);
            sink(top_left);
            cursor += item_size;
            cursor += spacing;
        }
    }
}

/// Types that have a size and a position.
pub trait Dimensions {
    fn get_size(&mut self) -> Offset;
    fn set_area(&mut self, area: Rect);
}
