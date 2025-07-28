use crate::{
    translations::TR,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Pad, PageMsg, Paginate},
        display::Color,
        geometry::{Insets, Rect},
        shape::Renderer,
        util::Pager,
    },
};

use super::{
    constant, theme, ButtonController, ButtonControllerMsg, ButtonDetails, ButtonLayout, ButtonPos,
};

pub struct ButtonPage<T>
where
    T: Component + Paginate,
{
    content: Child<T>,
    pad: Pad,
    cancel_btn_details: Option<ButtonDetails>,
    confirm_btn_details: Option<ButtonDetails>,
    back_btn_details: Option<ButtonDetails>,
    next_btn_details: Option<ButtonDetails>,
    buttons: Child<ButtonController>,
}

impl<T> ButtonPage<T>
where
    T: Component + Paginate,
{
    pub fn new(content: T, background: Color) -> Self {
        Self {
            content: Child::new(content),
            pad: Pad::with_background(background).with_clear(),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text(TR::buttons__confirm.into())),
            back_btn_details: Some(ButtonDetails::up_arrow_icon()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
        }
    }

    pub fn with_cancel_btn(mut self, btn_details: Option<ButtonDetails>) -> Self {
        self.cancel_btn_details = btn_details;
        self
    }

    pub fn with_confirm_btn(mut self, btn_details: Option<ButtonDetails>) -> Self {
        self.confirm_btn_details = btn_details;
        self
    }

    pub fn with_back_btn(mut self, btn_details: Option<ButtonDetails>) -> Self {
        self.back_btn_details = btn_details;
        self
    }

    pub fn with_next_btn(mut self, btn_details: Option<ButtonDetails>) -> Self {
        self.next_btn_details = btn_details;
        self
    }

    /// Basically just determining whether the right button for
    /// initial page should be "NEXT" or "CONFIRM".
    /// Can only be called when we know the final page_count.
    fn set_buttons_for_initial_page(&mut self, page_count: u16) {
        let btn_layout = self.get_button_layout(false, page_count > 1);
        self.buttons = Child::new(ButtonController::new(btn_layout));
    }

    /// Called when user pressed "BACK" or "NEXT".
    /// Change the page in the content, clear the background under it and make
    /// sure it gets completely repainted. Also updating the buttons.
    fn change_page(&mut self, ctx: &mut EventCtx) {
        let curr_page = self.pager().current();
        self.content.mutate(ctx, |ctx, content| {
            content.change_page(curr_page);
            content.request_complete_repaint(ctx);
        });
        self.update_buttons(ctx);
        self.pad.clear();
    }

    /// Reflecting the current page in the buttons.
    fn update_buttons(&mut self, ctx: &mut EventCtx) {
        let pager = self.pager();
        let btn_layout = self.get_button_layout(pager.has_prev(), pager.has_next());
        self.buttons.mutate(ctx, |_ctx, buttons| {
            buttons.set(btn_layout);
        });
    }

    fn get_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout {
        let btn_left = self.get_left_button_details(!has_prev);
        let btn_right = self.get_right_button_details(has_next);
        ButtonLayout::new(btn_left, None, btn_right)
    }

    fn get_left_button_details(&self, is_first: bool) -> Option<ButtonDetails> {
        if is_first {
            self.cancel_btn_details.clone()
        } else {
            self.back_btn_details.clone()
        }
    }

    fn get_right_button_details(&self, has_next_page: bool) -> Option<ButtonDetails> {
        if has_next_page {
            self.next_btn_details.clone()
        } else {
            self.confirm_btn_details.clone()
        }
    }
}

impl<T> Paginate for ButtonPage<T>
where
    T: Component + Paginate,
{
    fn pager(&self) -> Pager {
        self.content.pager()
    }

    fn change_page(&mut self, active_page: u16) {
        self.content.change_page(active_page);
    }
}

impl<T> Component for ButtonPage<T>
where
    T: Component + Paginate,
{
    type Msg = PageMsg<T::Msg>;

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
        self.set_buttons_for_initial_page(self.content.pager().total());
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.pager().total());
        if let Some(ButtonControllerMsg::Triggered(pos, _)) = self.buttons.event(ctx, event) {
            match pos {
                ButtonPos::Left => {
                    if self.pager().has_prev() {
                        // Clicked BACK. Scroll up.
                        self.prev_page();
                        self.change_page(ctx);
                    } else if self.cancel_btn_details.is_some() {
                        // Clicked CANCEL. Send result.
                        return Some(PageMsg::Cancelled);
                    } else {
                        return None;
                    }
                }
                ButtonPos::Right => {
                    if self.pager().has_next() {
                        // Clicked NEXT. Scroll down.
                        self.next_page();
                        self.change_page(ctx);
                    } else {
                        // Clicked CONFIRM. Send result.
                        return Some(PageMsg::Confirmed);
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        self.content.render(target);
        self.buttons.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ButtonPage<T>
where
    T: crate::trace::Trace + Paginate + Component,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ButtonPage");
        t.int("active_page", self.pager().current() as i64);
        t.int("page_count", self.pager().total() as i64);
        t.child("buttons", &self.buttons);
        t.child("content", &self.content);
    }
}
