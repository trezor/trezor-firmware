use crate::ui::{
    component::{Child, Component, ComponentExt, Event, EventCtx, Label, Pad},
    constant,
    constant::screen,
    display::{Color, Icon},
    geometry::{Alignment2D, Insets, Offset, Point, Rect},
    model_tt::{
        bootloader::theme::{
            button_bld_menu, BUTTON_AREA_START, BUTTON_HEIGHT, CONTENT_PADDING, CORNER_BUTTON_AREA,
            CORNER_BUTTON_TOUCH_EXPANSION, INFO32, TEXT_FINGERPRINT, TEXT_TITLE, TITLE_AREA, X32,
        },
        component::{Button, ButtonMsg::Clicked},
        constant::WIDTH,
        theme::WHITE,
    },
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

pub enum ConfirmTitle<'a> {
    Text(Label<&'a str>),
    Icon(Icon),
}

pub struct ConfirmInfo<'a> {
    pub title: Child<Label<&'a str>>,
    pub text: Child<Label<&'a str>>,
    pub info_button: Child<Button<&'static str>>,
    pub close_button: Child<Button<&'static str>>,
}

pub struct Confirm<'a> {
    bg: Pad,
    content_pad: Pad,
    bg_color: Color,
    title: ConfirmTitle<'a>,
    message: Child<Label<&'a str>>,
    alert: Option<Child<Label<&'a str>>>,
    left_button: Child<Button<&'static str>>,
    right_button: Child<Button<&'static str>>,
    info: Option<ConfirmInfo<'a>>,
    show_info: bool,
}

impl<'a> Confirm<'a> {
    pub fn new(
        bg_color: Color,
        left_button: Button<&'static str>,
        right_button: Button<&'static str>,
        title: ConfirmTitle<'a>,
        message: Label<&'a str>,
        alert: Option<Label<&'a str>>,
        info: Option<(&'a str, &'a str)>,
    ) -> Self {
        Self {
            bg: Pad::with_background(bg_color).with_clear(),
            content_pad: Pad::with_background(bg_color),
            bg_color,
            title,
            message: Child::new(message.vertically_centered()),
            alert: alert.map(|alert| Child::new(alert.vertically_centered())),
            left_button: Child::new(left_button),
            right_button: Child::new(right_button),
            info: info.map(|(title, text)| ConfirmInfo {
                title: Child::new(Label::left_aligned(title, TEXT_TITLE).vertically_centered()),
                text: Child::new(Label::left_aligned(text, TEXT_FINGERPRINT).vertically_centered()),
                info_button: Child::new(
                    Button::with_icon(Icon::new(INFO32))
                        .styled(button_bld_menu())
                        .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
                ),
                close_button: Child::new(
                    Button::with_icon(Icon::new(X32))
                        .styled(button_bld_menu())
                        .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
                ),
            }),
            show_info: false,
        }
    }
}

impl<'a> Component for Confirm<'a> {
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

    fn paint(&mut self) {
        self.bg.paint();
        self.content_pad.paint();

        if let Some(info) = self.info.as_mut() {
            if self.show_info {
                info.close_button.paint();
                info.title.paint();
                info.text.paint();
                self.left_button.paint();
                self.right_button.paint();
                // short-circuit before painting the main components
                return;
            } else {
                info.info_button.paint();
                // pass through to the rest of the paint
            }
        }

        self.message.paint();
        self.alert.paint();
        self.left_button.paint();
        self.right_button.paint();
        match &mut self.title {
            ConfirmTitle::Text(label) => label.paint(),
            ConfirmTitle::Icon(icon) => {
                icon.draw(
                    Point::new(screen().center().x, ICON_TOP),
                    Alignment2D::TOP_CENTER,
                    WHITE,
                    self.bg_color,
                );
            }
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.left_button.bounds(sink);
        self.right_button.bounds(sink);
    }
}
