use crate::{
    strutil::TString,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Pad, Paginate},
        constant::SCREEN,
        geometry::Rect,
        shape::Renderer,
    },
};

use super::{
    scrollbar::SCROLLBAR_SPACE, theme, title::Title, ButtonAction, ButtonController,
    ButtonControllerMsg, ButtonDetails, ButtonLayout, ButtonPos, CancelInfoConfirmMsg, FlowPages,
    Page, ScrollBar,
};

/// Encoding stride for the `Info` resume token: `page * STRIDE + sub_page`.
/// Must match the decode sites (`show_nav_tutorial` and the Python wrapper).
pub const NAV_SUBPAGE_STRIDE: usize = 100;

pub struct Flow<F>
where
    F: Fn(usize) -> Page,
{
    /// Function to get pages from
    pages: FlowPages<F>,
    /// Instance of the current Page
    current_page: Page,
    /// Title being shown at the top in bold upper
    title: Option<Title>,
    has_common_title: bool,
    scrollbar: Child<ScrollBar>,
    content_area: Rect,
    title_area: Rect,
    pad: Pad,
    buttons: Child<ButtonController>,
    page_counter: usize,
    return_confirmed_index: bool,
    /// When set, an `Info` result returns the current page index (instead of
    /// the `INFO` sentinel), so the caller can resume on the same page after a
    /// context menu.
    return_info_index: bool,
    show_scrollbar: bool,
    /// On `Page::is_nav()` pages, show a numeric "current/total" sub-page
    /// counter (top-right, like show_nav_demo) instead of the dot scrollbar.
    numeric_nav_indicator: bool,
    /// Possibly enforcing the second button to be ignored after some time after
    /// pressing the first button
    ignore_second_button_ms: Option<u32>,
    /// Whether the left "Shift" is currently being held on an action-bar
    /// (`Page::is_nav()`) page.
    shift_active: bool,
    /// Sub-page to jump to within the starting page on first `place()`
    /// (used to resume a scrolled nav page after a menu). Consumed once.
    start_subpage: u16,
    #[cfg(feature = "ui_debug")]
    has_menu: bool,
}

impl<F> Flow<F>
where
    F: Fn(usize) -> Page,
{
    pub fn new(pages: FlowPages<F>) -> Self {
        let current_page = pages.get(0);
        let title = current_page.title().map(Title::new);
        Self {
            pages,
            current_page,
            title,
            has_common_title: false,
            content_area: Rect::zero(),
            title_area: Rect::zero(),
            scrollbar: Child::new(ScrollBar::to_be_filled_later()),
            pad: Pad::with_background(theme::BG),
            // Setting empty layout for now, we do not yet know how many sub-pages the first page
            // has. Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
            page_counter: 0,
            return_confirmed_index: false,
            return_info_index: false,
            show_scrollbar: true,
            numeric_nav_indicator: false,
            ignore_second_button_ms: None,
            shift_active: false,
            start_subpage: 0,
            #[cfg(feature = "ui_debug")]
            has_menu: false,
        }
    }

    /// Adding a common title to all pages. The title will not be colliding
    /// with the page content, as the content will be offset.
    pub fn with_common_title(mut self, title: TString<'static>) -> Self {
        self.title = Some(Title::new(title));
        self.has_common_title = true;
        self
    }

    /// Causing the Flow to return the index of the page that was confirmed.
    pub fn with_return_confirmed_index(mut self) -> Self {
        self.return_confirmed_index = true;
        self
    }

    /// Causing an `Info` result to carry the index of the page it was triggered
    /// from (so a caller can resume there after a context menu).
    pub fn with_return_info_index(mut self) -> Self {
        self.return_info_index = true;
        self
    }

    /// Info result token = `page_counter * NAV_SUBPAGE_STRIDE + sub_page`, so
    /// the caller can resume on the exact page AND sub-page after a menu. Decode
    /// with the same stride (see `show_nav_tutorial`). `NAV_SUBPAGE_STRIDE` must
    /// match the decode sites (ui_firmware.rs and the Python wrapper).
    pub fn info_index(&self) -> Option<usize> {
        let sub_page = self.current_page.pager().current() as usize;
        self.return_info_index
            .then_some(self.page_counter * NAV_SUBPAGE_STRIDE + sub_page)
    }

    /// Show scrollbar or not.
    pub fn with_scrollbar(mut self, show_scrollbar: bool) -> Self {
        self.show_scrollbar = show_scrollbar;
        self
    }

    /// On action-bar (`Page::is_nav()`) pages, show a numeric "current/total"
    /// sub-page counter in the top-right (like show_nav_demo).
    pub fn with_numeric_nav_indicator(mut self) -> Self {
        self.numeric_nav_indicator = true;
        self
    }

    /// Whether the current page should use the numeric sub-page counter.
    fn use_numeric_indicator(&self) -> bool {
        self.numeric_nav_indicator && self.current_page.is_nav()
    }

    /// Start the flow on a page other than the first one. The button layout is
    /// (re)computed for the starting page in `place()`.
    pub fn with_start_page(mut self, page: usize) -> Self {
        let page = page.min(self.pages.count().saturating_sub(1));
        self.page_counter = page;
        self.current_page = self.pages.get(page);
        if !self.has_common_title {
            self.title = self.current_page.title().map(Title::new);
        }
        self
    }

    /// Start on a given sub-page within the starting page (applied on the first
    /// `place()`), so a scrolled nav page can be resumed after a menu.
    pub fn with_start_subpage(mut self, subpage: u16) -> Self {
        self.start_subpage = subpage;
        self
    }

    /// Ignoring the second button duration
    pub fn with_ignore_second_button_ms(mut self, ignore_second_button_ms: u32) -> Self {
        self.ignore_second_button_ms = Some(ignore_second_button_ms);
        self
    }

    pub fn confirmed_index(&self) -> Option<usize> {
        self.return_confirmed_index.then_some(self.page_counter)
    }

    #[cfg(feature = "ui_debug")]
    pub fn with_menu(mut self, has_menu: bool) -> Self {
        self.has_menu = has_menu;
        self
    }

    #[cfg(not(feature = "ui_debug"))]
    pub fn with_menu(self, _has_menu: bool) -> Self {
        self
    }

    /// Getting new current page according to page counter.
    /// Also updating the possible title and moving the scrollbar to correct
    /// position.
    fn change_current_page(&mut self, ctx: &mut EventCtx) {
        self.current_page = self.pages.get(self.page_counter);
        if !self.has_common_title {
            if let Some(title) = self.current_page.title() {
                self.title = Some(Title::new(title));
            } else {
                self.title = None;
            }
            // in case the title was added or removed, re-calculate the areas for
            // subcomponents
            self.place(SCREEN);
        }
        let use_numeric = self.use_numeric_indicator();
        let nav_pager = self.current_page.pager();
        let scrollbar_active_index = self
            .pages
            .scrollbar_page_index(self.content_area, self.page_counter);
        self.scrollbar.mutate(ctx, |_ctx, scrollbar| {
            if use_numeric {
                // Numeric counter reflects the current page's own sub-pages.
                scrollbar.set_pager(nav_pager);
            } else {
                scrollbar.change_page(scrollbar_active_index);
            }
        });
    }

    /// Placing current page, setting current buttons and clearing.
    fn update(&mut self, ctx: &mut EventCtx, get_new_page: bool) {
        if get_new_page {
            self.change_current_page(ctx);
            self.current_page.place(self.content_area);
        }
        self.set_buttons(ctx);
        self.scrollbar.request_complete_repaint(ctx);
        self.clear_and_repaint(ctx);
    }

    /// Clearing the whole area and requesting repaint.
    fn clear_and_repaint(&mut self, ctx: &mut EventCtx) {
        self.pad.clear();
        ctx.request_paint();
    }

    /// Going to the previous page.
    fn go_to_prev_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter -= 1;
        self.update(ctx, true);
    }

    /// Going to the next page.
    fn go_to_next_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter += 1;
        self.update(ctx, true);
    }

    /// Going to the first page.
    fn go_to_first_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter = 0;
        self.update(ctx, true);
    }

    /// Going to the first page.
    fn go_to_last_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter = self.pages.count() - 1;
        self.update(ctx, true);
    }

    /// Jumping to another page relative to the current one.
    fn go_to_page_relative(&mut self, jump: i16, ctx: &mut EventCtx) {
        self.page_counter += jump as usize;
        self.update(ctx, true);
    }

    /// Updating the visual state of the buttons after each event.
    /// All three buttons are handled based upon the current choice.
    /// If defined in the current choice, setting their text,
    /// whether they are long-pressed, and painting them.
    fn set_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.current_btn_layout();
        self.buttons.mutate(ctx, |ctx, buttons| {
            buttons.set(btn_layout);
            // Force a full repaint so leftover "pressed"/highlight pixels (e.g.
            // from holding the left button before entering Shift) are cleared.
            buttons.request_complete_repaint(ctx);
        });
    }

    /// The button layout for the current page, honoring the action-bar
    /// navigation on `Page::is_nav()` pages (which `Flow` drives itself).
    fn current_btn_layout(&self) -> ButtonLayout {
        if self.current_page.is_nav() {
            self.get_nav_button_layout()
        } else {
            self.current_page.btn_layout()
        }
    }

    /// Action-bar button layout for a nav page, mirroring `ButtonPage`:
    /// - not scrolled yet (no previous sub-page): the page's configured left
    ///   button (a back arrow to the previous step) and a wide down arrow;
    /// - scrolled (previous sub-page exists): left = menu icon in parentheses
    ///   (short press = menu, hold = Shift), right = down arrow or the page's
    ///   configured right button on the last sub-page;
    /// - while Shift is held: left = filled "Shift", right = the secondary
    ///   "back" (scroll up) button.
    fn get_nav_button_layout(&self) -> ButtonLayout {
        let pager = self.current_page.pager();
        let has_prev = pager.has_prev();
        let has_next = pager.has_next();
        let raw = self.current_page.raw_btn_layout();

        if self.shift_active {
            let btn_right = has_prev.then(ButtonDetails::back_secondary_icon);
            return ButtonLayout::new(Some(ButtonDetails::shift_text()), None, btn_right);
        }

        let btn_left = if has_prev {
            Some(ButtonDetails::menu_shift_icon())
        } else {
            raw.btn_left
        };
        let btn_right = if has_next {
            Some(ButtonDetails::down_arrow_icon_wide())
        } else {
            raw.btn_right
        };
        ButtonLayout::new(btn_left, None, btn_right)
    }

    /// Current choice is still the same, only its inner state has changed
    /// (its sub-page changed).
    fn update_after_current_choice_inner_change(&mut self, ctx: &mut EventCtx) {
        let inner_page = self.current_page.pager().current();
        let use_numeric = self.use_numeric_indicator();
        let nav_pager = self.current_page.pager();
        self.scrollbar.mutate(ctx, |ctx, scrollbar| {
            if use_numeric {
                // Advance the numeric "current/total" counter (e.g. 1/2 -> 2/2).
                scrollbar.set_pager(nav_pager);
            } else {
                scrollbar.change_page(self.page_counter as u16 + inner_page);
            }
            scrollbar.request_complete_repaint(ctx);
        });
        self.update(ctx, false);
    }

    /// When current choice contains paginated content, it may use the button
    /// event to just paginate itself.
    fn event_consumed_by_current_choice(&mut self, ctx: &mut EventCtx, pos: ButtonPos) -> bool {
        if matches!(pos, ButtonPos::Left) && self.current_page.pager().has_prev() {
            self.current_page.prev_page();
            self.update_after_current_choice_inner_change(ctx);
            true
        } else if matches!(pos, ButtonPos::Right) && self.current_page.pager().has_next() {
            self.current_page.next_page();
            self.update_after_current_choice_inner_change(ctx);
            true
        } else {
            false
        }
    }

    /// Execute the action configured for a button position, returning a message
    /// for the ones that leave the flow.
    fn dispatch_action(
        &mut self,
        ctx: &mut EventCtx,
        pos: ButtonPos,
    ) -> Option<CancelInfoConfirmMsg> {
        match self.current_page.btn_actions().get_action(pos) {
            Some(ButtonAction::PrevPage) => {
                self.go_to_prev_page(ctx);
                None
            }
            Some(ButtonAction::NextPage) => {
                self.go_to_next_page(ctx);
                None
            }
            Some(ButtonAction::FirstPage) => {
                self.go_to_first_page(ctx);
                None
            }
            Some(ButtonAction::LastPage) => {
                self.go_to_last_page(ctx);
                None
            }
            Some(ButtonAction::Cancel) => Some(CancelInfoConfirmMsg::Cancelled),
            Some(ButtonAction::Confirm) => Some(CancelInfoConfirmMsg::Confirmed),
            Some(ButtonAction::Info) => Some(CancelInfoConfirmMsg::Info),
            None => None,
        }
    }

    /// Scroll one sub-page back within the current (action-bar) page.
    fn scroll_to_prev_subpage(&mut self, ctx: &mut EventCtx) {
        self.current_page.prev_page();
        self.update_after_current_choice_inner_change(ctx);
    }

    /// Scroll one sub-page forward within the current (action-bar) page.
    fn scroll_to_next_subpage(&mut self, ctx: &mut EventCtx) {
        self.current_page.next_page();
        self.update_after_current_choice_inner_change(ctx);
    }

    /// Event handling for an action-bar (`Page::is_nav()`) page: left short
    /// press opens the menu (once scrolled), a ~0.5s left hold engages "Shift"
    /// so the right button scrolls back up, and the right button scrolls down
    /// or performs the page's configured action on the last sub-page.
    fn event_nav(
        &mut self,
        ctx: &mut EventCtx,
        button_event: Option<ButtonControllerMsg>,
    ) -> Option<CancelInfoConfirmMsg> {
        let msg = button_event?;
        let has_prev = self.current_page.pager().has_prev();
        match msg {
            ButtonControllerMsg::LongPressed(ButtonPos::Left) if has_prev => {
                self.shift_active = true;
                self.set_buttons(ctx);
                self.buttons.mutate(ctx, |ctx, buttons| {
                    buttons.highlight_button(ctx, ButtonPos::Left);
                });
            }
            ButtonControllerMsg::ShiftReleased => {
                self.shift_active = false;
                self.set_buttons(ctx);
            }
            ButtonControllerMsg::Triggered(ButtonPos::Left, _) => {
                if self.shift_active {
                    // Was a long press (Shift shown): releasing just restores the
                    // default layout and does NOT open the menu.
                    self.shift_active = false;
                    self.set_buttons(ctx);
                } else if has_prev {
                    // Menu icon short press: open the context menu.
                    return Some(CancelInfoConfirmMsg::Info);
                } else {
                    // First sub-page: the configured left action (back a step).
                    return self.dispatch_action(ctx, ButtonPos::Left);
                }
            }
            ButtonControllerMsg::ShiftedTriggered(ButtonPos::Right) => {
                if self.current_page.pager().has_prev() {
                    self.scroll_to_prev_subpage(ctx);
                }
                // Shift is still held; keep the "Shift" label filled.
                self.buttons.mutate(ctx, |ctx, buttons| {
                    buttons.highlight_button(ctx, ButtonPos::Left);
                });
            }
            ButtonControllerMsg::Triggered(ButtonPos::Right, _) => {
                if self.current_page.pager().has_next() {
                    self.scroll_to_next_subpage(ctx);
                } else {
                    return self.dispatch_action(ctx, ButtonPos::Right);
                }
            }
            _ => {}
        }
        None
    }
}

impl<F> Component for Flow<F>
where
    F: Fn(usize) -> Page,
{
    type Msg = CancelInfoConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (title_content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        // Accounting for possible title
        let (title_area, content_area) = if self.title.is_some() {
            title_content_area.split_top(theme::FONT_HEADER.line_height())
        } else {
            (Rect::zero(), title_content_area)
        };
        self.content_area = content_area;

        // Place the current page first so we can read its sub-page pager
        // (needed for the numeric nav indicator and the nav button layout).
        self.current_page.place(content_area);

        // Resume at a requested sub-page (once), e.g. after closing a menu that
        // was opened from a scrolled nav page. Done before reading the pager.
        if self.start_subpage > 0 {
            self.current_page.change_page(self.start_subpage);
            self.start_subpage = 0;
        }

        let use_numeric = self.use_numeric_indicator();
        // Build the scrollbar: a numeric per-page "current/total" counter on
        // action-bar (nav) pages, otherwise the flow-wide dot scrollbar.
        let scrollbar = if use_numeric {
            let mut sb = ScrollBar::to_be_filled_later().with_numeric();
            sb.set_pager(self.current_page.pager());
            sb
        } else {
            ScrollBar::new(self.pages.scrollbar_page_count(content_area))
        };
        self.scrollbar = Child::new(scrollbar);

        // Placing a title and scrollbar/indicator in case the title is there.
        if self.title.is_some() {
            let show_indicator = self.show_scrollbar || use_numeric;
            let (title_area, scrollbar_area) = if show_indicator {
                title_area.split_right(self.scrollbar.inner().overall_width() + SCROLLBAR_SPACE)
            } else {
                (title_area, Rect::zero())
            };

            self.title.place(title_area);
            self.title_area = title_area;
            self.scrollbar.place(scrollbar_area);
        }

        // The current page is already placed above; set its button layout.
        let mut controller = ButtonController::new(self.current_btn_layout());
        if let Some(ignore_ms) = self.ignore_second_button_ms {
            controller = controller.with_ignore_btn_delay(ignore_ms);
        }
        // Holding the left button acts as a "Shift" modifier on action-bar
        // pages. Harmless on other pages: their left buttons do not request
        // long-press events, so no shift can engage.
        controller = controller.with_left_shift();
        self.buttons = Child::new(controller);

        self.pad.place(title_content_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.pages.scrollbar_page_count(self.content_area));
        self.title.event(ctx, event);
        let button_event = self.buttons.event(ctx, event);

        // Action-bar (menu + "Shift") pages are handled separately.
        if self.current_page.is_nav() {
            return self.event_nav(ctx, button_event);
        }

        // Do something when a button was triggered
        // and we have some action connected with it
        if let Some(ButtonControllerMsg::Triggered(pos, _)) = button_event {
            // When there is a previous or next screen in the current flow,
            // handle that first and in case it triggers, then do not continue
            if self.event_consumed_by_current_choice(ctx, pos) {
                return None;
            }

            return self.dispatch_action(ctx, pos);
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        // Scrollbars are painted only with a title and when requested (or the
        // numeric sub-page counter on action-bar pages).
        if self.title.is_some() {
            if self.show_scrollbar || self.use_numeric_indicator() {
                self.scrollbar.render(target);
            }
            self.title.render(target);
        }
        self.buttons.render(target);
        // On purpose painting current page at the end, after buttons,
        // because we sometimes (in the case of QR code) need to use the
        // whole height of the display for showing the content
        // (and painting buttons last would cover the lower part).
        self.current_page.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<F> crate::trace::Trace for Flow<F>
where
    F: Fn(usize) -> Page,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Flow");
        t.int("flow_page", self.page_counter as i64);
        t.int("flow_page_count", self.pages.count() as i64);

        if let Some(title) = &self.title {
            t.child("title", title);
        }
        t.child("scrollbar", &self.scrollbar);
        t.child("buttons", &self.buttons);
        t.child("flow_page", &self.current_page);
        t.bool(
            "has_menu",
            self.has_menu && self.current_page.pager().is_last(),
        );
    }
}
