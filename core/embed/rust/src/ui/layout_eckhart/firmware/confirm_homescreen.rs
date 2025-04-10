use crate::{
    error::{value_error, Error},
    io::BinaryData,
    strutil::TString,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Label},
        constant::SCREEN,
        display::image::ImageInfo,
        geometry::{Insets, Rect},
        shape::{self, Renderer},
    },
};

use super::{check_homescreen_format, theme, ActionBar, ActionBarMsg, Header};

/// Full-screen component for confirming a new homescreen image. If the image is
/// empty, the user is asked to confirm the default homescreen.
pub struct ConfirmHomescreen {
    header: Header,
    text: Option<Label<'static>>,
    image: Option<BinaryData<'static>>,
    action_bar: ActionBar,
}

pub enum ConfirmHomescreenMsg {
    Cancelled,
    Confirmed,
}

impl ConfirmHomescreen {
    pub fn new(title: TString<'static>, image: BinaryData<'static>) -> Result<Self, Error> {
        let action_bar = ActionBar::new_cancel_confirm();
        let header = Header::new(title);

        if image.is_empty() {
            // Use default homescreen
            Ok(Self {
                header,
                text: Some(Label::left_aligned(
                    TR::homescreen__set_default.into(),
                    theme::firmware::TEXT_REGULAR,
                )),
                image: None,
                action_bar,
            })
        } else {
            // Validate and use custom homescreen
            if !check_homescreen_format(image) {
                return Err(value_error!(c"Invalid image."));
            }

            Ok(Self {
                header,
                text: None,
                image: Some(image),
                action_bar,
            })
        }
    }
}

impl Component for ConfirmHomescreen {
    type Msg = ConfirmHomescreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
        let text_area = rest.inset(theme::SIDE_INSETS);

        self.header.place(header_area);
        self.action_bar.place(action_bar_area);
        self.text.place(text_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.action_bar.event(ctx, event).and_then(|msg| match msg {
            ActionBarMsg::Cancelled => Some(Self::Msg::Cancelled),
            ActionBarMsg::Confirmed => Some(Self::Msg::Confirmed),
            _ => None,
        })
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(image) = self.image {
            if let ImageInfo::Jpeg(_) = ImageInfo::parse(image) {
                let clip = SCREEN.inset(Insets::bottom(theme::ACTION_BAR_HEIGHT));
                target.in_clip(clip, &|t| {
                    shape::JpegImage::new_image(SCREEN.top_left(), image).render(t);
                });
            }
        }
        self.header.render(target);
        self.text.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ConfirmHomescreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ConfirmHomescreen");
    }
}
