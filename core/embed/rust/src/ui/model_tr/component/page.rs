use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Pad, PageMsg, Paginate},
    display::Color,
    geometry::{Insets, Rect},
};

use super::{
    theme, ButtonController, ButtonControllerMsg, ButtonDetails, ButtonLayout, ButtonPos, ScrollBar,
};

pub struct ButtonPage<T> {
    content: Child<T>,
    scrollbar: Child<ScrollBar>,
    /// Optional available area for scrollbar defined by parent component.
    parent_scrollbar_area: Option<Rect>,
    pad: Pad,
    /// Left button of the first screen
    cancel_btn_details: Option<ButtonDetails>,
    /// Right button of the last screen
    confirm_btn_details: Option<ButtonDetails>,
    /// Left button of the last page
    last_back_btn_details: Option<ButtonDetails>,
    /// Left button of every screen in the middle
    back_btn_details: Option<ButtonDetails>,
    /// Right button of every screen apart the last one
    next_btn_details: Option<ButtonDetails>,
    buttons: Child<ButtonController>,
    /// Scrollbar may or may not be shown (but will be counting pages anyway).
    show_scrollbar: bool,
}

impl<T> ButtonPage<T>
where
    T: Component + Paginate,
{
    pub fn new(content: T, background: Color) -> Self {
        Self {
            content: Child::new(content),
            scrollbar: Child::new(ScrollBar::to_be_filled_later()),
            parent_scrollbar_area: None,
            pad: Pad::with_background(background).with_clear(),
            cancel_btn_details: Some(ButtonDetails::cancel_icon()),
            confirm_btn_details: Some(ButtonDetails::text("CONFIRM".into())),
            back_btn_details: Some(ButtonDetails::up_arrow_icon_wide()),
            last_back_btn_details: Some(ButtonDetails::up_arrow_icon()),
            next_btn_details: Some(ButtonDetails::down_arrow_icon_wide()),
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
            show_scrollbar: true,
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

    pub fn with_scrollbar(mut self, show: bool) -> Self {
        self.show_scrollbar = show;
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

    fn get_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout {
        let btn_left = self.get_left_button_details(!has_prev, !has_next);
        let btn_right = self.get_right_button_details(has_next);
        ButtonLayout::new(btn_left, None, btn_right)
    }

    /// Get the let button details, depending whether the page is first, last,
    /// or in the middle.
    fn get_left_button_details(&self, is_first: bool, is_last: bool) -> Option<ButtonDetails> {
        if is_first {
            self.cancel_btn_details.clone()
        } else if is_last {
            self.last_back_btn_details.clone()
        } else {
            self.back_btn_details.clone()
        }
    }

    /// Get the right button details, depending on whether there is a next
    /// page.
    fn get_right_button_details(&self, has_next_page: bool) -> Option<ButtonDetails> {
        if has_next_page {
            self.next_btn_details.clone()
        } else {
            self.confirm_btn_details.clone()
        }
    }
}

impl<T> Component for ButtonPage<T>
where
    T: Component + Paginate,
{
    type Msg = PageMsg<T::Msg, bool>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        let content_area = content_area.inset(Insets::top(1));
        // Do not pad the button area nor the scrollbar, leave it to them.
        self.pad.place(content_area);
        self.content.place(content_area);
        // Need to be called here, only after content is placed
        // and we can calculate the page count.
        let page_count = self.content.inner_mut().page_count();
        self.scrollbar.inner_mut().set_page_count(page_count);
        self.set_buttons_for_initial_page(page_count);

        // Placing the scrollbar when requested.
        // Put it into its dedicated area when parent component already chose it,
        // otherwise place it into the right top of the content.
        if self.show_scrollbar {
            let scrollbar_area = self.parent_scrollbar_area.unwrap_or(content_area);
            self.scrollbar.place(scrollbar_area);
        }

        self.buttons.place(button_area);
        bounds
    }

    fn set_scrollbar_area(&mut self, area: Rect) {
        self.parent_scrollbar_area = Some(area);
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
        if self.show_scrollbar {
            self.scrollbar.paint();
        }
        self.buttons.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
use super::ButtonAction;
#[cfg(feature = "ui_debug")]
use heapless::String;

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ButtonPage<T>
where
    T: crate::trace::Trace,
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
