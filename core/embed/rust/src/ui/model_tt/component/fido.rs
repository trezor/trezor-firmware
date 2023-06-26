use crate::ui::{
    component::{image::Image, Child, Component, Event, EventCtx, Label},
    display,
    geometry::{Insets, Rect},
    model_tt::component::{
        fido_icons::get_fido_icon_data,
        swipe::{Swipe, SwipeDirection},
        theme, ScrollBar,
    },
};

use super::CancelConfirmMsg;

const ICON_HEIGHT: i16 = 70;
const SCROLLBAR_INSET_TOP: i16 = 5;
const SCROLLBAR_HEIGHT: i16 = 10;
const APP_NAME_PADDING: i16 = 12;
const APP_NAME_HEIGHT: i16 = 30;

pub enum FidoMsg {
    Confirmed(usize),
    Cancelled,
}

pub struct FidoConfirm<F: Fn(usize) -> T, T, U> {
    page_swipe: Swipe,
    app_name: Label<T>,
    account_name: Label<T>,
    icon: Child<Image>,
    /// Function/closure that will return appropriate page on demand.
    get_account: F,
    scrollbar: ScrollBar,
    fade: bool,
    controls: U,
}

impl<F, T, U> FidoConfirm<F, T, U>
where
    F: Fn(usize) -> T,
    T: AsRef<str> + From<&'static str>,
    U: Component<Msg = CancelConfirmMsg>,
{
    pub fn new(
        app_name: T,
        get_account: F,
        page_count: usize,
        icon_name: Option<T>,
        controls: U,
    ) -> Self {
        let icon_data = get_fido_icon_data(icon_name.as_ref());

        // Preparing scrollbar and setting its page-count.
        let mut scrollbar = ScrollBar::horizontal();
        scrollbar.set_count_and_active_page(page_count, 0);

        // Preparing swipe component and setting possible initial
        // swipe directions according to number of pages.
        let mut page_swipe = Swipe::horizontal();
        page_swipe.allow_right = scrollbar.has_previous_page();
        page_swipe.allow_left = scrollbar.has_next_page();

        Self {
            app_name: Label::centered(app_name, theme::TEXT_DEMIBOLD),
            account_name: Label::centered("".into(), theme::TEXT_DEMIBOLD),
            page_swipe,
            icon: Child::new(Image::new(icon_data)),
            get_account,
            scrollbar,
            fade: false,
            controls,
        }
    }

    fn on_page_swipe(&mut self, ctx: &mut EventCtx, swipe: SwipeDirection) {
        // Change the page number.
        match swipe {
            SwipeDirection::Left if self.scrollbar.has_next_page() => {
                self.scrollbar.go_to_next_page();
            }
            SwipeDirection::Right if self.scrollbar.has_previous_page() => {
                self.scrollbar.go_to_previous_page();
            }
            _ => {} // page did not change
        };

        // Disable swipes on the boundaries. Not allowing carousel effect.
        self.page_swipe.allow_right = self.scrollbar.has_previous_page();
        self.page_swipe.allow_left = self.scrollbar.has_next_page();

        // Redraw the page.
        ctx.request_paint();

        // Reset backlight to normal level on next paint.
        self.fade = true;
    }

    fn active_page(&self) -> usize {
        self.scrollbar.active_page
    }
}

impl<F, T, U> Component for FidoConfirm<F, T, U>
where
    F: Fn(usize) -> T,
    T: AsRef<str> + From<&'static str>,
    U: Component<Msg = CancelConfirmMsg>,
{
    type Msg = FidoMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.page_swipe.place(bounds);

        // Place the control buttons.
        let controls_area = self.controls.place(bounds);

        // Get the image and content areas.
        let content_area = bounds.inset(Insets::bottom(controls_area.height()));
        let (image_area, content_area) = content_area.split_top(ICON_HEIGHT);

        // In case of showing a scrollbar, getting its area and placing it.
        let remaining_area = if self.scrollbar.page_count > 1 {
            let (scrollbar_area, remaining_area) = content_area
                .inset(Insets::top(SCROLLBAR_INSET_TOP))
                .split_top(SCROLLBAR_HEIGHT);
            self.scrollbar.place(scrollbar_area);
            remaining_area
        } else {
            content_area
        };

        // Place the icon image.
        self.icon.place(image_area);

        // Place the text labels.
        let (app_name_area, account_name_area) = remaining_area
            .inset(Insets::top(APP_NAME_PADDING))
            .split_top(APP_NAME_HEIGHT);

        self.app_name.place(app_name_area);
        self.account_name.place(account_name_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            // Swipe encountered, update the page.
            self.on_page_swipe(ctx, swipe);
        }
        if let Some(msg) = self.controls.event(ctx, event) {
            // Some button was clicked, send results.
            match msg {
                CancelConfirmMsg::Confirmed => return Some(FidoMsg::Confirmed(self.active_page())),
                CancelConfirmMsg::Cancelled => return Some(FidoMsg::Cancelled),
            }
        }
        None
    }

    fn paint(&mut self) {
        self.icon.paint();
        self.controls.paint();
        self.app_name.paint();

        if self.scrollbar.page_count > 1 {
            self.scrollbar.paint();
        }

        let current_account = (self.get_account)(self.active_page());

        // Erasing the old text content before writing the new one.
        let account_name_area = self.account_name.area();
        let real_area = account_name_area
            .with_height(account_name_area.height() + self.account_name.font().text_baseline() + 1);
        display::rect_fill(real_area, theme::BG);

        // Account name is optional.
        // Showing it only if it differs from app name.
        // (Dummy requests usually have some text as both app_name and account_name.)
        if !current_account.as_ref().is_empty()
            && current_account.as_ref() != self.app_name.text().as_ref()
        {
            self.account_name.set_text(current_account);
            self.account_name.paint();
        }

        if self.fade {
            self.fade = false;
            // Note that this is blocking and takes some time.
            display::fade_backlight(theme::BACKLIGHT_NORMAL);
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.icon.bounds(sink);
        self.app_name.bounds(sink);
        self.account_name.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl<F, T, U> crate::trace::Trace for FidoConfirm<F, T, U>
where
    F: Fn(usize) -> T,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FidoConfirm");
    }
}
