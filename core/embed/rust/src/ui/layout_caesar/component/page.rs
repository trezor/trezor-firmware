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

/// Which action the left slot performs in the external-menu ("action bar")
/// navigation mode.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum ExternalMenuLeft {
    /// Left slot is a hamburger icon; short press returns `PageMsg::Info`.
    Menu,
}

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
    has_menu: bool,
    /// When set, the page uses the action-bar navigation: the left button opens
    /// a menu (or closes the screen) on short press and acts as a "Shift"
    /// modifier when held. Opt-in; `None` keeps the classic behavior.
    external_nav: Option<ExternalMenuLeft>,
    /// Whether the left "Shift" is currently being held (action-bar mode only).
    shift_active: bool,
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
            has_menu: false,
            external_nav: None,
            shift_active: false,
            // Setting empty layout for now, we do not yet know the page count.
            // Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
        }
    }

    /// Enable the action-bar navigation with the given left-slot behavior.
    pub fn with_external_menu_nav(mut self, left: ExternalMenuLeft) -> Self {
        self.external_nav = Some(left);
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

    pub fn with_menu(mut self, has_menu: bool) -> Self {
        self.has_menu = has_menu;
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
        let mut controller = ButtonController::new(btn_layout);
        if self.external_nav.is_some() {
            // Holding the left button acts as a "Shift" modifier in nav mode.
            controller = controller.with_left_shift();
        }
        self.buttons = Child::new(controller);
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
        self.buttons.mutate(ctx, |ctx, buttons| {
            buttons.set(btn_layout);
            // Changing the button layout only clears the internal pad; force a
            // full repaint so any leftover "pressed"/highlight pixels (e.g. from
            // holding the left button before entering Shift) are cleared.
            buttons.request_complete_repaint(ctx);
        });
    }

    fn get_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout {
        if self.external_nav.is_some() {
            return self.get_nav_button_layout(has_prev, has_next);
        }
        let btn_left = if !has_prev {
            self.cancel_btn_details.clone()
        } else {
            self.back_btn_details.clone()
        };
        let (btn_middle, btn_right) = match (has_next, self.has_menu) {
            (true, _) => (None, self.next_btn_details.clone()),
            (false, false) => (None, self.confirm_btn_details.clone()),
            (false, true) => (
                self.confirm_btn_details.clone().map(|b| b.with_arms()),
                Some(ButtonDetails::info_icon()),
            ),
        };
        ButtonLayout::new(btn_left, btn_middle, btn_right)
    }

    /// Button layout for the action-bar navigation mode.
    fn get_nav_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout {
        if self.shift_active {
            // While "Shift" is held: left = filled "Shift" label, right = the
            // secondary "back" (scroll up) button if there is a previous page.
            let btn_right = has_prev.then(ButtonDetails::back_secondary_icon);
            return ButtonLayout::new(Some(ButtonDetails::shift_text()), None, btn_right);
        }

        // Show the menu icon wrapped in parentheses only when a secondary
        // ("Shift") action is available, i.e. there is a previous page to
        // scroll back to. On the first page there is no secondary action, so
        // the plain menu icon is used and the long press does nothing.
        let btn_left = Some(if has_prev {
            ButtonDetails::menu_shift_icon()
        } else {
            ButtonDetails::menu_icon()
        });
        let btn_right = if has_next {
            // Wide down arrow to scroll to the next page.
            Some(ButtonDetails::down_arrow_icon_wide())
        } else if let Some(confirm) = self.confirm_btn_details.clone() {
            // Last page with a configured confirm action.
            confirm.into()
        } else {
            // Last page with no confirm action: wide up arrow acts as "close".
            Some(ButtonDetails::up_arrow_icon_wide())
        };
        ButtonLayout::new(btn_left, None, btn_right)
    }

    /// Event handling for the action-bar navigation mode.
    fn event_nav(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
        external_nav: ExternalMenuLeft,
    ) -> Option<PageMsg<T::Msg>> {
        if let Some(msg) = self.buttons.event(ctx, event) {
            match msg {
                // Long press of the left button (~1s) engages "Shift" mode:
                // swap to the shift layout and highlight the right (secondary)
                // button. A plain press-down does NOT enter shift anymore.
                ButtonControllerMsg::LongPressed(ButtonPos::Left) => {
                    self.shift_active = true;
                    self.update_buttons(ctx);
                    self.buttons.mutate(ctx, |ctx, buttons| {
                        // Keep the "Shift" label filled while it is held.
                        buttons.highlight_button(ctx, ButtonPos::Left);
                    });
                }
                // Leaving shift mode: restore the normal layout.
                ButtonControllerMsg::ShiftReleased => {
                    self.shift_active = false;
                    self.update_buttons(ctx);
                }
                // Left button released.
                ButtonControllerMsg::Triggered(ButtonPos::Left, _) => {
                    if self.shift_active {
                        // Was a long press (shift shown): releasing just returns
                        // to the default layout and does NOT open the menu.
                        self.shift_active = false;
                        self.update_buttons(ctx);
                    } else {
                        // Short press: open the menu / close the screen.
                        return Some(match external_nav {
                            ExternalMenuLeft::Menu => PageMsg::Info,
                        });
                    }
                }
                // Secondary action (right pressed while Shift held): scroll up.
                ButtonControllerMsg::ShiftedTriggered(ButtonPos::Right) => {
                    if self.pager().has_prev() {
                        self.prev_page();
                        self.change_page(ctx);
                    }
                    // Shift is still held; keep the "Shift" label filled.
                    self.buttons.mutate(ctx, |ctx, buttons| {
                        buttons.highlight_button(ctx, ButtonPos::Left);
                    });
                }
                // Primary action: next page, or confirm/close on the last page.
                ButtonControllerMsg::Triggered(ButtonPos::Right, _) => {
                    if self.pager().has_next() {
                        self.next_page();
                        self.change_page(ctx);
                    } else if self.confirm_btn_details.is_some() {
                        return Some(PageMsg::Confirmed);
                    } else {
                        return Some(PageMsg::Cancelled);
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
        if let Some(external_nav) = self.external_nav {
            return self.event_nav(ctx, event, external_nav);
        }
        if let Some(ButtonControllerMsg::Triggered(pos, _)) = self.buttons.event(ctx, event) {
            match pos {
                ButtonPos::Left => {
                    if self.pager().has_prev() {
                        // Clicked BACK. Scroll up.
                        self.prev_page();
                        self.change_page(ctx);
                    } else {
                        // First page — left slot can only be the cancel button
                        // (otherwise the layout would not have rendered it and
                        // no Triggered would arrive here).
                        return Some(PageMsg::Cancelled);
                    }
                }
                ButtonPos::Middle => {
                    return Some(PageMsg::Confirmed);
                }
                ButtonPos::Right => {
                    if self.pager().has_next() {
                        // Clicked NEXT. Scroll down.
                        self.next_page();
                        self.change_page(ctx);
                    } else if self.has_menu {
                        return Some(PageMsg::Info);
                    } else {
                        return Some(PageMsg::Confirmed);
                    }
                }
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
        // In the action-bar Menu mode the menu is reachable from every page.
        let has_menu = matches!(self.external_nav, Some(ExternalMenuLeft::Menu))
            || (self.has_menu && self.pager().is_last());
        t.bool("has_menu", has_menu);
        t.bool("external_menu", self.external_nav.is_some());
    }
}
