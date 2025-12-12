use crate::{
    strutil::TString,
    ui::{
        component::{
            image::Image,
            text::paragraphs::{Paragraph, ParagraphSource, Paragraphs},
            Child, Component, Event, EventCtx, Label, Paginate,
        },
        display,
        geometry::{Insets, Rect},
        shape::{self, Renderer},
        util::Pager,
    },
};

use super::{
    fido_icons::get_fido_icon_data,
    swipe::{Swipe, SwipeDirection},
    theme, CancelConfirmMsg, ScrollBar,
};

use core::cell::Cell;

const ICON_HEIGHT: i16 = 70;
const SCROLLBAR_INSET_TOP: i16 = 5;
const SCROLLBAR_HEIGHT: i16 = 10;
const APP_NAME_PADDING: i16 = 12;
const APP_NAME_HEIGHT: i16 = 30;

#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum FidoMsg {
    Confirmed(usize),
    Cancelled,
}

pub struct FidoConfirm<F: Fn(usize) -> TString<'static>, U> {
    page_swipe: Swipe,
    app_name: Label<'static>,
    account_name: Paragraphs<Paragraph<'static>>,
    icon: Child<Image>,
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
        scrollbar.set_pager(Pager::new(page_count as u16));

        // Preparing swipe component and setting possible initial
        // swipe directions according to number of pages.
        let mut page_swipe = Swipe::horizontal();
        page_swipe.allow_right = scrollbar.pager().has_prev();
        page_swipe.allow_left = scrollbar.pager().has_next();

        Self {
            app_name: Label::centered(app_name, theme::TEXT_DEMIBOLD),
            account_name: Paragraph::new(
                &theme::TEXT_MONO_DATA,
                get_account(scrollbar.pager().current().into()),
            )
            .into_paragraphs(),
            page_swipe,
            icon: Child::new(Image::new(icon_data)),
            get_account,
            scrollbar,
            fade: Cell::new(false),
            controls,
        }
    }

    fn on_page_swipe(&mut self, ctx: &mut EventCtx, swipe: SwipeDirection) {
        // Change the page number.
        match swipe {
            SwipeDirection::Left => {
                self.scrollbar.next_page();
            }
            SwipeDirection::Right => {
                self.scrollbar.prev_page();
            }
            _ => {} // page did not change
        };

        // Disable swipes on the boundaries. Not allowing carousel effect.
        self.page_swipe.allow_right = self.scrollbar.has_previous_page();
        self.page_swipe.allow_left = self.scrollbar.has_next_page();

        self.account_name
            .update((self.get_account)(self.active_page()));

        // Redraw the page.
        ctx.request_paint();

        // Reset backlight to normal level on next paint.
        self.fade.set(true);
    }

    fn active_page(&self) -> usize {
        self.scrollbar.pager().current() as usize
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
        let remaining_area = if !self.scrollbar.pager().is_single() {
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
        let (app_name_area, account_name_area) = remaining_area.split_top(APP_NAME_HEIGHT);

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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.icon.render(target);
        self.controls.render(target);
        self.app_name.render(target);

        if self.scrollbar.pager().total() > 1 {
            self.scrollbar.render(target);
        }

        // Erasing the old text content before writing the new one.
        shape::Bar::new(self.account_name.area())
            .with_bg(theme::BG)
            .render(target);

        // Account name is optional.
        // Showing it only if it differs from app name.
        // (Dummy requests usually have some text as both app_name and account_name.)
        let account_name = self.account_name.content();
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
        t.string("account_name", *self.account_name.content());
    }
}
