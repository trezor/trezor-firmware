use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    geometry::{Point, Rect},
    model_tr::constant,
};

use super::{common, theme, ButtonController, ButtonControllerMsg, ButtonPos, FlowPage, FlowPages};
use heapless::Vec;

/// To be returned directly from Flow.
pub enum FlowMsg {
    Confirmed,
    Cancelled,
}

// TODO: consider each FlowPage having the ability
// to handle custom actions triggered by some btn.

// TODO: might move FlowButtonAction together with ButtonDetails
// Or at least rename it to `ButtonAction`, so it can be used elsewhere
// Would be nice to use it in `ChoicePage` as well

/// What happens when a button is triggered.
/// Theoretically any action can be connected
/// with any button.
#[derive(Clone, Debug)]
pub enum FlowButtonAction {
    /// Go to the next page of this flow
    NextPage,
    /// Go to the previous page of this flow
    PrevPage,
    /// Go to a page of this flow specified by an index.
    /// Negative numbers can be used to count from the end.
    /// (0 ~ GoToFirstPage, -1 ~ GoToLastPage etc.)
    GoToIndex(i32),
    /// Go forwards/backwards a specified number of pages.
    /// Negative numbers mean going back.
    MovePageRelative(i32),
    /// Cancel the whole flow - send FlowMsg::Cancelled
    Cancel,
    /// Confirm the whole flow - send FlowMsg::Confirmed
    Confirm,
}

/// Storing actions for all three possible buttons.
#[derive(Clone, Debug)]

pub struct BtnActions {
    pub left: Option<FlowButtonAction>,
    pub middle: Option<FlowButtonAction>,
    pub right: Option<FlowButtonAction>,
}

impl BtnActions {
    pub fn new(
        left: Option<FlowButtonAction>,
        middle: Option<FlowButtonAction>,
        right: Option<FlowButtonAction>,
    ) -> Self {
        Self {
            left,
            middle,
            right,
        }
    }

    /// Going back with left, going further with right
    pub fn prev_next() -> Self {
        Self::new(
            Some(FlowButtonAction::PrevPage),
            None,
            Some(FlowButtonAction::NextPage),
        )
    }

    /// Going back with left, going further with middle
    pub fn prev_next_with_middle() -> Self {
        Self::new(
            Some(FlowButtonAction::PrevPage),
            Some(FlowButtonAction::NextPage),
            None,
        )
    }

    /// Going to last page with left, to the next page with right
    pub fn last_next() -> Self {
        Self::new(
            Some(FlowButtonAction::GoToIndex(-1)),
            None,
            Some(FlowButtonAction::NextPage),
        )
    }

    /// Cancelling with left, going to the next page with right
    pub fn cancel_next() -> Self {
        Self::new(
            Some(FlowButtonAction::Cancel),
            None,
            Some(FlowButtonAction::NextPage),
        )
    }

    /// Cancelling with left, confirming with right
    pub fn cancel_confirm() -> Self {
        Self::new(
            Some(FlowButtonAction::Cancel),
            None,
            Some(FlowButtonAction::Confirm),
        )
    }

    /// Going to the beginning with left, confirming with right
    pub fn beginning_confirm() -> Self {
        Self::new(
            Some(FlowButtonAction::GoToIndex(0)),
            None,
            Some(FlowButtonAction::Confirm),
        )
    }

    /// Going to the beginning with left, cancelling with right
    pub fn beginning_cancel() -> Self {
        Self::new(
            Some(FlowButtonAction::GoToIndex(0)),
            None,
            Some(FlowButtonAction::Cancel),
        )
    }

    /// Having access to appropriate action based on the `ButtonPos`
    pub fn get_action(&self, pos: ButtonPos) -> Option<FlowButtonAction> {
        match pos {
            ButtonPos::Left => self.left.clone(),
            ButtonPos::Middle => self.middle.clone(),
            ButtonPos::Right => self.right.clone(),
        }
    }
}

// TODO: should support even paginated FlowPages, when the text
// cannot fit on one page (and when we do not have control over its length)
// This is currently needed for the recipient address verification, as
// the address may, but may not fit on one screen (depends on external input)

pub struct Flow<T, const N: usize> {
    pages: Vec<FlowPages<T>, N>,
    common_title: Option<T>,
    pad: Pad,
    buttons: Child<ButtonController<&'static str>>,
    page_counter: u8,
}

impl<T, const N: usize> Flow<T, N>
where
    T: AsRef<str>,
    T: Clone,
{
    pub fn new(pages: Vec<FlowPages<T>, N>) -> Self {
        let initial_btn_layout = pages[0].btn_layout();

        Self {
            pages,
            common_title: None,
            pad: Pad::with_background(theme::BG),
            buttons: Child::new(ButtonController::new(initial_btn_layout)),
            page_counter: 0,
        }
    }

    /// Adding a common title to all pages. The title will not be colliding
    /// with the page content, as the content will be offset.
    pub fn with_common_title(mut self, title: T) -> Self {
        self.common_title = Some(title);
        self
    }

    /// Rendering the whole page.
    fn paint_page(&mut self) {
        // TODO: print statements uncovered that this is being called
        // also when the button is just pressed, which is wasteful
        // (and also repeatedly when the HTC was being pressed)

        // Painting the current_choice in the biggest area as possible,
        // just accounting for the buttons.
        let mut top_left = Point::zero();
        let bottom_right = Point::new(constant::WIDTH, constant::HEIGHT - theme::BUTTON_HEIGHT);

        // Optionally painting the header.
        // In that case offsetting the current_choice by the height of the header.
        if let Some(title) = &self.common_title {
            top_left.y += common::paint_header(top_left, title, None);
        }
        self.current_choice()
            .paint(Rect::new(top_left, bottom_right));
    }

    /// Setting current buttons and clearing.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.set_buttons(ctx);
        self.clear(ctx);
    }

    /// Clearing the whole area and requesting repaint.
    fn clear(&mut self, ctx: &mut EventCtx) {
        self.pad.clear();
        ctx.request_paint();
    }

    /// Page that is/should be currently on the screen.
    fn current_choice(&mut self) -> &mut FlowPages<T> {
        &mut self.pages[self.page_counter as usize]
    }

    /// Going to the previous page.
    fn go_to_prev_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter -= 1;
        self.update(ctx);
    }

    /// Going to the next page.
    fn go_to_next_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter += 1;
        self.update(ctx);
    }

    /// Going to page by its absolute index.
    /// Negative index means counting from the end.
    fn go_to_page_absolute(&mut self, index: i32, ctx: &mut EventCtx) {
        if index < 0 {
            self.page_counter = (self.pages.len() as i32 + index) as u8;
        } else {
            self.page_counter = index as u8;
        }
        self.update(ctx);
    }

    /// Jumping to another page relative to the current one.
    fn go_to_page_relative(&mut self, jump: i32, ctx: &mut EventCtx) {
        self.page_counter = (self.page_counter as i32 + jump) as u8;
        self.update(ctx);
    }

    /// Updating the visual state of the buttons after each event.
    /// All three buttons are handled based upon the current choice.
    /// If defined in the current choice, setting their text,
    /// whether they are long-pressed, and painting them.
    ///
    /// NOTE: ButtonController is handling the painting, and
    /// it will not repaint the buttons unless some of them changed.
    fn set_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.current_choice().btn_layout();
        self.buttons.mutate(ctx, |ctx, buttons| {
            buttons.set(ctx, btn_layout);
        });
    }
}

impl<T, const N: usize> Component for Flow<T, N>
where
    T: AsRef<str>,
    T: Clone,
{
    type Msg = FlowMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        self.pad.place(content_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let button_event = self.buttons.event(ctx, event);

        // Do something when a button was triggered
        // and we have some action connected with it
        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            let actions = self.current_choice().btn_actions();
            let action = actions.get_action(pos);
            if let Some(action) = action {
                match action {
                    FlowButtonAction::PrevPage => {
                        self.go_to_prev_page(ctx);
                        return None;
                    }
                    FlowButtonAction::NextPage => {
                        self.go_to_next_page(ctx);
                        return None;
                    }
                    FlowButtonAction::GoToIndex(index) => {
                        self.go_to_page_absolute(index, ctx);
                        return None;
                    }
                    FlowButtonAction::MovePageRelative(jump) => {
                        self.go_to_page_relative(jump, ctx);
                        return None;
                    }
                    FlowButtonAction::Cancel => return Some(FlowMsg::Cancelled),
                    FlowButtonAction::Confirm => return Some(FlowMsg::Confirmed),
                }
            }
        };
        None
    }

    fn paint(&mut self) {
        // TODO: might put horizontal scrollbar at the top right
        self.pad.paint();
        self.buttons.paint();
        self.paint_page();
    }
}

#[cfg(feature = "ui_debug")]
impl<T, const N: usize> crate::trace::Trace for Flow<T, N> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Flow");
        t.close();
    }
}
