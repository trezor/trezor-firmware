use crate::ui::{
    component::{base::Component, FormattedText, Paginate},
    geometry::Rect,
};

use super::{flow::BtnActions, ButtonDetails, ButtonLayout};

pub trait FlowPage {
    fn paint(&mut self);
    fn place(&mut self, bounds: Rect) -> Rect;
    fn btn_layout(&self) -> ButtonLayout<&'static str>;
    fn btn_actions(&self) -> BtnActions;
    fn has_prev_page(&self) -> bool;
    fn has_next_page(&self) -> bool;
    fn go_to_prev_page(&mut self);
    fn go_to_next_page(&mut self);
}

// TODO: consider using `dyn` instead of `enum` to allow
// for more components implementing `FlowPage`
// Alloc screen by GC .. gc alloc, new
// dyn... gc dyn obj component
// Vec<Gc<dyn FlowPage>, 2>...

#[derive(Clone)]
pub enum FlowPages<T> {
    // NOTE / TODO: this FormattedText here as the only
    // component was an experiment to use it as one-for-all
    // component, when users would only supply a specific
    // `format` string together with some arguments fitting
    // into that format/template.
    // Issue that this uncovers is mostly the inability to
    // easily draw/do a certain sequence of steps on the screen,
    // with all the features like supporting pagination,
    // handling line ends, dynamic placement into a certain
    // area etc.
    // One part is also the difficulty of supporting a sequence
    // of general components implementing `FlowPage` in `Flow`.
    FormattedText(FormattedTextPage<T>),
}

impl<T> FlowPage for FlowPages<T>
where
    T: AsRef<str>,
    T: Clone,
{
    fn paint(&mut self) {
        match self {
            FlowPages::FormattedText(item) => item.paint(),
        }
    }

    fn place(&mut self, bounds: Rect) -> Rect {
        match self {
            FlowPages::FormattedText(item) => item.place(bounds),
        }
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        match self {
            FlowPages::FormattedText(item) => item.btn_layout(),
        }
    }

    fn btn_actions(&self) -> BtnActions {
        match self {
            FlowPages::FormattedText(item) => item.btn_actions(),
        }
    }

    fn has_prev_page(&self) -> bool {
        match self {
            FlowPages::FormattedText(item) => item.has_prev_page(),
        }
    }

    fn has_next_page(&self) -> bool {
        match self {
            FlowPages::FormattedText(item) => item.has_next_page(),
        }
    }

    fn go_to_prev_page(&mut self) {
        match self {
            FlowPages::FormattedText(item) => item.go_to_prev_page(),
        }
    }

    fn go_to_next_page(&mut self) {
        match self {
            FlowPages::FormattedText(item) => item.go_to_next_page(),
        }
    }
}

/// Page displaying recipient address.
#[derive(Clone)]
pub struct FormattedTextPage<T> {
    text: FormattedText<&'static str, T>,
    btn_layout: ButtonLayout<&'static str>,
    btn_actions: BtnActions,
    current_page: usize,
    page_count: usize,
}

impl<T> FormattedTextPage<T>
where
    T: AsRef<str>,
{
    pub fn new(
        text: FormattedText<&'static str, T>,
        btn_layout: ButtonLayout<&'static str>,
        btn_actions: BtnActions,
    ) -> Self {
        Self {
            text,
            btn_layout,
            btn_actions,
            current_page: 0,
            page_count: 1,
        }
    }
}

impl<T> FlowPage for FormattedTextPage<T>
where
    T: AsRef<str>,
{
    fn paint(&mut self) {
        self.text.change_page(self.current_page);
        self.text.paint();
    }

    fn btn_layout(&self) -> ButtonLayout<&'static str> {
        // When we are in pagination inside this flow,
        // show the up and down arrows on appropriate sides
        let current = self.btn_layout.clone();

        let btn_left = if self.has_prev_page() {
            Some(ButtonDetails::up_arrow_icon_wide("arr_up"))
        } else {
            current.btn_left
        };
        let btn_right = if self.has_next_page() {
            Some(ButtonDetails::down_arrow_icon_wide("arr_down"))
        } else {
            current.btn_right
        };

        ButtonLayout::new(btn_left, current.btn_middle, btn_right)
    }

    fn place(&mut self, bounds: Rect) -> Rect {
        self.text.place(bounds);
        self.page_count = self.text.page_count();
        bounds
    }

    fn btn_actions(&self) -> BtnActions {
        self.btn_actions.clone()
    }

    fn has_prev_page(&self) -> bool {
        self.current_page > 0
    }

    fn has_next_page(&self) -> bool {
        self.current_page < self.page_count - 1
    }

    fn go_to_prev_page(&mut self) {
        self.current_page -= 1;
    }

    fn go_to_next_page(&mut self) {
        self.current_page += 1;
    }
}
