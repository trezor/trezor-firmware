use crate::{
    translations::TR,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Pad, PageMsg, Paginate},
        display::{Color, Font},
        geometry::{Insets, Rect},
        shape::Renderer,
    },
};

use super::{
    constant, frame::ScrollableContent, theme, ButtonController, ButtonControllerMsg,
    ButtonDetails, ButtonLayout, ButtonPos,
};

#[derive(PartialEq)]
enum LastPageLayout {
    Confirm,
    ArmedConfirmPlusInfo,
}

pub struct ButtonPage<T>
where
    T: Component + Paginate,
{
    page_count: usize,
    active_page: usize,
    page_limit: Option<usize>,
    last_page_layout: LastPageLayout,
    content: Child<T>,
    pad: Pad,
    cancel_btn_details: Option<ButtonDetails>,
    confirm_btn_details: Option<ButtonDetails>,
    info_btn_details: Option<ButtonDetails>,
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
            page_count: 0, // will be set in place()
            active_page: 0,
            page_limit: None,
            last_page_layout: LastPageLayout::Confirm,
            content: Child::new(content),
            pad: Pad::with_background(background).with_clear(),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text(TR::buttons__confirm.into())),
            info_btn_details: Some(
                ButtonDetails::text("i".into())
                    .with_fixed_width(theme::BUTTON_ICON_WIDTH)
                    .with_font(Font::NORMAL),
            ),
            back_btn_details: Some(ButtonDetails::up_arrow_icon()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
        }
    }

    pub fn with_armed_confirm_plus_info(mut self) -> Self {
        self.last_page_layout = LastPageLayout::ArmedConfirmPlusInfo;
        self.confirm_btn_details = Some(ButtonDetails::armed_text(TR::words__confirm.into()));
        self
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

    pub fn with_page_limit(mut self, page_limit: Option<usize>) -> Self {
        self.page_limit = page_limit;
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

    fn get_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout {
        let btn_left = self.get_left_button_details(!has_prev);
        let btn_middle = self.get_middle_button_details(has_next);
        let btn_right = self.get_right_button_details(has_next);
        ButtonLayout::new(btn_left, btn_middle, btn_right)
    }

    fn get_left_button_details(&self, is_first: bool) -> Option<ButtonDetails> {
        if is_first {
            self.cancel_btn_details.clone()
        } else {
            self.back_btn_details.clone()
        }
    }

    fn get_middle_button_details(&self, has_next_page: bool) -> Option<ButtonDetails> {
        if has_next_page || self.last_page_layout == LastPageLayout::Confirm {
            None
        } else {
            self.confirm_btn_details.clone()
        }
    }

    fn get_right_button_details(&self, has_next_page: bool) -> Option<ButtonDetails> {
        if has_next_page {
            self.next_btn_details.clone()
        } else if self.last_page_layout == LastPageLayout::Confirm {
            self.confirm_btn_details.clone()
        } else {
            self.info_btn_details.clone()
        }
    }
}

impl<T> ScrollableContent for ButtonPage<T>
where
    T: Component + Paginate,
{
    fn page_count(&self) -> usize {
        self.page_count
    }
    fn active_page(&self) -> usize {
        self.active_page
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
        self.page_count = self.content.page_count();
        if let Some(limit) = self.page_limit {
            self.page_count = self.page_count.min(limit);
        }

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
                        return Some(PageMsg::Cancelled);
                    }
                }
                ButtonPos::Middle => {
                    return Some(PageMsg::Confirmed);
                }
                ButtonPos::Right => {
                    if self.has_next_page() {
                        // Clicked NEXT. Scroll down.
                        self.go_to_next_page();
                        self.change_page(ctx);
                    } else {
                        match self.last_page_layout {
                            LastPageLayout::Confirm => {
                                return Some(PageMsg::Confirmed);
                            }
                            LastPageLayout::ArmedConfirmPlusInfo => {
                                return Some(PageMsg::Info);
                            }
                        }
                    }
                }
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
        t.int("active_page", self.active_page as i64);
        t.int("page_count", self.page_count as i64);
        t.child("buttons", &self.buttons);
        t.child("content", &self.content);
    }
}
