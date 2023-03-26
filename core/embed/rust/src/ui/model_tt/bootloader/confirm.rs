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
            button_bld_menu, BUTTON_AREA_START, CLOSE, CONTENT_PADDING, CORNER_BUTTON_AREA,
            INFO_SMALL, TEXT_TITLE, TITLE_AREA,
        },
        component::{Button, ButtonMsg::Clicked},
        constant::WIDTH,
        theme::WHITE,
    },
};

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
    title: Option<Child<Label<&'static str>>>,
    message: Child<Paragraphs<ParagraphVecShort<&'a str>>>,
    left: Child<Button<&'static str>>,
    right: Child<Button<&'static str>>,
    info_button: Option<Button<&'static str>>,
    close_button: Option<Button<&'static str>>,
    info_title: Option<Child<Label<&'static str>>>,
    info_text: Option<Paragraphs<ParagraphVecShort<&'a str>>>,
    show_info: bool,

    confirm_left: bool,
}

impl<'a> Confirm<'a> {
    pub fn new(
        bg_color: Color,
        icon: Option<Icon>,
        left: Button<&'static str>,
        right: Button<&'static str>,
        confirm_left: bool,
        confirm: (Option<&'static str>, Paragraphs<ParagraphVecShort<&'a str>>),
        info: Option<(&'static str, Paragraphs<ParagraphVecShort<&'a str>>)>,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(bg_color),
            content_pad: Pad::with_background(bg_color),
            bg_color,
            icon,
            message: Child::new(confirm.1),
            left: Child::new(left),
            right: Child::new(right),
            close_button: None,
            info_button: None,
            info_title: None,
            info_text: None,
            confirm_left,
            show_info: false,
            title: confirm
                .0
                .map(|title| Child::new(Label::new(title, Alignment::Start, TEXT_TITLE))),
        };
        if let Some((title, text)) = info {
            instance.info_title = Some(Child::new(Label::new(title, Alignment::Start, TEXT_TITLE)));
            instance.info_text = Some(text);
            instance.info_button = Some(
                Button::with_icon(Icon::new(INFO_SMALL))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(13)),
            );
            instance.close_button = Some(
                Button::with_icon(Icon::new(CLOSE))
                    .styled(button_bld_menu())
                    .with_expanded_touch_area(Insets::uniform(13)),
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
        let icon_height = if let Some(icon) = self.icon {
            icon.toif.height()
        } else {
            0
        };
        self.message.place(Rect::new(
            Point::new(CONTENT_PADDING, 32 + icon_height),
            Point::new(WIDTH - CONTENT_PADDING, BUTTON_AREA_START),
        ));

        let button_size = Offset::new(106, 38);
        self.left.place(Rect::from_top_left_and_size(
            Point::new(CONTENT_PADDING, BUTTON_AREA_START),
            button_size,
        ));
        self.right.place(Rect::from_top_left_and_size(
            Point::new(124, BUTTON_AREA_START),
            button_size,
        ));
        self.info_button.place(CORNER_BUTTON_AREA);
        self.close_button.place(CORNER_BUTTON_AREA);
        self.info_title.place(TITLE_AREA);
        self.title.place(TITLE_AREA);
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
        if let Some(Clicked) = self.left.event(ctx, event) {
            return if self.confirm_left {
                Some(Self::Msg::Confirm)
            } else {
                Some(Self::Msg::Cancel)
            };
        };
        if let Some(Clicked) = self.right.event(ctx, event) {
            return if self.confirm_left {
                Some(Self::Msg::Cancel)
            } else {
                Some(Self::Msg::Confirm)
            };
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
            self.left.paint();
            self.right.paint();
        } else {
            self.info_button.paint();
            self.title.paint();
            self.message.paint();
            self.left.paint();
            self.right.paint();
            if let Some(icon) = self.icon {
                icon.draw(
                    Point::new(screen().center().x, 32),
                    TOP_CENTER,
                    WHITE,
                    self.bg_color,
                );
            }
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.left.bounds(sink);
        self.right.bounds(sink);
    }
}
