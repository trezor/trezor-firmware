use crate::ui::{
    component::{Component, Event, EventCtx},
    geometry::{Grid, GridCellSpan, Rect},
};

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

    fn paint(&mut self) {
        self.inner.paint()
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for GridPlaced<T>
where
    T: Component,
    T: crate::trace::Trace,
{
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("GridPlaced");
        d.field("inner", &self.inner);
        d.close();
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

    fn paint(&mut self) {
        self.inner.paint()
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for FixedHeightBar<T>
where
    T: Component,
    T: crate::trace::Trace,
{
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("FixedHeightBar");
        d.field("inner", &self.inner);
        d.close();
    }
}
