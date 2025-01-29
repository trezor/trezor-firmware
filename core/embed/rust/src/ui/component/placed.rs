use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Alignment, Alignment2D, Axis, Grid, GridCellSpan, Insets, Offset, Rect},
    shape::Renderer,
};

use super::paginated::SinglePage;

pub struct GridPlaced<T> {
    inner: T,
    grid: Grid,
    cells: GridCellSpan,
}

impl<T> GridPlaced<T> {
    pub fn new(inner: T) -> Self {
        Self {
            inner,
            grid: Grid::new(Rect::zero(), 0, 0),
            cells: GridCellSpan {
                from: (0, 0),
                to: (0, 0),
            },
        }
    }

    pub fn with_grid(mut self, rows: usize, cols: usize) -> Self {
        self.grid.rows = rows;
        self.grid.cols = cols;
        self
    }

    pub fn with_spacing(mut self, spacing: i16) -> Self {
        self.grid.spacing = spacing;
        self
    }

    pub fn with_row_col(mut self, row: usize, col: usize) -> Self {
        self.cells.from = (row, col);
        self.cells.to = (row, col);
        self
    }

    pub fn with_from_to(mut self, from: (usize, usize), to: (usize, usize)) -> Self {
        self.cells.from = from;
        self.cells.to = to;
        self
    }
}

impl<T> Component for GridPlaced<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.grid.area = bounds;
        self.inner.place(self.grid.cells(self.cells))
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for GridPlaced<T>
where
    T: Component,
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("GridPlaced");
        t.child("inner", &self.inner);
    }
}

pub struct FixedHeightBar<T> {
    inner: T,
    height: i16,
}

impl<T> FixedHeightBar<T> {
    pub const fn bottom(inner: T, height: i16) -> Self {
        Self { inner, height }
    }
}

impl<T> Component for FixedHeightBar<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (_, bar) = bounds.split_bottom(self.height);
        self.inner.place(bar)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for FixedHeightBar<T>
where
    T: Component,
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FixedHeightBar");
        t.child("inner", &self.inner);
    }
}

pub struct Floating<T> {
    inner: T,
    size: Offset,
    border: Offset,
    align: Alignment2D,
}

impl<T> Floating<T> {
    pub const fn new(size: Offset, border: Offset, align: Alignment2D, inner: T) -> Self {
        Self {
            inner,
            size,
            border,
            align,
        }
    }

    pub const fn top_right(side: i16, border: i16, inner: T) -> Self {
        let size = Offset::uniform(side);
        let border = Offset::uniform(border);
        Self::new(size, border, Alignment2D::TOP_RIGHT, inner)
    }
}

impl<T> Component for Floating<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let mut border = self.border;
        let area = match self.align.0 {
            Alignment::Start => bounds.split_left(self.size.x).0,
            Alignment::Center => fatal_error!("Alignment not supported"),
            Alignment::End => {
                border.x = -border.x;
                bounds.split_right(self.size.x).1
            }
        };
        let area = match self.align.1 {
            Alignment::Start => area.split_top(self.size.y).0,
            Alignment::Center => fatal_error!("Alignment not supported"),
            Alignment::End => {
                border.y = -border.y;
                area.split_bottom(self.size.y).1
            }
        };
        self.inner.place(area.translate(border))
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.inner.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Floating<T>
where
    T: Component,
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Floating");
        t.child("inner", &self.inner);
    }
}

pub struct Split<T, U> {
    first: T,
    second: U,
    axis: Axis,
    size: i16,
    spacing: i16,
}

impl<T, U> Split<T, U> {
    pub const fn new(axis: Axis, size: i16, spacing: i16, first: T, second: U) -> Self {
        Self {
            first,
            second,
            axis,
            size,
            spacing,
        }
    }

    pub const fn left(size: i16, spacing: i16, first: T, second: U) -> Self {
        Self::new(Axis::Vertical, size, spacing, first, second)
    }

    pub const fn right(size: i16, spacing: i16, first: T, second: U) -> Self {
        Self::new(Axis::Vertical, -size, spacing, first, second)
    }

    pub const fn top(size: i16, spacing: i16, first: T, second: U) -> Self {
        Self::new(Axis::Horizontal, size, spacing, first, second)
    }

    pub const fn bottom(size: i16, spacing: i16, first: T, second: U) -> Self {
        Self::new(Axis::Horizontal, -size, spacing, first, second)
    }
}

impl<M, T, U> Component for Split<T, U>
where
    T: Component<Msg = M>,
    U: Component<Msg = M>,
{
    type Msg = M;

    fn place(&mut self, bounds: Rect) -> Rect {
        let size = if self.size == 0 {
            (bounds.size().axis(self.axis.cross()) - self.spacing) / 2
        } else {
            self.size
        };
        let (first, second) = match self.axis {
            Axis::Vertical if size > 0 => bounds.split_left(size),
            Axis::Vertical => bounds.split_right(-size),
            Axis::Horizontal if size > 0 => bounds.split_top(size),
            Axis::Horizontal => bounds.split_bottom(-size),
        };
        let (first, second) = match self.axis {
            Axis::Vertical if size > 0 => (first, second.inset(Insets::left(self.spacing))),
            Axis::Vertical => (first.inset(Insets::right(self.spacing)), second),
            Axis::Horizontal if size > 0 => (first, second.inset(Insets::top(self.spacing))),
            Axis::Horizontal => (first.inset(Insets::bottom(self.spacing)), second),
        };

        self.first.place(first);
        self.second.place(second);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.first
            .event(ctx, event)
            .or_else(|| self.second.event(ctx, event))
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.first.render(target);
        self.second.render(target);
    }
}

impl<T, U> SinglePage for Split<T, U> {}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for Split<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Split");
        t.child("first", &self.first);
        t.child("second", &self.second);
    }
}
