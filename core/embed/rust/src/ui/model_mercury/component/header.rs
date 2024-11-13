use crate::{
    strutil::TString,
    time::{Duration, Stopwatch},
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, FlowMsg, Label},
        display::{Color, Icon},
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        lerp::Lerp,
        model_mercury::{
            component::{Button, ButtonMsg, ButtonStyleSheet},
            theme::{self, TITLE_HEIGHT},
        },
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

const ANIMATION_TIME_MS: u32 = 1000;

#[derive(Default, Clone)]
struct AttachAnimation {
    pub timer: Stopwatch,
}

impl AttachAnimation {
    pub fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer
            .is_running_within(Duration::from_millis(ANIMATION_TIME_MS))
    }

    pub fn eval(&self) -> f32 {
        if animation_disabled() {
            return ANIMATION_TIME_MS as f32 / 1000.0;
        }
        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    pub fn get_title_offset(&self, t: f32) -> i16 {
        let fnc = pareen::constant(0.0).seq_ease_in_out(
            0.8,
            easer::functions::Cubic,
            0.2,
            pareen::constant(1.0),
        );
        i16::lerp(0, 25, fnc.eval(t))
    }

    pub fn start(&mut self) {
        self.timer.start();
    }

    pub fn reset(&mut self) {
        self.timer = Stopwatch::new_stopped();
    }
}

const BUTTON_EXPAND_BORDER: i16 = 32;

pub struct Header {
    area: Rect,
    title: Label<'static>,
    subtitle: Option<Label<'static>>,
    button: Option<Button>,
    anim: Option<AttachAnimation>,
    icon: Option<Icon>,
    color: Option<Color>,
    title_style: TextStyle,
    button_msg: FlowMsg,
}

impl Header {
    pub const fn new(alignment: Alignment, title: TString<'static>) -> Self {
        Self {
            area: Rect::zero(),
            title: Label::new(title, alignment, theme::label_title_main()).vertically_centered(),
            subtitle: None,
            button: None,
            anim: None,
            icon: None,
            color: None,
            title_style: theme::label_title_main(),
            button_msg: FlowMsg::Cancelled,
        }
    }
    #[inline(never)]
    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        let style = theme::TEXT_SUB_GREY;
        self.title = self.title.top_aligned();
        self.subtitle = Some(Label::new(subtitle, self.title.alignment(), style));
        self
    }
    #[inline(never)]
    pub fn styled(mut self, style: TextStyle) -> Self {
        self.title_style = style;
        self.title = self.title.styled(style);
        self
    }
    #[inline(never)]
    pub fn subtitle_styled(mut self, style: TextStyle) -> Self {
        if let Some(subtitle) = self.subtitle.take() {
            self.subtitle = Some(subtitle.styled(style))
        }
        self
    }
    #[inline(never)]
    pub fn update_title(&mut self, ctx: &mut EventCtx, title: TString<'static>) {
        self.title.set_text(title);
        ctx.request_paint();
    }
    #[inline(never)]
    pub fn update_subtitle(
        &mut self,
        ctx: &mut EventCtx,
        new_subtitle: TString<'static>,
        new_style: Option<TextStyle>,
    ) {
        let style = new_style.unwrap_or(theme::TEXT_SUB_GREY);
        match &mut self.subtitle {
            Some(subtitle) => {
                subtitle.set_style(style);
                subtitle.set_text(new_subtitle);
            }
            None => {
                self.subtitle = Some(Label::new(new_subtitle, self.title.alignment(), style));
            }
        }
        ctx.request_paint();
    }

    #[inline(never)]
    pub fn with_button(mut self, icon: Icon, enabled: bool, msg: FlowMsg) -> Self {
        let touch_area = Insets::uniform(BUTTON_EXPAND_BORDER);
        self.button = Some(
            Button::with_icon(icon)
                .with_expanded_touch_area(touch_area)
                .initially_enabled(enabled)
                .styled(theme::button_default()),
        );
        self.button_msg = msg;
        self
    }
    #[inline(never)]

    pub fn button_styled(mut self, style: ButtonStyleSheet) -> Self {
        if self.button.is_some() {
            self.button = Some(self.button.unwrap().styled(style));
        }
        self
    }

    #[inline(never)]
    pub fn with_result_icon(mut self, icon: Icon, color: Color) -> Self {
        self.anim = Some(AttachAnimation::default());
        self.icon = Some(icon);
        self.color = Some(color);
        let mut title_style = self.title_style;
        title_style.text_color = color;
        self.styled(title_style)
    }
}

impl Component for Header {
    type Msg = FlowMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let header_area = if let Some(b) = &mut self.button {
            let (rest, button_area) = bounds.split_right(TITLE_HEIGHT);
            b.place(button_area);
            rest
        } else {
            bounds
        };

        if self.subtitle.is_some() {
            let title_area = self.title.place(header_area);
            let remaining = header_area.inset(Insets::top(title_area.height()));
            let _subtitle_area = self.subtitle.place(remaining);
        } else {
            self.title.place(header_area);
        }

        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.title.event(ctx, event);
        self.subtitle.event(ctx, event);

        if let Some(anim) = &mut self.anim {
            if let Event::Attach(_) = event {
                anim.start();
                ctx.request_paint();
                ctx.request_anim_frame();
            }
            if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
                if anim.is_active() {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                }
            }
        }

        if let Some(ButtonMsg::Clicked) = self.button.event(ctx, event) {
            return Some(self.button_msg.clone());
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let offset = if let Some(anim) = &self.anim {
            Offset::x(anim.get_title_offset(anim.eval()))
        } else {
            Offset::zero()
        };

        self.button.render(target);

        target.in_clip(self.area.split_left(offset.x).0, &|target| {
            if let Some(icon) = self.icon {
                let color = self.color.unwrap_or(theme::GREEN);
                shape::ToifImage::new(self.title.area().left_center(), icon.toif)
                    .with_fg(color)
                    .with_align(Alignment2D::CENTER_LEFT)
                    .render(target);
            }
        });

        target.with_origin(offset, &|target| {
            self.title.render(target);
            self.subtitle.render(target);
        });
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Header {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Header");
        t.child("title", &self.title);
        if let Some(subtitle) = &self.subtitle {
            t.child("subtitle", subtitle);
        }

        if let Some(button) = &self.button {
            t.child("button", button);
        }
    }
}
