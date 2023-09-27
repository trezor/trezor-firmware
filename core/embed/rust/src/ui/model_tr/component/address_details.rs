use heapless::Vec;

use crate::{
    error::Error,
    strutil::StringType,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs, VecExt},
            Child, Component, Event, EventCtx, Pad, Paginate, Qr,
        },
        geometry::Rect,
    },
};

use super::{
    theme, ButtonController, ButtonControllerMsg, ButtonDetails, ButtonLayout, ButtonPos, Frame,
};

const MAX_XPUBS: usize = 16;
const QR_BORDER: i16 = 3;

pub struct AddressDetails<T>
where
    T: StringType,
{
    qr_code: Qr,
    details_view: Paragraphs<ParagraphVecShort<T>>,
    xpub_view: Frame<Paragraphs<Paragraph<T>>, T>,
    xpubs: Vec<(T, T), MAX_XPUBS>,
    current_page: usize,
    current_subpage: usize,
    area: Rect,
    pad: Pad,
    buttons: Child<ButtonController<T>>,
}

impl<T> AddressDetails<T>
where
    T: StringType + Clone,
{
    pub fn new(
        qr_address: T,
        case_sensitive: bool,
        account: Option<T>,
        path: Option<T>,
    ) -> Result<Self, Error> {
        let qr_code = Qr::new(qr_address, case_sensitive)?.with_border(QR_BORDER);
        let details_view = {
            let mut para = ParagraphVecShort::new();
            if let Some(account) = account {
                para.add(Paragraph::new(&theme::TEXT_BOLD, "Account:".into()));
                para.add(Paragraph::new(&theme::TEXT_MONO, account));
            }
            if let Some(path) = path {
                para.add(Paragraph::new(&theme::TEXT_BOLD, "Derivation path:".into()));
                para.add(Paragraph::new(&theme::TEXT_MONO, path));
            }
            Paragraphs::new(para)
        };
        let xpub_view = Frame::new(
            "".into(),
            Paragraph::new(&theme::TEXT_MONO_DATA, "".into()).into_paragraphs(),
        );

        let result = Self {
            qr_code,
            details_view,
            xpub_view,
            xpubs: Vec::new(),
            area: Rect::zero(),
            current_page: 0,
            current_subpage: 0,
            pad: Pad::with_background(theme::BG).with_clear(),
            buttons: Child::new(ButtonController::new(ButtonLayout::arrow_none_arrow())),
        };
        Ok(result)
    }

    pub fn add_xpub(&mut self, title: T, xpub: T) -> Result<(), Error> {
        self.xpubs
            .push((title, xpub))
            .map_err(|_| Error::OutOfRange)
    }

    fn is_in_subpage(&self) -> bool {
        self.current_subpage > 0
    }

    fn is_xpub_page(&self) -> bool {
        self.current_page > 1
    }

    fn is_last_page(&self) -> bool {
        self.current_page == self.page_count() - 1
    }

    fn is_last_subpage(&mut self) -> bool {
        self.current_subpage == self.subpages_in_current_page() - 1
    }

    fn subpages_in_current_page(&mut self) -> usize {
        if self.is_xpub_page() {
            self.xpub_view.page_count()
        } else {
            1
        }
    }

    /// Button layout for the current page.
    /// Normally there are arrows everywhere, apart from the right side of the
    /// last page. On xpub pages there is SHOW ALL middle button when it
    /// cannot fit one page. On xpub subpages there are wide arrows to
    /// scroll.
    fn get_button_layout(&mut self) -> ButtonLayout<T> {
        let (left, middle, right) = if self.is_in_subpage() {
            let left = Some(ButtonDetails::up_arrow_icon_wide());
            let right = if self.is_last_subpage() {
                None
            } else {
                Some(ButtonDetails::down_arrow_icon_wide())
            };
            (left, None, right)
        } else {
            let left = Some(ButtonDetails::left_arrow_icon());
            let middle = if self.is_xpub_page() && self.subpages_in_current_page() > 1 {
                Some(ButtonDetails::armed_text("SHOW ALL".into()))
            } else {
                None
            };
            let right = if self.is_last_page() {
                None
            } else {
                Some(ButtonDetails::right_arrow_icon())
            };
            (left, middle, right)
        };
        ButtonLayout::new(left, middle, right)
    }

    /// Reflecting the current page in the buttons.
    fn update_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.get_button_layout();
        self.buttons.mutate(ctx, |_ctx, buttons| {
            buttons.set(btn_layout);
        });
    }

    fn page_count(&self) -> usize {
        2 + self.xpubs.len()
    }

    fn fill_xpub_page(&mut self, ctx: &mut EventCtx) {
        let i = self.current_page - 2;
        self.xpub_view.update_title(ctx, self.xpubs[i].0.clone());
        self.xpub_view.update_content(ctx, |p| {
            p.inner_mut().update(self.xpubs[i].1.clone());
            p.change_page(0)
        });
    }

    fn change_page(&mut self, ctx: &mut EventCtx) {
        if self.is_xpub_page() {
            self.fill_xpub_page(ctx);
        }
        self.pad.clear();
        self.current_subpage = 0;
    }

    fn change_subpage(&mut self, ctx: &mut EventCtx) {
        if self.is_xpub_page() {
            self.xpub_view
                .update_content(ctx, |p| p.change_page(self.current_subpage));
            self.pad.clear();
        }
    }
}

impl<T> Component for AddressDetails<T>
where
    T: StringType + Clone,
{
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        // QR code is being placed on the whole bounds, so it can be as big as possible
        // (it will not collide with the buttons, they are narrow and on the sides).
        // Therefore, also placing pad on the whole bounds.
        self.qr_code.place(bounds);
        self.pad.place(bounds);
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        self.details_view.place(content_area);
        self.xpub_view.place(content_area);
        self.buttons.place(button_area);
        self.area = content_area;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Possibly update the components that have e.g. marquee
        match self.current_page {
            0 => self.qr_code.event(ctx, event),
            1 => self.details_view.event(ctx, event),
            _ => self.xpub_view.event(ctx, event),
        };

        let button_event = self.buttons.event(ctx, event);
        if let Some(ButtonControllerMsg::Triggered(button, _)) = button_event {
            if self.is_in_subpage() {
                match button {
                    ButtonPos::Left => {
                        // Going back
                        self.current_subpage -= 1;
                    }
                    ButtonPos::Right => {
                        // Going next
                        self.current_subpage += 1;
                    }
                    _ => unreachable!(),
                }
                self.change_subpage(ctx);
                self.update_buttons(ctx);
                return None;
            } else {
                match button {
                    ButtonPos::Left => {
                        // Cancelling or going back
                        if self.current_page == 0 {
                            return Some(());
                        }
                        self.current_page -= 1;
                        self.change_page(ctx);
                    }
                    ButtonPos::Right => {
                        // Going to the next page
                        self.current_page += 1;
                        self.change_page(ctx);
                    }
                    ButtonPos::Middle => {
                        // Going into subpage
                        self.current_subpage = 1;
                        self.change_subpage(ctx);
                    }
                }
                self.update_buttons(ctx);
                return None;
            }
        }
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.buttons.paint();
        match self.current_page {
            0 => self.qr_code.paint(),
            1 => self.details_view.paint(),
            _ => self.xpub_view.paint(),
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area)
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for AddressDetails<T>
where
    T: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("AddressDetails");
        match self.current_page {
            0 => t.child("qr_code", &self.qr_code),
            1 => t.child("details_view", &self.details_view),
            _ => t.child("xpub_view", &self.xpub_view),
        }
    }
}
