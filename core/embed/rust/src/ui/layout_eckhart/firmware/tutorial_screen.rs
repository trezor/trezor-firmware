use crate::{
    time::Duration,
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeConfig, Component, Event, EventCtx, Label},
        flow::Swipable,
        geometry::{Alignment, Insets, Rect},
        shape::Renderer,
        util::{animation_disabled, Pager},
    },
};

use super::super::{
    component::Button,
    constant::SCREEN,
    cshape::{render_loader_indeterminate, ScreenBorder},
    firmware::{ActionBar, ActionBarMsg},
    theme,
};

const LOADER_SPEED: u16 = 2;
const ANIM_DURATION: Duration = Duration::from_secs(3);

pub enum TutorialWelcomeScreenMsg {
    Confirmed,
}

pub struct TutorialWelcomeScreen {
    text: Label<'static>,
    action_bar: ActionBar,
    /// Current value of the progress bar.
    value: u16,
    border: ScreenBorder,
}

impl TutorialWelcomeScreen {
    pub fn new() -> Self {
        Self {
            text: Label::new(
                TR::tutorial__welcome_safe7.into(),
                Alignment::Start,
                theme::firmware::TEXT_REGULAR,
            )
            .top_aligned(),
            action_bar: ActionBar::new_timeout(
                Button::with_text(TR::tutorial__tropic.into()),
                ANIM_DURATION,
            ),
            value: 0,
            border: ScreenBorder::new(theme::GREEN_LIME),
        }
    }
}

impl Component for TutorialWelcomeScreen {
    type Msg = TutorialWelcomeScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (rest, action_bar_area) = bounds.split_bottom(theme::ACTION_BAR_HEIGHT);
        let content_area = rest.inset(theme::SIDE_INSETS).inset(Insets::top(38));

        self.text.place(content_area);
        self.action_bar.place(action_bar_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ActionBarMsg::Confirmed) = self.action_bar.event(ctx, event) {
            return Some(TutorialWelcomeScreenMsg::Confirmed);
        }

        // TutorialWelcomeScreen reacts to ANIM_FRAME_TIMER
        match event {
            _ if animation_disabled() => {
                return None;
            }
            Event::Attach(_) => {
                ctx.request_anim_frame();
            }
            Event::Timer(EventCtx::ANIM_FRAME_TIMER) => {
                self.value = (self.value + LOADER_SPEED) % 1000;
                ctx.request_anim_frame();
                ctx.request_paint();
            }
            _ => {}
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let progress_val = self.value.min(1000);
        self.text.render(target);
        self.action_bar.render(target);
        render_loader_indeterminate(progress_val, &self.border, target);
    }
}

#[cfg(feature = "micropython")]
impl Swipable for TutorialWelcomeScreen {
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::new()
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TutorialWelcomeScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TutorialWelcomeScreen");
    }
}
