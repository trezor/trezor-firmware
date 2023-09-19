use crate::{
    strutil::StringType,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Pad, PageMsg, Paginate},
        display::Color,
        geometry::{Insets, Rect},
    },
};

use super::{
    constant, frame::ScrollableContent, theme, ButtonController, ButtonControllerMsg,
    ButtonDetails, ButtonLayout, ButtonPos,
};

pub struct ButtonPage<T, U>
where
    T: Component + Paginate,
    U: StringType,
{
    page_count: usize,
    active_page: usize,
    content: Child<T>,
    pad: Pad,
    /// Left button of the first screen
    cancel_btn_details: Option<ButtonDetails<U>>,
    /// Right button of the last screen
    confirm_btn_details: Option<ButtonDetails<U>>,
    /// Left button of every screen
    back_btn_details: Option<ButtonDetails<U>>,
    /// Right button of every screen apart the last one
    next_btn_details: Option<ButtonDetails<U>>,
    buttons: Child<ButtonController<U>>,
}

impl<T, U> ButtonPage<T, U>
where
    T: Component + Paginate,
    U: StringType + Clone,
{
    pub fn new(content: T, background: Color) -> Self {
        Self {
            page_count: 0, // will be set in place()
            active_page: 0,
            content: Child::new(content),
            pad: Pad::with_background(background).with_clear(),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text("CONFIRM".into())),
            back_btn_details: Some(ButtonDetails::up_arrow_icon()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
        }
    }

    pub fn with_cancel_btn(mut self, btn_details: Option<ButtonDetails<U>>) -> Self {
        self.cancel_btn_details = btn_details;
        self
    }

    pub fn with_confirm_btn(mut self, btn_details: Option<ButtonDetails<U>>) -> Self {
        self.confirm_btn_details = btn_details;
        self
    }

    pub fn with_back_btn(mut self, btn_details: Option<ButtonDetails<U>>) -> Self {
        self.back_btn_details = btn_details;
        self
    }

    pub fn with_next_btn(mut self, btn_details: Option<ButtonDetails<U>>) -> Self {
        self.next_btn_details = btn_details;
        self
    }

    pub fn has_next_page(&self) -> bool {
        self.active_page < self.page_count - 1
    }

    pub fn has_previous_page(&self) -> bool {
        self.active_page > 0
    }

    pub fn go_to_next_page(&mut self) {
        self.active_page = self.active_page.saturating_add(1).min(self.page_count - 1);
    }

    pub fn go_to_previous_page(&mut self) {
        self.active_page = self.active_page.saturating_sub(1);
    }

    /// Basically just determining whether the right button for
    /// initial page should be "NEXT" or "CONFIRM".
    /// Can only be called when we know the final page_count.
    fn set_buttons_for_initial_page(&mut self, page_count: usize) {
        let btn_layout = self.get_button_layout(false, page_count > 1);
        self.buttons = Child::new(ButtonController::new(btn_layout));
    }

    /// Called when user pressed "BACK" or "NEXT".
    /// Change the page in the content, clear the background under it and make
    /// sure it gets completely repainted. Also updating the buttons.
    fn change_page(&mut self, ctx: &mut EventCtx) {
        self.content.mutate(ctx, |ctx, content| {
            content.change_page(self.active_page);
            content.request_complete_repaint(ctx);
        });
        self.update_buttons(ctx);
        self.pad.clear();
    }

    /// Reflecting the current page in the buttons.
    fn update_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.get_button_layout(self.has_previous_page(), self.has_next_page());
        self.buttons.mutate(ctx, |_ctx, buttons| {
            buttons.set(btn_layout);
        });
    }

    fn get_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout<U> {
        let btn_left = self.get_left_button_details(!has_prev);
        let btn_right = self.get_right_button_details(has_next);
        ButtonLayout::new(btn_left, None, btn_right)
    }

    /// Get the left button details, depending whether the page is first or not.
    fn get_left_button_details(&self, is_first: bool) -> Option<ButtonDetails<U>> {
        if is_first {
            self.cancel_btn_details.clone()
        } else {
            self.back_btn_details.clone()
        }
    }

    /// Get the right button details, depending on whether there is a next
    /// page.
    fn get_right_button_details(&self, has_next_page: bool) -> Option<ButtonDetails<U>> {
        if has_next_page {
            self.next_btn_details.clone()
        } else {
            self.confirm_btn_details.clone()
        }
    }
}

impl<T, U> ScrollableContent for ButtonPage<T, U>
where
    T: Component + Paginate,
    U: StringType,
{
    fn page_count(&self) -> usize {
        self.page_count
    }
    fn active_page(&self) -> usize {
        self.active_page
    }
}

impl<T, U> Component for ButtonPage<T, U>
where
    T: Component + Paginate,
    U: StringType + Clone,
{
    type Msg = PageMsg<T::Msg, bool>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        // Pad only the content, buttons handle it themselves.
        self.pad.place(content_area);
        // Moving the content LINE_SPACE pixels down, otherwise the top would not be
        // padded correctly
        self.content
            .place(content_area.inset(Insets::top(constant::LINE_SPACE)));
        // Need to be called here, only after content is placed
        // and we can calculate the page count.
        self.page_count = self.content.page_count();
        self.set_buttons_for_initial_page(self.page_count);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.page_count());
        if let Some(ButtonControllerMsg::Triggered(pos, _)) = self.buttons.event(ctx, event) {
            match pos {
                ButtonPos::Left => {
                    if self.has_previous_page() {
                        // Clicked BACK. Scroll up.
                        self.go_to_previous_page();
                        self.change_page(ctx);
                    } else {
                        // Clicked CANCEL. Send result.
                        return Some(PageMsg::Controls(false));
                    }
                }
                ButtonPos::Right => {
                    if self.has_next_page() {
                        // Clicked NEXT. Scroll down.
                        self.go_to_next_page();
                        self.change_page(ctx);
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
        self.buttons.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for ButtonPage<T, U>
where
    T: crate::trace::Trace + Paginate + Component,
    U: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ButtonPage");
        t.int("active_page", self.active_page as i64);
        t.int("page_count", self.page_count as i64);
        t.child("buttons", &self.buttons);
        t.child("content", &self.content);
    }
}
