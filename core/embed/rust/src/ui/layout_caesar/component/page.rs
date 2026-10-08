use super::{
    constant, theme, ButtonController, ButtonControllerMsg, ButtonDetails, ButtonLayout, ButtonPos,
};
use crate::translations::TR;
use crate::ui::component::{
    Child, Component, ComponentExt, Event, EventCtx, Pad, PageMsg, Paginate,
};
use crate::ui::display::Color;
use crate::ui::geometry::{Insets, Rect};
use crate::ui::shape::Renderer;
use crate::ui::util::Pager;

/// What the left button does in the menu navigation (see
/// `ButtonPage::with_menu_nav`).
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum MenuNav {
    /// Opens the context menu - the screen returns `PageMsg::Info`.
    Menu,
    /// Closes the screen, e.g. the one opened from a context menu - the screen
    /// returns `PageMsg::Cancelled`.
    Close,
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
    /// Menu navigation, replacing the cancel/back/next buttons.
    menu_nav: Option<MenuNav>,
    /// Whether the left button is being held as "Shift" (menu navigation only).
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
            menu_nav: None,
            shift_active: false,
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

    pub fn with_menu(mut self, has_menu: bool) -> Self {
        self.has_menu = has_menu;
        self
    }

    /// Navigation with the left button opening a context menu (or closing the
    /// screen), and the right button scrolling down and finally confirming
    /// (when there is a confirm button).
    ///
    /// Holding the left button on any but the first page engages "Shift", and
    /// the right button then scrolls up.
    pub fn with_menu_nav(mut self, menu_nav: MenuNav) -> Self {
        self.menu_nav = Some(menu_nav);
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
        let shift_active = self.shift_active;
        self.buttons.mutate(ctx, |ctx, buttons| {
            buttons.set(btn_layout);
            if shift_active {
                // The new left button is still being held.
                buttons.refresh_pressed(ctx);
            }
        });
    }

    fn get_button_layout(&self, has_prev: bool, has_next: bool) -> ButtonLayout {
        if let Some(menu_nav) = self.menu_nav {
            return self.get_menu_nav_button_layout(menu_nav, has_prev, has_next);
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

    fn get_menu_nav_button_layout(
        &self,
        menu_nav: MenuNav,
        has_prev: bool,
        has_next: bool,
    ) -> ButtonLayout {
        // The bracketed left icon advertises "Shift", which is offered only when
        // there is somewhere to scroll up to. It stays while "Shift" is held.
        let shift = has_prev || self.shift_active;
        let btn_left = match (menu_nav, shift) {
            (MenuNav::Menu, false) => ButtonDetails::menu_icon(),
            (MenuNav::Menu, true) => ButtonDetails::menu_shift_icon(),
            (MenuNav::Close, false) => ButtonDetails::close_icon(),
            (MenuNav::Close, true) => ButtonDetails::close_shift_icon(),
        };
        let btn_right = if self.shift_active {
            has_prev.then(ButtonDetails::scroll_up_wide)
        } else if has_next {
            Some(ButtonDetails::scroll_down_wide())
        } else {
            self.confirm_btn_details.clone()
        };
        ButtonLayout::new(Some(btn_left), None, btn_right)
    }

    fn event_menu_nav(
        &mut self,
        ctx: &mut EventCtx,
        event: Event,
        menu_nav: MenuNav,
    ) -> Option<PageMsg<T::Msg>> {
        match self.buttons.event(ctx, event) {
            Some(ButtonControllerMsg::Triggered(ButtonPos::Left, _)) => {
                return Some(match menu_nav {
                    MenuNav::Menu => PageMsg::Info,
                    MenuNav::Close => PageMsg::Cancelled,
                });
            }
            Some(ButtonControllerMsg::Triggered(ButtonPos::Right, _)) => {
                if self.pager().has_next() {
                    self.next_page();
                    self.change_page(ctx);
                } else {
                    return Some(PageMsg::Confirmed);
                }
            }
            Some(ButtonControllerMsg::ShiftStarted) => {
                self.shift_active = true;
                self.update_buttons(ctx);
            }
            Some(ButtonControllerMsg::ShiftedTriggered) if self.pager().has_prev() => {
                self.prev_page();
                self.change_page(ctx);
            }
            Some(ButtonControllerMsg::ShiftEnded) => {
                self.shift_active = false;
                self.update_buttons(ctx);
            }
            _ => {}
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
        if let Some(menu_nav) = self.menu_nav {
            if let Some(msg) = self.event_menu_nav(ctx, event, menu_nav) {
                return Some(msg);
            }
        } else if let Some(ButtonControllerMsg::Triggered(pos, _)) = self.buttons.event(ctx, event)
        {
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
        t.int("active_page", i64::from(self.pager().current()));
        t.int("page_count", i64::from(self.pager().total()));
        t.child("buttons", &self.buttons);
        t.child("content", &self.content);
        let has_menu = self.has_menu || self.menu_nav == Some(MenuNav::Menu);
        t.bool("has_menu", has_menu && self.pager().is_last());
        // The context menu is opened by the left button.
        t.bool("left_menu", self.menu_nav == Some(MenuNav::Menu));
    }
}
