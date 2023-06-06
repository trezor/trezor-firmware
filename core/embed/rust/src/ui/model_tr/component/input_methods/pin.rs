use crate::{
    strutil::StringType,
    trezorhal::random,
    ui::{
        component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
        display::Icon,
        geometry::Rect,
    },
};

use super::super::{
    theme, ButtonDetails, ButtonLayout, CancelConfirmMsg, ChangingTextLine, ChoiceFactory,
    ChoiceItem, ChoicePage,
};
use heapless::String;

#[derive(Clone, Copy)]
enum PinAction {
    Delete,
    Show,
    Enter,
    Digit(char),
}

const MAX_PIN_LENGTH: usize = 50;

const CHOICE_LENGTH: usize = 13;
const NUMBER_START_INDEX: usize = 3;
const CHOICES: [(&str, PinAction, Option<Icon>); CHOICE_LENGTH] = [
    ("DELETE", PinAction::Delete, Some(theme::ICON_DELETE)),
    ("SHOW", PinAction::Show, Some(theme::ICON_EYE)),
    ("ENTER", PinAction::Enter, Some(theme::ICON_TICK)),
    ("0", PinAction::Digit('0'), None),
    ("1", PinAction::Digit('1'), None),
    ("2", PinAction::Digit('2'), None),
    ("3", PinAction::Digit('3'), None),
    ("4", PinAction::Digit('4'), None),
    ("5", PinAction::Digit('5'), None),
    ("6", PinAction::Digit('6'), None),
    ("7", PinAction::Digit('7'), None),
    ("8", PinAction::Digit('8'), None),
    ("9", PinAction::Digit('9'), None),
];

fn get_random_digit_position() -> usize {
    random::uniform_between(NUMBER_START_INDEX as u32, (CHOICE_LENGTH - 1) as u32) as usize
}

struct ChoiceFactoryPIN;

impl<T: StringType + Clone> ChoiceFactory<T> for ChoiceFactoryPIN {
    type Action = PinAction;
    type Item = ChoiceItem<T>;

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        let (choice_str, action, icon) = CHOICES[choice_index];

        let mut choice_item = ChoiceItem::new(choice_str, ButtonLayout::default_three_icons());

        // Action buttons have different middle button text
        if !matches!(action, PinAction::Digit(_)) {
            let confirm_btn = ButtonDetails::armed_text("CONFIRM".into());
            choice_item.set_middle_btn(Some(confirm_btn));
        }

        // Adding icons for appropriate items
        if let Some(icon) = icon {
            choice_item = choice_item.with_icon(icon);
        }

        (choice_item, action)
    }

    fn count(&self) -> usize {
        CHOICE_LENGTH
    }
}

/// Component for entering a PIN.
pub struct PinEntry<T: StringType + Clone> {
    choice_page: ChoicePage<ChoiceFactoryPIN, T, PinAction>,
    pin_line: Child<ChangingTextLine<String<MAX_PIN_LENGTH>>>,
    subprompt_line: Child<ChangingTextLine<T>>,
    prompt: T,
    show_real_pin: bool,
    textbox: TextBox<MAX_PIN_LENGTH>,
}

impl<T> PinEntry<T>
where
    T: StringType + Clone,
{
    pub fn new(prompt: T, subprompt: T) -> Self {
        let choices = ChoiceFactoryPIN;

        Self {
            // Starting at a random digit.
            choice_page: ChoicePage::new(choices)
                .with_initial_page_counter(get_random_digit_position())
                .with_carousel(true),
            pin_line: Child::new(ChangingTextLine::center_bold(String::from(prompt.as_ref()))),
            subprompt_line: Child::new(ChangingTextLine::center_mono(subprompt)),
            prompt,
            show_real_pin: false,
            textbox: TextBox::empty(),
        }
    }

    /// Performs overall update of the screen.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.update_header_info(ctx);
        ctx.request_paint();
    }

    /// Update the header information - (sub)prompt and visible PIN.
    /// If PIN is empty, showing prompt in `pin_line` and sub-prompt in the
    /// `subprompt_line`. Otherwise disabling the `subprompt_line` and showing
    /// the PIN - either in real numbers or masked in asterisks.
    fn update_header_info(&mut self, ctx: &mut EventCtx) {
        let show_prompts = self.is_empty();

        let text = if show_prompts {
            String::from(self.prompt.as_ref())
        } else if self.show_real_pin {
            String::from(self.pin())
        } else {
            // Showing asterisks and the last digit.
            let mut dots: String<MAX_PIN_LENGTH> = String::new();
            for _ in 0..self.textbox.len() - 1 {
                unwrap!(dots.push('*'));
            }
            let last_char = unwrap!(self.textbox.content().chars().last());
            unwrap!(dots.push(last_char));
            dots
        };

        // Force repaint of the whole header.
        // Putting the current text into the PIN line.
        self.pin_line.mutate(ctx, |ctx, pin_line| {
            pin_line.update_text(text);
            pin_line.request_complete_repaint(ctx);
        });
        // Showing subprompt only conditionally.
        self.subprompt_line.mutate(ctx, |ctx, subprompt_line| {
            subprompt_line.show_or_not(show_prompts);
            subprompt_line.request_complete_repaint(ctx);
        });
    }

    pub fn pin(&self) -> &str {
        self.textbox.content()
    }

    fn is_full(&self) -> bool {
        self.textbox.is_full()
    }

    fn is_empty(&self) -> bool {
        self.textbox.is_empty()
    }
}

impl<T> Component for PinEntry<T>
where
    T: StringType + Clone,
{
    type Msg = CancelConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let pin_height = self.pin_line.inner().needed_height();
        let subtitle_height = self.subprompt_line.inner().needed_height();
        let (title_area, subtitle_and_choice_area) = bounds.split_top(pin_height);
        let (subtitle_area, choice_area) = subtitle_and_choice_area.split_top(subtitle_height);
        self.pin_line.place(title_area);
        self.subprompt_line.place(subtitle_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Any event when showing real PIN should hide it
        if self.show_real_pin {
            self.show_real_pin = false;
            self.update(ctx)
        }

        match self.choice_page.event(ctx, event) {
            Some(PinAction::Delete) => {
                self.textbox.delete_last(ctx);
                self.update(ctx);
                None
            }
            Some(PinAction::Show) => {
                self.show_real_pin = true;
                self.update(ctx);
                None
            }
            Some(PinAction::Enter) => Some(CancelConfirmMsg::Confirmed),
            Some(PinAction::Digit(ch)) if !self.is_full() => {
                self.textbox.append(ctx, ch);
                // Choosing random digit to be shown next
                self.choice_page
                    .set_page_counter(ctx, get_random_digit_position());
                self.update(ctx);
                None
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        self.pin_line.paint();
        self.subprompt_line.paint();
        self.choice_page.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for PinEntry<T>
where
    T: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PinKeyboard");
        t.string("prompt", self.prompt.as_ref());
        let subprompt = self.subprompt_line.inner().get_text();
        if !subprompt.as_ref().is_empty() {
            t.string("subprompt", subprompt.as_ref());
        }
        t.string("pin", self.textbox.content());
        t.child("choice_page", &self.choice_page);
    }
}
