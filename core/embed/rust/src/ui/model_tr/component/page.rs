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
    content: Child<T>,
    scrollbar: Child<ScrollBar>,
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
            content: Child::new(content),
            scrollbar: Child::new(ScrollBar::vertical_to_be_filled_later()),
            pad: Pad::with_background(background),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text("CONFIRM")),
            back_btn_details: Some(ButtonDetails::up_arrow_icon_wide()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
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
            content: Child::new(content),
            scrollbar: Child::new(ScrollBar::vertical_to_be_filled_later()),
            pad: Pad::with_background(background),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text("CONFIRM".into())),
            back_btn_details: Some(ButtonDetails::up_arrow_icon_wide()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
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
    /// Change the page in the content, clear the background under it and make
    /// sure it gets completely repainted. Also updating the buttons.
    fn change_page(&mut self, ctx: &mut EventCtx) {
        let active_page = self.scrollbar.inner().active_page;
        self.content.inner_mut().change_page(active_page);
        self.content.request_complete_repaint(ctx);
        self.scrollbar.request_complete_repaint(ctx);
        self.update_buttons(ctx);
        self.pad.clear();
    }

    /// Reflecting the current page in the buttons.
    fn update_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.get_button_layout(
            self.scrollbar.inner().has_previous_page(),
            self.scrollbar.inner().has_next_page(),
        );
        self.buttons.mutate(ctx, |_ctx, buttons| {
            buttons.set(btn_layout);
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
        // Do not pad the button area nor the scrollbar, leave it to them
        self.pad.place(content_area);
        self.content.place(content_area);
        // Need to be called here, only after content is placed
        // and we can calculate the page count
        let page_count = self.content.inner_mut().page_count();
        self.scrollbar.inner_mut().set_page_count(page_count);
        self.scrollbar.place(scrollbar_area);
        self.set_buttons_for_initial_page(page_count);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.scrollbar.inner().page_count);
        let button_event = self.buttons.event(ctx, event);

        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            match pos {
                ButtonPos::Left => {
                    if self.scrollbar.inner().has_previous_page() {
                        // Clicked BACK. Scroll up.
                        self.scrollbar.inner_mut().go_to_previous_page();
                        self.change_page(ctx);
                    } else {
                        // Clicked CANCEL. Send result.
                        return Some(PageMsg::Controls(false));
                    }
                }
                ButtonPos::Right => {
                    if self.scrollbar.inner().has_next_page() {
                        // Clicked NEXT. Scroll down.
                        self.scrollbar.inner_mut().go_to_next_page();
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
        self.scrollbar.paint();
        self.buttons.paint();
    }
}

#[cfg(feature = "ui_debug")]
use super::ButtonAction;
#[cfg(feature = "ui_debug")]
use heapless::String;

#[cfg(feature = "ui_debug")]
impl<S, T> crate::trace::Trace for ButtonPage<S, T>
where
    T: crate::trace::Trace,
    S: AsRef<str>,
{
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => {
                if self.scrollbar.inner().has_previous_page() {
                    ButtonAction::PrevPage.string()
                } else if self.cancel_btn_details.is_some() {
                    ButtonAction::Cancel.string()
                } else {
                    ButtonAction::empty()
                }
            }
            ButtonPos::Right => {
                if self.scrollbar.inner().has_next_page() {
                    ButtonAction::NextPage.string()
                } else if self.confirm_btn_details.is_some() {
                    ButtonAction::Confirm.string()
                } else {
                    ButtonAction::empty()
                }
            }
            ButtonPos::Middle => ButtonAction::empty(),
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ButtonPage");
        t.kw_pair(
            "active_page",
            inttostr!(self.scrollbar.inner().active_page as u8),
        );
        t.kw_pair(
            "page_count",
            inttostr!(self.scrollbar.inner().page_count as u8),
        );
        self.report_btn_actions(t);
        // TODO: it seems the button text is not updated when paginating (but actions
        // above are)
        t.field("buttons", &self.buttons);
        t.field("content", &self.content);
        t.close();
    }
}
