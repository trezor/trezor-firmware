use crate::{
    time::Duration,
    ui::{
        component::{Component, Event, EventCtx},
        display::Color,
        geometry::{Alignment2D, Offset, Rect},
        shape,
        shape::Renderer,
    },
};

use super::{theme, Button, ButtonContent, ButtonMsg};

const HOLD_DURATION_MS: u32 = 1000;
const BUTTON_SIZE: i16 = 110;

/// Component requesting an action from a user. Most typically embedded as a
/// content of a Frame and promptin "Tap to confirm" or "Hold to XYZ".
#[derive(Clone)]
pub struct PromptScreen {
    area: Rect,
    button: Button,
    circle_color: Color,
    circle_pad_color: Color,
    circle_inner_color: Color,
    dismiss_type: DismissType,
}

#[derive(Clone)]
enum DismissType {
    Tap,
    Hold,
}

impl PromptScreen {
    pub fn new_hold_to_confirm() -> Self {
        let icon = theme::ICON_SIGN;
        let button = Button::new(ButtonContent::Icon(icon))
            .styled(theme::button_default())
            .with_long_press(Duration::from_millis(HOLD_DURATION_MS));
        Self {
            area: Rect::zero(),
            circle_color: theme::GREEN,
            circle_pad_color: theme::GREY_EXTRA_DARK,
            circle_inner_color: theme::GREEN_LIGHT,
            dismiss_type: DismissType::Hold,
            button,
        }
    }

    pub fn new_tap_to_confirm() -> Self {
        let icon = theme::ICON_SIMPLE_CHECKMARK;
        let button = Button::new(ButtonContent::Icon(icon)).styled(theme::button_default());
        Self {
            area: Rect::zero(),
            circle_color: theme::GREEN,
            circle_inner_color: theme::GREEN,
            circle_pad_color: theme::GREY_EXTRA_DARK,
            dismiss_type: DismissType::Tap,
            button,
        }
    }

    pub fn new_tap_to_cancel() -> Self {
        let icon = theme::ICON_SIMPLE_CHECKMARK;
        let button = Button::new(ButtonContent::Icon(icon)).styled(theme::button_default());
        Self {
            area: Rect::zero(),
            circle_color: theme::ORANGE_LIGHT,
            circle_inner_color: theme::ORANGE_LIGHT,
            circle_pad_color: theme::GREY_EXTRA_DARK,
            dismiss_type: DismissType::Tap,
            button,
        }
    }
}

impl Component for PromptScreen {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.button.place(Rect::snap(
            self.area.center(),
            Offset::uniform(BUTTON_SIZE),
            Alignment2D::CENTER,
        ));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let btn_msg = self.button.event(ctx, event);
        match (&self.dismiss_type, btn_msg) {
            (DismissType::Tap, Some(ButtonMsg::Clicked)) => {
                return Some(());
            }
            (DismissType::Hold, Some(ButtonMsg::LongPressed)) => {
                return Some(());
            }
            _ => (),
        }
        None
    }

    fn paint(&mut self) {
        todo!()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        shape::Circle::new(self.area.center(), 70)
            .with_fg(self.circle_pad_color)
            .with_bg(theme::BLACK)
            .with_thickness(20)
            .render(target);
        shape::Circle::new(self.area.center(), 50)
            .with_fg(self.circle_color)
            .with_bg(theme::BLACK)
            .with_thickness(2)
            .render(target);
        shape::Circle::new(self.area.center(), 48)
            .with_fg(self.circle_pad_color)
            .with_bg(theme::BLACK)
            .with_thickness(8)
            .render(target);
        matches!(self.dismiss_type, DismissType::Hold).then(|| {
            shape::Circle::new(self.area.center(), 40)
                .with_fg(self.circle_inner_color)
                .with_bg(theme::BLACK)
                .with_thickness(2)
                .render(target);
        });
        self.button.render_content(target, self.button.style());
    }
}

#[cfg(feature = "micropython")]
impl crate::ui::flow::Swipable<()> for PromptScreen {}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PromptScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PromptScreen");
        t.child("button", &self.button);
    }
}
