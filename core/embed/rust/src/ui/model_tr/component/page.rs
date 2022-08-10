use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Pad, PageMsg, Paginate},
        display::Color,
        geometry::{Insets, Rect},
    },
};

use super::{
    theme, ButtonController, ButtonControllerMsg, ButtonDetails, ButtonLayout, ButtonPos, ScrollBar,
};

pub struct ButtonPage<S, T> {
    content: T,
    scrollbar: ScrollBar,
    pad: Pad,
    cancel_btn_details: Option<ButtonDetails<S>>,
    confirm_btn_details: Option<ButtonDetails<S>>,
    back_btn_details: Option<ButtonDetails<S>>,
    next_btn_details: Option<ButtonDetails<S>>,
    buttons: Child<ButtonController<S>>,
}

impl<T> ButtonPage<&'static str, T>
where
    T: Paginate,
    T: Component,
{
    /// Constructor for `&'static str` button-text type.
    pub fn new_str(content: T, background: Color) -> Self {
        Self {
            content,
            scrollbar: ScrollBar::vertical_to_be_filled_later(),
            pad: Pad::with_background(background),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text("CONFIRM")),
            back_btn_details: Some(ButtonDetails::up_arrow_icon_wide()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
        }
    }
}

impl<T> ButtonPage<StrBuffer, T>
where
    T: Paginate,
    T: Component,
{
    /// Constructor for `StrBuffer` button-text type.
    pub fn new_str_buf(content: T, background: Color) -> Self {
        Self {
            content,
            scrollbar: ScrollBar::vertical_to_be_filled_later(),
            pad: Pad::with_background(background),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text("CONFIRM".into())),
            back_btn_details: Some(ButtonDetails::up_arrow_icon_wide()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
        }
    }
}

impl<S, T> ButtonPage<S, T>
where
    T: Paginate,
    T: Component,
    S: AsRef<str>,
    S: Clone,
{
    pub fn with_cancel_btn(mut self, btn_details: Option<ButtonDetails<S>>) -> Self {
        self.cancel_btn_details = btn_details;
        self
    }

    pub fn with_confirm_btn(mut self, btn_details: Option<ButtonDetails<S>>) -> Self {
        self.confirm_btn_details = btn_details;
        self
    }

    pub fn with_back_btn(mut self, btn_details: Option<ButtonDetails<S>>) -> Self {
        self.back_btn_details = btn_details;
        self
    }

    pub fn with_next_btn(mut self, btn_details: Option<ButtonDetails<S>>) -> Self {
        self.next_btn_details = btn_details;
        self
    }

    /// Basically just determining whether the right button for
    /// initial page should be "NEXT" or "CONFIRM".
    /// Can only be called when we know the final page_count.
    fn set_buttons_for_initial_page(&mut self, page_count: usize) {
        let btn_layout = self.get_button_layout(false, page_count > 1);
        self.buttons = Child::new(ButtonController::new(btn_layout));
    }

    /// Called when user pressed "BACK" or "NEXT".
    /// Change the page in the content, clear the background under it and make sure
    /// it gets completely repainted. Also updating the buttons.
    fn change_page(&mut self, ctx: &mut EventCtx, page: usize) {
        self.content.change_page(page);
        self.content.request_complete_repaint(ctx);
        self.update_buttons(ctx);
        self.pad.clear();
    }

    /// Reflecting the current page in the buttons.
    fn update_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.get_button_layout(
            self.scrollbar.has_previous_page(),
            self.scrollbar.has_next_page(),
        );
        self.buttons.mutate(ctx, |ctx, buttons| {
            buttons.set(ctx, btn_layout);
        });
    }

    fn get_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout<S> {
        let btn_left = self.get_left_button_details(has_prev);
        let btn_right = self.get_right_button_details(has_next);
        ButtonLayout::new(btn_left, None, btn_right)
    }

    fn get_left_button_details(&self, has_prev_page: bool) -> Option<ButtonDetails<S>> {
        if has_prev_page {
            self.back_btn_details.clone()
        } else {
            self.cancel_btn_details.clone()
        }
    }

    fn get_right_button_details(&self, has_next_page: bool) -> Option<ButtonDetails<S>> {
        if has_next_page {
            self.next_btn_details.clone()
        } else {
            self.confirm_btn_details.clone()
        }
    }
}

impl<S, T> Component for ButtonPage<S, T>
where
    S: Clone,
    S: AsRef<str>,
    T: Component,
    T: Paginate,
{
    type Msg = PageMsg<T::Msg, bool>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_and_scrollbar_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        let (content_area, scrollbar_area) =
            content_and_scrollbar_area.split_right(ScrollBar::WIDTH);
        let content_area = content_area.inset(Insets::top(1));
        // Do not pad the button area, leave it to `ButtonController`
        self.pad.place(content_and_scrollbar_area);
        self.content.place(content_area);
        // Need to be called here, only after content is placed
        // and we can calculate the page count
        let page_count = self.content.page_count();
        self.scrollbar.set_page_count(page_count);
        self.scrollbar.place(scrollbar_area);
        self.set_buttons_for_initial_page(page_count);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.scrollbar.page_count);
        let button_event = self.buttons.event(ctx, event);

        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            match pos {
                ButtonPos::Left => {
                    if self.scrollbar.has_previous_page() {
                        // Clicked BACK. Scroll up.
                        self.scrollbar.go_to_previous_page();
                        self.change_page(ctx, self.scrollbar.active_page);
                    } else {
                        // Clicked CANCEL. Send result.
                        return Some(PageMsg::Controls(false));
                    }
                }
                ButtonPos::Right => {
                    if self.scrollbar.has_next_page() {
                        // Clicked NEXT. Scroll down.
                        self.scrollbar.go_to_next_page();
                        self.change_page(ctx, self.scrollbar.active_page);
                    } else {
                        // Clicked CONFIRM. Send result.
                        return Some(PageMsg::Controls(true));
                    }
                }
                _ => {}
            }
        }

        if let Some(msg) = self.content.event(ctx, event) {
            return Some(PageMsg::Content(msg));
        }
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.content.paint();
        self.scrollbar.paint();
        self.buttons.paint();
    }
}

#[cfg(feature = "ui_debug")]
impl<S, T> crate::trace::Trace for ButtonPage<S, T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ButtonPage");
        t.field("active_page", &self.scrollbar.active_page);
        t.field("page_count", &self.scrollbar.page_count);
        t.field("content", &self.content);
        t.close();
    }
}
