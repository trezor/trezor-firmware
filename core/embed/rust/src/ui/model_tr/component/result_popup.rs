use crate::{
    strutil::StringType,
    time::Instant,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            Child, Component, ComponentExt, Event, EventCtx, Label, Pad,
        },
        constant::screen,
        display::toif::Icon,
        geometry::{Insets, LinearPlacement, Rect},
    },
};

use super::{
    super::theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos, ResultAnim,
    ResultAnimMsg,
};

pub enum ResultPopupMsg {
    Confirmed,
}

pub struct ResultPopup<T>
where
    T: StringType,
{
    area: Rect,
    pad: Pad,
    result_anim: Child<ResultAnim>,
    headline: Option<Label<&'static str>>,
    text: Child<Paragraphs<Paragraph<T>>>,
    buttons: Option<Child<ButtonController<T>>>,
    autoclose: bool,
}

const ANIM_SIZE: i16 = 18;
const ANIM_SPACE: i16 = 11;
const ANIM_POS: i16 = 32;
const ANIM_POS_ADJ_HEADLINE: i16 = 10;
const ANIM_POS_ADJ_BUTTON: i16 = 6;

impl<T> ResultPopup<T>
where
    T: StringType + Clone,
{
    pub fn new(
        icon: Icon,
        text: T,
        headline: Option<&'static str>,
        button_text: Option<&'static str>,
    ) -> Self {
        let p1 = Paragraphs::new(Paragraph::new(&theme::TEXT_BIG, text))
            .with_placement(LinearPlacement::vertical().align_at_center());

        let buttons = button_text.map(|text| {
            let btn_layout = ButtonLayout::none_none_text(text.into());
            Child::new(ButtonController::new(btn_layout))
        });

        let mut pad = Pad::with_background(theme::BG);
        pad.clear();

        Self {
            area: Rect::zero(),
            pad,
            result_anim: Child::new(ResultAnim::new(icon)),
            headline: headline.map(|a| Label::centered(a, theme::TEXT_BOLD)),
            text: Child::new(p1),
            buttons,
            autoclose: false,
        }
    }

    // autoclose even if button is used
    pub fn autoclose(&mut self) {
        self.autoclose = true;
    }

    pub fn start(&mut self, ctx: &mut EventCtx) {
        self.text.request_complete_repaint(ctx);
        self.headline.request_complete_repaint(ctx);
        self.buttons.request_complete_repaint(ctx);
        self.result_anim.mutate(ctx, |ctx, c| {
            let now = Instant::now();
            c.start_growing(ctx, now);
        });
        ctx.request_paint();
    }
}

impl<T> Component for ResultPopup<T>
where
    T: StringType + Clone,
{
    type Msg = ResultPopupMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;

        let anim_margins = (screen().width() - ANIM_SIZE) / 2;
        let mut anim_adjust = 0;
        let mut headline_height = 0;
        let mut button_height = 0;

        if let Some(h) = self.headline.as_mut() {
            headline_height = h.max_size().y;
            anim_adjust += ANIM_POS_ADJ_HEADLINE;
        }
        if self.buttons.is_some() {
            button_height = theme::BUTTON_HEIGHT;
            anim_adjust += ANIM_POS_ADJ_BUTTON;
        }

        let (_, rest) = bounds.split_top(ANIM_POS - anim_adjust);
        let (anim, rest) = rest.split_top(ANIM_SIZE);
        let (_, rest) = rest.split_top(ANIM_SPACE);
        let (headline, rest) = rest.split_top(headline_height);
        let (text, buttons) = rest.split_bottom(button_height);

        self.pad.place(bounds);
        self.buttons.place(buttons);
        self.headline.place(headline);
        self.text.place(text);
        self.result_anim
            .place(anim.inset(Insets::sides(anim_margins)));

        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let mut button_confirmed = false;

        self.text.event(ctx, event);
        self.headline.event(ctx, event);

        if let Some(ButtonControllerMsg::Triggered(ButtonPos::Right, _)) =
            self.buttons.event(ctx, event)
        {
            button_confirmed = true;
        }

        if let Some(ResultAnimMsg::FullyGrown) = self.result_anim.event(ctx, event) {
            if self.buttons.is_none() || self.autoclose {
                return Some(ResultPopupMsg::Confirmed);
            }
        }

        if button_confirmed {
            return Some(ResultPopupMsg::Confirmed);
        }

        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.text.paint();
        self.buttons.paint();
        self.headline.paint();
        self.result_anim.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ResultPopup<T>
where
    T: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ResultPopup");
        t.child("text", &self.text);
        if let Some(button) = &self.buttons {
            t.child("button", button);
        }
        if let Some(headline) = &self.headline {
            t.child("headline", headline);
        }
        t.child("result_anim", &self.result_anim);
    }
}
