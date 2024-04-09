use crate::ui::lerp::Lerp;
use core::ops::{Add, Mul, Neg, Sub};

const fn min(a: i16, b: i16) -> i16 {
    if a < b {
        a
    } else {
        b
    }
}

const fn max(a: i16, b: i16) -> i16 {
    if a > b {
        a
    } else {
        b
    }
}

const fn clamp(x: i16, min: i16, max: i16) -> i16 {
    if x < min {
        min
    } else if x > max {
        max
    } else {
        x
    }
}

/// Relative offset in 2D space, used for representing translation and
/// dimensions of objects. Absolute positions on the screen are represented by
/// the `Point` type.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub struct Offset {
    pub x: i16,
    pub y: i16,
}

impl Offset {
    pub const fn new(x: i16, y: i16) -> Self {
        Self { x, y }
    }

    pub const fn uniform(a: i16) -> Self {
        Self::new(a, a)
    }

    pub const fn zero() -> Self {
        Self::new(0, 0)
    }

    pub const fn x(x: i16) -> Self {
        Self::new(x, 0)
    }

    pub const fn y(y: i16) -> Self {
        Self::new(0, y)
    }

    pub const fn on_axis(axis: Axis, a: i16) -> Self {
        match axis {
            Axis::Horizontal => Self::new(a, 0),
            Axis::Vertical => Self::new(0, a),
        }
    }

    pub const fn axis(&self, axis: Axis) -> i16 {
        match axis {
            Axis::Horizontal => self.x,
            Axis::Vertical => self.y,
        }
    }

    pub const fn abs(self) -> Self {
        Self::new(self.x.abs(), self.y.abs())
    }

    /// With `self` representing a rectangle size, returns top-left corner of
    /// the rectangle such that it is aligned relative to the `point`.
    pub const fn snap(self, point: Point, alignment: Alignment2D) -> Point {
        let x_off = match alignment.0 {
            Alignment::Start => 0,
            Alignment::Center => self.x / 2,
            Alignment::End => self.x,
        };
        let y_off = match alignment.1 {
            Alignment::Start => 0,
            Alignment::Center => self.y / 2,
            Alignment::End => self.y,
        };
        point.ofs(Self::new(-x_off, -y_off))
    }

    pub const fn neg(self) -> Self {
        Self::new(-self.x, -self.y)
    }

    pub const fn add(self, rhs: Offset) -> Self {
        Self::new(self.x + rhs.x, self.y + rhs.y)
    }

    pub const fn sub(self, rhs: Offset) -> Self {
        self.add(rhs.neg())
    }
}

impl Add<Offset> for Offset {
    type Output = Offset;

    fn add(self, rhs: Offset) -> Self::Output {
        Offset::add(self, rhs)
    }
}

impl Neg for Offset {
    type Output = Offset;

    fn neg(self) -> Self::Output {
        Offset::neg(self)
    }
}

impl Sub<Offset> for Offset {
    type Output = Offset;

    fn sub(self, rhs: Offset) -> Self::Output {
        Offset::sub(self, rhs)
    }
}

impl Mul<f32> for Offset {
    type Output = Offset;

    fn mul(self, rhs: f32) -> Self::Output {
        Offset::new(
            (f32::from(self.x) * rhs) as i16,
            (f32::from(self.y) * rhs) as i16,
        )
    }
}

impl From<Point> for Offset {
    fn from(val: Point) -> Self {
        Offset::new(val.x, val.y)
    }
}

impl Lerp for Offset {
    fn lerp(a: Self, b: Self, t: f32) -> Self {
        Offset::new(i16::lerp(a.x, b.x, t), i16::lerp(a.y, b.y, t))
    }
}

/// A point in 2D space defined by the the `x` and `y` coordinate. Relative
/// coordinates, vectors, and offsets are represented by the `Offset` type.
#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct Point {
    pub x: i16,
    pub y: i16,
}

impl Point {
    pub const fn new(x: i16, y: i16) -> Self {
        Self { x, y }
    }

    pub const fn zero() -> Self {
        Self::new(0, 0)
    }

    pub const fn center(self, rhs: Self) -> Self {
        Self::new((self.x + rhs.x) / 2, (self.y + rhs.y) / 2)
    }

    pub const fn ofs(self, rhs: Offset) -> Self {
        Self::new(self.x + rhs.x, self.y + rhs.y)
    }

    pub const fn sub(self, rhs: Point) -> Offset {
        Offset::new(self.x - rhs.x, self.y - rhs.y)
    }
}

impl Add<Offset> for Point {
    type Output = Point;

    fn add(self, rhs: Offset) -> Self::Output {
        self.ofs(rhs)
    }
}

impl Sub<Offset> for Point {
    type Output = Point;

    fn sub(self, rhs: Offset) -> Self::Output {
        self.ofs(-rhs)
    }
}

impl Sub<Point> for Point {
    type Output = Offset;

    fn sub(self, rhs: Point) -> Self::Output {
        Point::sub(self, rhs)
    }
}

impl core::ops::Neg for Point {
    type Output = Point;

    fn neg(self) -> Self::Output {
        Point {
            x: -self.x,
            y: -self.y,
        }
    }
}

impl Lerp for Point {
    fn lerp(a: Self, b: Self, t: f32) -> Self {
        Point::new(i16::lerp(a.x, b.x, t), i16::lerp(a.y, b.y, t))
    }
}

impl From<Offset> for Point {
    fn from(val: Offset) -> Self {
        Point::new(val.x, val.y)
    }
}

/// A rectangle in 2D space defined by the top-left point `x0`,`y0` and the
/// bottom-right point `x1`,`y1`.
/// NOTE: bottom-right point is not included in the rectangle, it is outside of
/// it.
#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Rect {
    pub x0: i16,
    pub y0: i16,
    pub x1: i16,
    pub y1: i16,
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

    /// Returns a rectangle of `size` such that `point` is on position specified
    /// by `alignment`.
    pub const fn snap(point: Point, size: Offset, alignment: Alignment2D) -> Rect {
        Self::from_top_left_and_size(size.snap(point, alignment), size)
    }

    pub const fn from_top_left_and_size(p0: Point, size: Offset) -> Self {
        Self {
            x0: p0.x,
            y0: p0.y,
            x1: p0.x + size.x,
            y1: p0.y + size.y,
        }
    }

    pub const fn from_size(size: Offset) -> Self {
        Self::from_top_left_and_size(Point::zero(), size)
    }

    pub const fn from_top_right_and_size(p0: Point, size: Offset) -> Self {
        let top_left = Point::new(p0.x - size.x, p0.y);
        Self::from_top_left_and_size(top_left, size)
    }

    pub const fn from_bottom_left_and_size(p0: Point, size: Offset) -> Self {
        let top_left = Point::new(p0.x, p0.y - size.y);
        Self::from_top_left_and_size(top_left, size)
    }

    pub const fn from_bottom_right_and_size(p0: Point, size: Offset) -> Self {
        let top_left = Point::new(p0.x - size.x, p0.y - size.y);
        Self::from_top_left_and_size(top_left, size)
    }

    pub const fn from_center_and_size(p: Point, size: Offset) -> Self {
        let x0 = p.x - size.x / 2;
        let y0 = p.y - size.y / 2;
        let x1 = x0 + size.x;
        let y1 = y0 + size.y;

        Self { x0, y0, x1, y1 }
    }

    pub const fn with_top_left(self, p0: Point) -> Self {
        Self::from_top_left_and_size(p0, self.size())
    }

    pub const fn with_size(self, size: Offset) -> Self {
        Self::from_top_left_and_size(self.top_left(), size)
    }

    pub const fn with_width(self, width: i16) -> Self {
        self.with_size(Offset::new(width, self.height()))
    }

    pub const fn with_height(self, height: i16) -> Self {
        self.with_size(Offset::new(self.width(), height))
    }

    pub const fn width(&self) -> i16 {
        self.x1 - self.x0
    }

    pub const fn height(&self) -> i16 {
        self.y1 - self.y0
    }

    pub const fn size(&self) -> Offset {
        Offset::new(self.width(), self.height())
    }

    pub const fn top_left(&self) -> Point {
        Point::new(self.x0, self.y0)
    }

    pub const fn top_right(&self) -> Point {
        Point::new(self.x1, self.y0)
    }

    pub const fn bottom_left(&self) -> Point {
        Point::new(self.x0, self.y1)
    }

    pub const fn bottom_right(&self) -> Point {
        Point::new(self.x1, self.y1)
    }

    pub const fn center(&self) -> Point {
        self.top_left().center(self.bottom_right())
    }

    pub const fn top_center(&self) -> Point {
        self.top_left().center(self.top_right())
    }

    pub const fn bottom_center(&self) -> Point {
        self.bottom_left().center(self.bottom_right())
    }

    pub const fn left_center(&self) -> Point {
        self.bottom_left().center(self.top_left())
    }

    pub const fn right_center(&self) -> Point {
        self.bottom_right().center(self.top_right())
    }

    /// Checks if the rectangle is empty.
    ///
    /// It is possible to custruct a rectangle with negative width or height.
    /// All such rectangles are considered as empty.
    pub const fn is_empty(&self) -> bool {
        self.x0 >= self.x1 || self.y0 >= self.y1
    }

    /// Whether a `Point` is inside the `Rect`.
    pub const fn contains(&self, point: Point) -> bool {
        point.x >= self.x0 && point.x < self.x1 && point.y >= self.y0 && point.y < self.y1
    }

    /// Create a bigger `Rect` that contains both `self` and `other`.
    pub const fn union(&self, other: Self) -> Self {
        Self {
            x0: min(self.x0, other.x0),
            y0: min(self.y0, other.y0),
            x1: max(self.x1, other.x1),
            y1: max(self.y1, other.y1),
        }
    }

    /// Create a smaller `Rect` from the bigger one by moving
    /// all the four sides closer to the center.
    pub const fn inset(&self, insets: Insets) -> Self {
        Self {
            x0: self.x0 + insets.left,
            y0: self.y0 + insets.top,
            x1: self.x1 - insets.right,
            y1: self.y1 - insets.bottom,
        }
    }

    pub const fn outset(&self, insets: Insets) -> Self {
        Self {
            x0: self.x0 - insets.left,
            y0: self.y0 - insets.top,
            x1: self.x1 + insets.right,
            y1: self.y1 + insets.bottom,
        }
    }

    /// Move all the sides further from the center by the same distance.
    pub const fn expand(&self, size: i16) -> Self {
        self.outset(Insets::uniform(size))
    }

    /// Move all the sides closer to the center by the same distance.
    pub const fn shrink(&self, size: i16) -> Self {
        self.inset(Insets::uniform(size))
    }

    /// Split `Rect` into top and bottom, given the top one's `height`.
    pub const fn split_top(self, height: i16) -> (Self, Self) {
        let height = clamp(height, 0, self.height());

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

    /// Split `Rect` into top and bottom, given the bottom one's `height`.
    pub const fn split_bottom(self, height: i16) -> (Self, Self) {
        self.split_top(self.height() - height)
    }

    /// Split `Rect` into left and right, given the left one's `width`.
    pub const fn split_left(self, width: i16) -> (Self, Self) {
        let width = clamp(width, 0, self.width());

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

    /// Split `Rect` into left and right, given the right one's `width`.
    pub const fn split_right(self, width: i16) -> (Self, Self) {
        self.split_left(self.width() - width)
    }

    /// Split `Rect` into left, center and right, given the center one's
    /// `width`. Center element is symmetric, left and right have the same
    /// size. In case left and right cannot be the same size, right is 1px
    /// wider.
    pub const fn split_center(self, width: i16) -> (Self, Self, Self) {
        let left_right_width = (self.width() - width) / 2;
        let (left, center_right) = self.split_left(left_right_width);
        let (center, right) = center_right.split_left(width);
        (left, center, right)
    }

    /// Calculates the intersection of two rectangles.
    ///
    /// If the rectangles do not intersect, an "empty" rectangle is returned.
    ///
    /// The implementation may yield rectangles with negative width or height
    /// if there's no intersection. Such rectangles are considered empty,
    /// and subsequent operations like clamp, union, and translation
    /// work correctly with them. However, it's important to be aware of this
    /// behavior.
    pub const fn clamp(self, limit: Rect) -> Self {
        Self {
            x0: max(self.x0, limit.x0),
            y0: max(self.y0, limit.y0),
            x1: min(self.x1, limit.x1),
            y1: min(self.y1, limit.y1),
        }
    }

    pub const fn ensure_even_width(self) -> Self {
        if self.width() % 2 == 0 {
            self
        } else {
            self.with_size(Offset::new(self.size().x - 1, self.size().y))
        }
    }

    /// Moving `Rect` by the given offset.
    pub const fn translate(&self, offset: Offset) -> Self {
        Self {
            x0: self.x0 + offset.x,
            y0: self.y0 + offset.y,
            x1: self.x1 + offset.x,
            y1: self.y1 + offset.y,
        }
    }

    /// Get all four corner points.
    pub fn corner_points(&self) -> [Point; 4] {
        [
            self.top_left(),
            self.top_right() - Offset::x(1),
            self.bottom_right() - Offset::uniform(1),
            self.bottom_left() - Offset::y(1),
        ]
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Insets {
    pub top: i16,
    pub right: i16,
    pub bottom: i16,
    pub left: i16,
}

impl Insets {
    pub const fn new(top: i16, right: i16, bottom: i16, left: i16) -> Self {
        Self {
            top,
            right,
            bottom,
            left,
        }
    }

    pub const fn uniform(d: i16) -> Self {
        Self::new(d, d, d, d)
    }

    pub const fn top(d: i16) -> Self {
        Self::new(d, 0, 0, 0)
    }

    pub const fn right(d: i16) -> Self {
        Self::new(0, d, 0, 0)
    }

    pub const fn bottom(d: i16) -> Self {
        Self::new(0, 0, d, 0)
    }

    pub const fn left(d: i16) -> Self {
        Self::new(0, 0, 0, d)
    }

    pub const fn sides(d: i16) -> Self {
        Self::new(0, d, 0, d)
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum Alignment {
    Start,
    Center,
    End,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct Alignment2D(pub Alignment, pub Alignment);

impl Alignment2D {
    pub const TOP_LEFT: Alignment2D = Alignment2D(Alignment::Start, Alignment::Start);
    pub const TOP_RIGHT: Alignment2D = Alignment2D(Alignment::End, Alignment::Start);
    pub const TOP_CENTER: Alignment2D = Alignment2D(Alignment::Center, Alignment::Start);
    pub const CENTER: Alignment2D = Alignment2D(Alignment::Center, Alignment::Center);
    pub const CENTER_LEFT: Alignment2D = Alignment2D(Alignment::Start, Alignment::Center);
    pub const CENTER_RIGHT: Alignment2D = Alignment2D(Alignment::End, Alignment::Center);
    pub const BOTTOM_LEFT: Alignment2D = Alignment2D(Alignment::Start, Alignment::End);
    pub const BOTTOM_RIGHT: Alignment2D = Alignment2D(Alignment::End, Alignment::End);
    pub const BOTTOM_CENTER: Alignment2D = Alignment2D(Alignment::Center, Alignment::End);
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

    pub const fn cross(self) -> Self {
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
    pub spacing: i16,
    /// Total area covered by this grid.
    pub area: Rect,
}

impl Grid {
    pub const fn new(area: Rect, rows: usize, cols: usize) -> Self {
        Self {
            rows,
            cols,
            spacing: 0,
            area,
        }
    }

    pub const fn with_spacing(self, spacing: i16) -> Self {
        Self { spacing, ..self }
    }

    pub const fn row_col(&self, row: usize, col: usize) -> Rect {
        let ncols = self.cols as i16;
        let nrows = self.rows as i16;
        let col = min(col as i16, ncols - 1);
        let row = min(row as i16, nrows - 1);

        // Total number of horizontal pixels used for spacing.
        let spacing_width = self.spacing * (ncols - 1);
        let spacing_height = self.spacing * (nrows - 1);

        // Divide what is left by number of cells to obtain width of each cell.
        let cell_width = (self.area.width() - spacing_width) / ncols;
        let cell_height = (self.area.height() - spacing_height) / nrows;

        // Not every area can be fully covered by equal-sized cells and spaces, there
        // might be several pixels left unused. We'll distribute them by 1px to
        // the leftmost cells.
        let leftover_width = (self.area.width() - spacing_width) % ncols;
        let leftover_height = (self.area.height() - spacing_height) % nrows;

        let mut top_left = self.area.top_left().ofs(Offset::new(
            col * (cell_width + self.spacing),
            row * (cell_height + self.spacing),
        ));
        // Some previous cells were 1px wider.
        top_left.x += min(leftover_width, col);
        top_left.y += min(leftover_height, row);

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

    pub const fn cell(&self, index: usize) -> Rect {
        self.row_col(index / self.cols, index % self.cols)
    }

    pub const fn cells(&self, cells: GridCellSpan) -> Rect {
        let from = self.row_col(cells.from.0, cells.from.1);
        let to = self.row_col(cells.to.0, cells.to.1);
        from.union(to)
    }
}

#[derive(Copy, Clone)]
pub struct GridCellSpan {
    pub from: (usize, usize),
    pub to: (usize, usize),
}

#[derive(Copy, Clone)]
pub struct LinearPlacement {
    pub axis: Axis,
    pub align: Alignment,
    pub spacing: i16,
}

impl LinearPlacement {
    pub const fn new(axis: Axis) -> Self {
        Self {
            axis,
            align: Alignment::Start,
            spacing: 0,
        }
    }

    pub const fn horizontal() -> Self {
        Self::new(Axis::Horizontal)
    }

    pub const fn vertical() -> Self {
        Self::new(Axis::Vertical)
    }

    pub const fn align_at_start(self) -> Self {
        Self {
            align: Alignment::Start,
            ..self
        }
    }

    pub const fn align_at_center(self) -> Self {
        Self {
            align: Alignment::Center,
            ..self
        }
    }

    pub const fn align_at_end(self) -> Self {
        Self {
            align: Alignment::End,
            ..self
        }
    }

    pub const fn with_spacing(self, spacing: i16) -> Self {
        Self { spacing, ..self }
    }

    /// Arranges all `items` by parameters configured in `self` into `area`.
    /// Does not change the size of the items (only the position).
    pub fn arrange(&self, area: Rect, items: &mut [impl Dimensions]) {
        let size_sum: i16 = items
            .iter_mut()
            .map(|i| i.area().size().axis(self.axis))
            .sum();
        let (mut cursor, spacing) = self.compute_spacing(area, items.len(), size_sum);

        for item in items {
            let item_origin = area.top_left() + Offset::on_axis(self.axis, cursor);
            let item_area = item.area().with_top_left(item_origin);
            item.fit(item_area);
            cursor += item_area.size().axis(self.axis);
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
        let (mut cursor, spacing) = self.compute_spacing(area, count, (count as i16) * item_size);
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

    const fn compute_spacing(&self, area: Rect, count: usize, size_sum: i16) -> (i16, i16) {
        let spacing_count = count.saturating_sub(1);
        let spacing_sum = spacing_count as i16 * self.spacing;
        let naive_size = size_sum + spacing_sum;
        let available_space = area.size().axis(self.axis);

        // scale down spacing to fit everything into area
        let (total_size, spacing) = if naive_size > available_space {
            let scaled_space = (available_space - size_sum) / max(spacing_count as i16, 1);
            // forbid negative spacing
            (available_space, max(scaled_space, 0))
        } else {
            (naive_size, self.spacing)
        };

        let initial_cursor = match self.align {
            Alignment::Start => 0,
            Alignment::Center => available_space / 2 - total_size / 2,
            Alignment::End => available_space - total_size,
        };

        (initial_cursor, spacing)
    }
}

/// Types that can place themselves within area specified by `bounds`.
pub trait Dimensions {
    fn fit(&mut self, bounds: Rect);
    fn area(&self) -> Rect;
}
