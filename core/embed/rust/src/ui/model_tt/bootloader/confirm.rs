use crate::ui::{
    component::{
        text::paragraphs::{ParagraphVecShort, Paragraphs},
        Child, Component, ComponentExt, Event, EventCtx, Label, Pad,
    },
    constant,
    constant::screen,
    display::{Color, Icon},
    geometry::{Alignment, Insets, Offset, Point, Rect, TOP_CENTER},
    model_tt::{
        bootloader::theme::{
            button_bld_menu, BUTTON_AREA_START, BUTTON_HEIGHT, CONTENT_PADDING, CORNER_BUTTON_AREA,
            CORNER_BUTTON_TOUCH_EXPANSION, INFO32, TEXT_TITLE, TITLE_AREA, TITLE_Y_ADJUSTMENT, X32,
        },
        component::{Button, ButtonMsg::Clicked},
        constant::WIDTH,
        theme::WHITE,
    },
};

const ICON_TOP: i16 = 17;
const CONTENT_START_WITH_ICON: i16 = 40 + CONTENT_PADDING;
const CONTENT_START: i16 = 58;

#[derive(Copy, Clone, ToPrimitive)]
pub enum ConfirmMsg {
    Cancel = 1,
    Confirm = 2,
}

pub struct Confirm<'a> {
    bg: Pad,
    content_pad: Pad,
    bg_color: Color,
    icon: Option<Icon>,
    title: Option<Child<Label<&'a str>>>,
    message: Child<Label<&'a str>>,
    alert: Option<Child<Label<&'a str>>>,
    left_button: Child<Button<&'static str>>,
    right_button: Child<Button<&'static str>>,
    info_button: Option<Button<&'static str>>,
    close_button: Option<Button<&'static str>>,
    info_title: Option<Child<Label<&'static str>>>,
    info_text: Option<Child<Paragraphs<ParagraphVecShort<&'a str>>>>,
    show_info: bool,
}

impl<'a> Confirm<'a> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        bg_color: Color,
        icon: Option<Icon>,
        left_button: Button<&'static str>,
        right_button: Button<&'static str>,
        title: Option<Label<&'a str>>,
        msg: Label<&'a str>,
        alert: Option<Label<&'a str>>,
        info: Option<(&'static str, Paragraphs<ParagraphVecShort<&'a str>>)>,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            content_pad: Pad::with_background(bg_color),
            bg_color,
            icon,
            title: title.map(Child::new),
            message: Child::new(msg),
            alert: alert.map(Child::new),
            left_button: Child::new(left_button),
            right_button: Child::new(right_button),
            close_button: None,
            info_button: None,
            info_title: None,
            info_text: None,
            show_info: false,
        };
        if let Some((title, text)) = info {
            instance.info_title = Some(Child::new(Label::new(title, Alignment::Start, TEXT_TITLE)));
            instance.info_text = Some(text.into_child());
            instance.info_button = Some(
                Button::with_icon(Icon::new(INFO32))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
            );
            instance.close_button = Some(
                Button::with_icon(Icon::new(X32))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(CORNER_BUTTON_TOUCH_EXPANSION)),
            );
        }
        instance.bg.clear();
        instance
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

        let content_area_start = if self.icon.is_some() {
            CONTENT_START_WITH_ICON
        } else {
            CONTENT_START
        };

        let content_area = Rect::new(
            Point::new(CONTENT_PADDING, content_area_start),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
        );

        self.message.place(content_area);
        let message_height = self.message.inner().area().height();

        if let Some(alert) = &mut self.alert {
            alert.place(content_area);
            let alert_height = alert.inner().area().height();

            let space_height = (content_area.height() - message_height - alert_height) / 3;

            self.message.place(Rect::new(
                Point::new(CONTENT_PADDING, content_area_start + space_height),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START),
            ));
            self.alert.place(Rect::new(
                Point::new(
                    CONTENT_PADDING,
                    content_area_start + 2 * space_height + message_height,
                ),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START),
            ));
        } else {
            self.message.place(Rect::new(
                Point::new(
                    CONTENT_PADDING,
                    content_area.center().y - (message_height / 2),
                ),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
            ));
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
        self.info_button.place(CORNER_BUTTON_AREA);
        self.close_button.place(CORNER_BUTTON_AREA);

        if let Some(title) = self.info_title.as_mut() {
            title.place(TITLE_AREA);
            let title_height = title.inner().area().height();

            title.place(Rect::new(
                Point::new(
                    CONTENT_PADDING,
                    TITLE_AREA.center().y - (title_height / 2) - TITLE_Y_ADJUSTMENT,
                ),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
            ));
        }

        if let Some(title) = self.title.as_mut() {
            title.place(TITLE_AREA);
            let title_height = title.inner().area().height();

            title.place(Rect::new(
                Point::new(
                    CONTENT_PADDING,
                    TITLE_AREA.center().y - (title_height / 2) - TITLE_Y_ADJUSTMENT,
                ),
                Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START - CONTENT_PADDING),
            ));
        }

        self.info_text.place(Rect::new(
            Point::new(CONTENT_PADDING, TITLE_AREA.y1),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START),
        ));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if self.show_info {
            if let Some(Clicked) = self.close_button.event(ctx, event) {
                self.show_info = false;
                self.content_pad.clear();
                self.title.request_complete_repaint(ctx);
                self.message.request_complete_repaint(ctx);
                return None;
            }
        } else if let Some(Clicked) = self.info_button.event(ctx, event) {
            self.show_info = true;
            self.info_text.request_complete_repaint(ctx);
            self.info_title.request_complete_repaint(ctx);
            self.content_pad.clear();
            return None;
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

        if self.show_info {
            self.close_button.paint();
            self.info_title.paint();
            self.info_text.paint();
            self.left_button.paint();
            self.right_button.paint();
        } else {
            self.info_button.paint();
            self.title.paint();
            self.message.paint();
            self.alert.paint();
            self.left_button.paint();
            self.right_button.paint();
            if let Some(icon) = self.icon {
                icon.draw(
                    Point::new(screen().center().x, ICON_TOP),
                    TOP_CENTER,
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
