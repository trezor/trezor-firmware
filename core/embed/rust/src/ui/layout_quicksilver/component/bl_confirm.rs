use crate::{
    strutil::TString,
    ui::{
        component::{Child, Component, ComponentExt, Event, EventCtx, Label, Pad},
        constant,
        constant::screen,
        display::{Color, Icon},
        geometry::{Alignment2D, Insets, Offset, Point, Rect},
        shape,
        shape::Renderer,
    },
};

use super::{
    constant::WIDTH,
    theme::{
        bootloader::{
            text_fingerprint, text_title, BUTTON_AREA_START, BUTTON_HEIGHT, CONTENT_PADDING,
            CORNER_BUTTON_AREA, CORNER_BUTTON_TOUCH_EXPANSION, INFO32, TITLE_AREA, X32,
        },
        WHITE,
    },
    Button,
    ButtonMsg::Clicked,
    ButtonStyleSheet,
};

const ICON_TOP: i16 = 17;
const CONTENT_START: i16 = 72;

const CONTENT_AREA: Rect = Rect::new(
    Point::new(CONTENT_PADDING, CONTENT_START),
    Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
);

#[derive(Copy, Clone, ToPrimitive)]
pub enum ConfirmMsg {
    Cancel = 1,
    Confirm = 2,
}

pub enum ConfirmTitle {
    Text(Label<'static>),
    Icon(Icon),
}

pub struct ConfirmInfo<'a> {
    pub title: Child<Label<'a>>,
    pub text: Child<Label<'a>>,
    pub info_button: Child<Button>,
    pub close_button: Child<Button>,
}

pub struct Confirm<'a> {
    bg: Pad,
    content_pad: Pad,
    bg_color: Color,
    title: ConfirmTitle,
    message: Child<Label<'a>>,
    alert: Option<Child<Label<'static>>>,
    left_button: Child<Button>,
    right_button: Child<Button>,
    info: Option<ConfirmInfo<'a>>,
    show_info: bool,
}

impl<'a> Confirm<'a> {
    pub fn new(
        bg_color: Color,
        left_button: Button,
        right_button: Button,
        title: ConfirmTitle,
        message: Label<'a>,
    ) -> Self {
        Self {
            bg: Pad::with_background(bg_color).with_clear(),
            content_pad: Pad::with_background(bg_color),
            bg_color,
            title,
            message: Child::new(message.vertically_centered()),
            left_button: Child::new(left_button),
            right_button: Child::new(right_button),
            alert: None,
            info: None,
            show_info: false,
        }
    }

    pub fn with_alert(mut self, alert: Label<'static>) -> Self {
        self.alert = Some(Child::new(alert.vertically_centered()));
        self
    }

    pub fn with_info(
        mut self,
        title: TString<'a>,
        text: TString<'a>,
        menu_button: ButtonStyleSheet,
    ) -> Self {
        self.info = Some(ConfirmInfo {
            title: Child::new(
                Label::left_aligned(title, text_title(self.bg_color)).vertically_centered(),
            ),
            text: Child::new(
                Label::left_aligned(text, text_fingerprint(self.bg_color)).vertically_centered(),
            ),
            info_button: Child::new(
                Button::with_icon(Icon::new(INFO32))
                    .styled(menu_button)
                    .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
            ),
            close_button: Child::new(
                Button::with_icon(Icon::new(X32))
                    .styled(menu_button)
                    .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
            ),
        });
        self
    }
}

impl Component for Confirm<'_> {
    type Msg = ConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg.place(constant::screen());
        self.content_pad.place(Rect::new(
            Point::zero(),
            Point::new(WIDTH, BUTTON_AREA_START),
        ));

        let mut content_area = CONTENT_AREA;

        match &mut self.title {
            ConfirmTitle::Icon(_) => {
                // XXX HACK: when icon is present (wipe device screen), we know the
                // string is long and we need to go outside the content padding
                content_area = content_area.inset(Insets::sides(-CONTENT_PADDING));
            }
            ConfirmTitle::Text(title) => {
                title.place(TITLE_AREA);
            }
        };

        if self.alert.is_some() {
            let message_height = self.message.inner().text_height(content_area.width());
            self.message.place(Rect::from_top_left_and_size(
                content_area.top_left(),
                Offset::new(content_area.width(), message_height),
            ));

            let (_, alert_bounds) = content_area.split_top(message_height);

            self.alert.place(alert_bounds);
        } else {
            self.message.place(content_area);
        }

        let button_size = Offset::new((WIDTH - 3 * CONTENT_PADDING) / 2, BUTTON_HEIGHT);
        self.left_button.place(Rect::from_top_left_and_size(
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            button_size,
        ));
        self.right_button.place(Rect::from_top_left_and_size(
            Point::new(2 * CONTENT_PADDING + button_size.x, BUTTON_AREA_START),
            button_size,
        ));

        if let Some(info) = self.info.as_mut() {
            info.info_button.place(CORNER_BUTTON_AREA);
            info.close_button.place(CORNER_BUTTON_AREA);
            info.title.place(TITLE_AREA);
            info.text.place(Rect::new(
                Point::new(CONTENT_PADDING, TITLE_AREA.y1),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START),
            ));
        }
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(info) = self.info.as_mut() {
            if self.show_info {
                if let Some(Clicked) = info.close_button.event(ctx, event) {
                    self.show_info = false;
                    self.content_pad.clear();
                    self.message.request_complete_repaint(ctx);
                    self.alert.request_complete_repaint(ctx);
                    return None;
                }
            } else if let Some(Clicked) = info.info_button.event(ctx, event) {
                self.show_info = true;
                info.text.request_complete_repaint(ctx);
                info.title.request_complete_repaint(ctx);
                self.content_pad.clear();
                return None;
            }
        }
        if let Some(Clicked) = self.left_button.event(ctx, event) {
            return Some(Self::Msg::Cancel);
        };
        if let Some(Clicked) = self.right_button.event(ctx, event) {
            return Some(Self::Msg::Confirm);
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.bg.render(target);
        self.content_pad.render(target);

        if let Some(info) = self.info.as_ref() {
            if self.show_info {
                info.close_button.render(target);
                info.title.render(target);
                info.text.render(target);
                self.left_button.render(target);
                self.right_button.render(target);
                // short-circuit before painting the main components
                return;
            } else {
                info.info_button.render(target);
                // pass through to the rest of the paint
            }
        }

        self.message.render(target);
        self.alert.render(target);
        self.left_button.render(target);
        self.right_button.render(target);
        match &self.title {
            ConfirmTitle::Text(label) => label.render(target),
            ConfirmTitle::Icon(icon) => {
                shape::ToifImage::new(Point::new(screen().center().x, ICON_TOP), icon.toif)
                    .with_align(Alignment2D::TOP_CENTER)
                    .with_fg(WHITE)
                    .render(target);
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Confirm<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("BlConfirm");
    }
}
