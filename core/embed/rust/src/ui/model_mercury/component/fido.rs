use crate::{
    strutil::TString,
    ui::{
        component::{image::Image, Component, Event, EventCtx, Label, Swipe, SwipeDirection},
        display,
        geometry::{Insets, Rect},
        model_mercury::component::{fido_icons::get_fido_icon_data, theme, ScrollBar},
        shape,
        shape::Renderer,
    },
};

use super::CancelConfirmMsg;
use core::cell::Cell;

const ICON_HEIGHT: i16 = 70;
const SCROLLBAR_INSET_TOP: i16 = 5;
const SCROLLBAR_HEIGHT: i16 = 10;
const APP_NAME_PADDING: i16 = 12;
const APP_NAME_HEIGHT: i16 = 30;

pub enum FidoMsg {
    Confirmed(usize),
    Cancelled,
}

pub struct FidoConfirm<F: Fn(usize) -> TString<'static>, U> {
    page_swipe: Swipe,
    app_name: Label<'static>,
    account_name: Label<'static>,
    icon: Image,
    /// Function/closure that will return appropriate page on demand.
    get_account: F,
    scrollbar: ScrollBar,
    fade: Cell<bool>,
    controls: U,
}

impl<F, U> FidoConfirm<F, U>
where
    F: Fn(usize) -> TString<'static>,
    U: Component<Msg = CancelConfirmMsg>,
{
    pub fn new(
        app_name: TString<'static>,
        get_account: F,
        page_count: usize,
        icon_name: Option<TString<'static>>,
        controls: U,
    ) -> Self {
        let icon_data = get_fido_icon_data(icon_name);

        // Preparing scrollbar and setting its page-count.
        let mut scrollbar = ScrollBar::horizontal();
        scrollbar.set_count_and_active_page(page_count, 0);

        // Preparing swipe component and setting possible initial
        // swipe directions according to number of pages.
        let mut page_swipe = Swipe::horizontal();
        page_swipe.allow_right = scrollbar.has_previous_page();
        page_swipe.allow_left = scrollbar.has_next_page();

        // NOTE: This is an ugly hotfix for the erroneous behavior of
        // TextLayout used in the account_name Label. In this
        // particular case, TextLayout calculates the wrong height of
        // fitted text that's higher than the TextLayout bound itself.
        //
        // The following two lines should be swapped when the problem with
        // TextLayout is fixed.
        //
        // See also, continuation of this hotfix in the place() function.

        // let current_account = get_account(scrollbar.active_page);
        let current_account = "".into();

        Self {
            app_name: Label::centered(app_name, theme::TEXT_DEMIBOLD),
            account_name: Label::centered(current_account, theme::TEXT_DEMIBOLD),
            page_swipe,
            icon: Image::new(icon_data),
            get_account,
            scrollbar,
            fade: Cell::new(false),
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

        let current_account = (self.get_account)(self.active_page());
        self.account_name.set_text(current_account);

        // Redraw the page.
        ctx.request_paint();

        // Reset backlight to normal level on next paint.
        self.fade.set(true);
    }

    fn active_page(&self) -> usize {
        self.scrollbar.active_page
    }
}

impl<F, U> Component for FidoConfirm<F, U>
where
    F: Fn(usize) -> TString<'static>,
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

        // NOTE: This is a hotfix used due to the erroneous behavior of TextLayout.
        // This line should be removed when the problem with TextLayout is fixed.
        // See also the code for FidoConfirm::new().
        self.account_name
            .set_text((self.get_account)(self.scrollbar.active_page));

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

        // Erasing the old text content before writing the new one.
        let account_name_area = self.account_name.area();
        let real_area = account_name_area
            .with_height(account_name_area.height() + self.account_name.font().text_baseline() + 1);
        display::rect_fill(real_area, theme::BG);

        // Account name is optional.
        // Showing it only if it differs from app name.
        // (Dummy requests usually have some text as both app_name and account_name.)
        let account_name = self.account_name.text();
        let app_name = self.app_name.text();
        if !account_name.is_empty() && account_name != app_name {
            self.account_name.paint();
        }

        if self.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(theme::backlight::get_backlight_normal());
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.icon.render(target);
        self.controls.render(target);
        self.app_name.render(target);

        if self.scrollbar.page_count > 1 {
            self.scrollbar.render(target);
        }

        // Erasing the old text content before writing the new one.
        let account_name_area = self.account_name.area();
        let real_area = account_name_area
            .with_height(account_name_area.height() + self.account_name.font().text_baseline() + 1);
        shape::Bar::new(real_area).with_bg(theme::BG).render(target);

        // Account name is optional.
        // Showing it only if it differs from app name.
        // (Dummy requests usually have some text as both app_name and account_name.)
        let account_name = self.account_name.text();
        let app_name = self.app_name.text();
        if !account_name.is_empty() && account_name != app_name {
            self.account_name.render(target);
        }

        if self.fade.take() {
            // Note that this is blocking and takes some time.
            display::fade_backlight(theme::backlight::get_backlight_normal());
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<F, T> crate::trace::Trace for FidoConfirm<F, T>
where
    F: Fn(usize) -> TString<'static>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("FidoConfirm");
    }
}
