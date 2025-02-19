use crate::{
    trezorhal::random,
    ui::{
        component::{Component, Event, EventCtx, Maybe},
        geometry::{Alignment, Insets, Offset, Rect},
        shape::Renderer,
    },
};

use super::super::super::{
    component::button::{Button, ButtonContent, ButtonMsg, ButtonStyleSheet},
    constant::SCREEN,
    theme,
};

#[derive(PartialEq)]
pub enum KeypadButton {
    Key(usize),
    Erase,   // Represents an erase button.
    Cancel,  // Represents a cancel button.
    Confirm, // Represents a confirm button.
    Back,    // Represents a back(previous) button.
}

pub enum ButtonState {
    Enabled,
    Disabled,
    Hidden,
}

const KEYPAD_MAX_KEYS: usize = 10;
type KeypadKeys = [Maybe<Button>; KEYPAD_MAX_KEYS];

pub struct Keypad {
    back: Maybe<Button>,
    erase: Maybe<Button>,
    cancel: Maybe<Button>,
    confirm: Maybe<Button>,
    keys: KeypadKeys,
    pressed: Option<KeypadButton>,
}

#[derive(PartialEq, Debug, Copy, Clone)]
#[cfg_attr(feature = "ui_debug", derive(ufmt::derive::uDebug))]
pub enum KeypadMsg {
    Back,
    Confirm,
    EraseShort,
    EraseLong,
    Cancel,
    Key(usize),
}

impl Keypad {
    pub const MAX_KEYS: usize = KEYPAD_MAX_KEYS;
    const KEYBOARD_BUTTON_HEIGHT: i16 = 70;
    const KEYBOARD_BUTTON_RADIUS: u8 = 11;

    const ERASE_BUTTON_INDEX: usize = 9;
    const CONFIRM_BUTTON_INDEX: usize = 11;

    // Create a new keypad with numeric keys. The keys are shown and active and are
    // shuffled if `shuffle` is true. The special buttons are hidden.
    pub fn new_numeric(shuffle: bool) -> Self {
        let mut digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"];
        // Shuffle if requested
        if shuffle {
            random::shuffle(&mut digits);
        }
        let keypad_content: [_; KEYPAD_MAX_KEYS] =
            core::array::from_fn(|i| ButtonContent::Text(digits[i].into()));

        Self::new_inner(true, true, theme::button_keyboard_numeric())
            .with_keys_content(&keypad_content)
    }

    // Create a new keypad with empty keys. The keys and special buttons are hidden.
    pub fn new_hidden() -> Self {
        Self::new_inner(false, false, theme::button_keyboard())
    }

    // Create a new keypad with empty keys. The keys are shown and the special
    // buttons are hidden.
    pub fn new_shown() -> Self {
        Self::new_inner(true, true, theme::button_keyboard())
    }

    fn new_inner(enabled: bool, visible: bool, styles: ButtonStyleSheet) -> Self {
        Self {
            // Special buttons are hidden by default.
            back: Maybe::hidden(
                theme::BG,
                Button::with_icon(theme::ICON_CHEVRON_LEFT)
                    .styled(theme::button_keyboard_numeric())
                    .with_radius(Self::KEYBOARD_BUTTON_RADIUS)
                    .initially_enabled(false),
            ),
            cancel: Maybe::hidden(
                theme::BG,
                Button::with_icon(theme::ICON_CROSS)
                    .styled(theme::button_cancel())
                    .with_radius(Self::KEYBOARD_BUTTON_RADIUS)
                    .initially_enabled(false),
            ),
            confirm: Maybe::hidden(
                theme::BG,
                Button::with_icon(theme::ICON_CHECKMARK)
                    .styled(theme::button_keyboard_confirm())
                    .with_radius(Self::KEYBOARD_BUTTON_RADIUS)
                    .initially_enabled(false),
            ),
            erase: Maybe::hidden(
                theme::BG,
                Button::with_icon(theme::ICON_DELETE)
                    .styled(theme::button_keyboard())
                    .with_long_press(theme::ERASE_HOLD_DURATION)
                    .with_radius(Self::KEYBOARD_BUTTON_RADIUS)
                    .initially_enabled(false),
            ),
            // Initialize all keys with empty content
            keys: core::array::from_fn(|_idx| {
                let inner = Button::empty()
                    .with_radius(Self::KEYBOARD_BUTTON_RADIUS)
                    .styled(styles)
                    .with_text_align(Alignment::Center)
                    .initially_enabled(enabled);
                Maybe::new(theme::BG, inner, visible)
            }),
            pressed: None,
        }
    }

    // Set the content of all keyboard keys.
    pub fn with_keys_content(mut self, keypad_content: &[ButtonContent]) -> Self {
        // Make sure the content fits the keypad.
        debug_assert!(keypad_content.len() <= Self::MAX_KEYS);

        for (i, key_content) in keypad_content.into_iter().enumerate() {
            self.keys[i].inner_mut().set_content(key_content.clone());
        }
        self
    }

    // Get the content of a key at the specified index.
    pub fn get_key_content(&self, idx: usize) -> &ButtonContent {
        // Make sure the index is within bounds.
        debug_assert!(idx < Self::MAX_KEYS);

        &self.keys[idx].inner().content()
    }

    // Set the content of a key at the specified index.
    pub fn set_key_content(&mut self, idx: usize, content: ButtonContent) {
        // Make sure the index is within bounds.
        debug_assert!(idx < Self::MAX_KEYS);

        self.keys[idx].inner_mut().set_content(content);
    }

    pub fn set_button_stylesheet(&mut self, button: KeypadButton, styles: ButtonStyleSheet) {
        let apply_state = |btn: &mut Maybe<Button>, styles: ButtonStyleSheet| {
            btn.inner_mut().set_stylesheet(styles);
        };

        match button {
            KeypadButton::Key(idx) => apply_state(&mut self.keys[idx], styles),
            KeypadButton::Erase => apply_state(&mut self.erase, styles),
            KeypadButton::Cancel => apply_state(&mut self.cancel, styles),
            KeypadButton::Confirm => apply_state(&mut self.confirm, styles),
            KeypadButton::Back => apply_state(&mut self.back, styles),
        }
    }

    fn apply_button_state(btn: &mut Maybe<Button>, state: &ButtonState, ctx: &mut EventCtx) {
        match state {
            ButtonState::Enabled => {
                btn.show(ctx);
                btn.inner_mut().enable(ctx);
            }
            ButtonState::Disabled => {
                btn.show(ctx);
                btn.inner_mut().disable(ctx);
            }
            ButtonState::Hidden => {
                btn.hide(ctx);
            }
        }
    }

    // Set the state of all key buttons
    pub fn set_keys_state(&mut self, ctx: &mut EventCtx, state: &ButtonState) {
        for btn in self.keys.iter_mut() {
            Self::apply_button_state(btn, state, ctx);
        }
    }

    pub fn set_button_state(
        &mut self,
        ctx: &mut EventCtx,
        button: KeypadButton,
        state: &ButtonState,
    ) {
        match button {
            KeypadButton::Key(idx) => Self::apply_button_state(&mut self.keys[idx], state, ctx),
            KeypadButton::Erase => Self::apply_button_state(&mut self.erase, state, ctx),
            KeypadButton::Cancel => Self::apply_button_state(&mut self.cancel, state, ctx),
            KeypadButton::Confirm => Self::apply_button_state(&mut self.confirm, state, ctx),
            KeypadButton::Back => Self::apply_button_state(&mut self.back, state, ctx),
        }
    }

    fn render_button<'s>(btn: &'s Maybe<Button>, target: &mut impl Renderer<'s>) {
        if btn.is_visible() {
            btn.render(target);
        }
    }

    // Render the pressed button.
    // TODO: Render special shape for the edge buttons.
    fn render_pressed_button<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match self.pressed {
            Some(KeypadButton::Key(idx)) => {
                Self::render_button(&self.keys[idx], target);
            }
            Some(KeypadButton::Cancel) => {
                Self::render_button(&self.cancel, target);
            }
            Some(KeypadButton::Erase) => {
                Self::render_button(&self.erase, target);
            }
            Some(KeypadButton::Confirm) => {
                Self::render_button(&self.confirm, target);
            }
            Some(KeypadButton::Back) => {
                Self::render_button(&self.back, target);
            }
            None => {}
        }
    }

    // Convert key index to grid cell index.
    // Key with index 9 must be mapped after the cancel button.
    fn key_2_grid_cell(key: usize) -> usize {
        // Make sure the key is within bounds.
        debug_assert!(key < Self::MAX_KEYS);
        if key < 9 {
            key
        } else {
            key + 1
        }
    }
}

impl Component for Keypad {
    type Msg = KeypadMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen width
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let keypad_grid = KeypadGrid::new(bounds);

        // Decrease touch area for buttons.
        let erase_touch_inset = keypad_grid.insets_of_cell(Self::ERASE_BUTTON_INDEX);
        let confirm_touch_inset = keypad_grid.insets_of_cell(Self::CONFIRM_BUTTON_INDEX);

        self.erase
            .inner_mut()
            .set_expanded_touch_area(erase_touch_inset);
        self.cancel
            .inner_mut()
            .set_expanded_touch_area(erase_touch_inset);
        self.back
            .inner_mut()
            .set_expanded_touch_area(erase_touch_inset);
        self.confirm
            .inner_mut()
            .set_expanded_touch_area(confirm_touch_inset);

        for (i, btn) in self.keys.iter_mut().enumerate() {
            btn.inner_mut()
                .set_expanded_touch_area(keypad_grid.insets_of_cell(Self::key_2_grid_cell(i)));
        }

        // Place buttons
        let erase_area = keypad_grid.border_of_cell(Self::ERASE_BUTTON_INDEX);
        let confirm_area = keypad_grid.border_of_cell(Self::CONFIRM_BUTTON_INDEX);

        self.erase.place(erase_area);
        self.cancel.place(erase_area);
        self.back.place(erase_area);
        self.confirm.place(confirm_area);
        for (i, btn) in self.keys.iter_mut().enumerate() {
            btn.place(keypad_grid.border_of_cell(Self::key_2_grid_cell(i)));
        }
        bounds
    }
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let buttons = [
            (&mut self.confirm, KeypadButton::Confirm, KeypadMsg::Confirm),
            (&mut self.erase, KeypadButton::Erase, KeypadMsg::EraseShort),
            (&mut self.cancel, KeypadButton::Cancel, KeypadMsg::Cancel),
            (&mut self.back, KeypadButton::Back, KeypadMsg::Back),
        ];

        for (btn, btn_type, msg) in buttons {
            match btn.event(ctx, event) {
                // Detect click of all special buttons
                Some(ButtonMsg::Clicked) => {
                    self.pressed = None;
                    return Some(msg);
                }
                // Detect long press of the erase button
                Some(ButtonMsg::LongPressed) if btn_type == KeypadButton::Erase => {
                    self.pressed = None;
                    return Some(KeypadMsg::EraseLong);
                }
                // Detect press of all special buttons for rendering purposes
                Some(ButtonMsg::Pressed) => {
                    self.pressed = Some(btn_type);
                }
                _ => {}
            }
        }

        for (idx, btn) in self.keys.iter_mut().enumerate() {
            match btn.event(ctx, event) {
                // Detect click of all key buttons
                Some(ButtonMsg::Clicked) => {
                    self.pressed = None;
                    return Some(KeypadMsg::Key(idx));
                }
                // Detect press of all key buttons for rendering purposes
                Some(ButtonMsg::Pressed) => {
                    self.pressed = Some(KeypadButton::Key(idx));
                }
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // render key buttons
        for btn in self.keys.iter() {
            Self::render_button(btn, target);
        }

        // render special buttons
        Self::render_button(&self.cancel, target);
        Self::render_button(&self.erase, target);
        Self::render_button(&self.back, target);
        Self::render_button(&self.confirm, target);

        // render currently pressed button once again because of possible overlap
        self.render_pressed_button(target);
    }
}

const ROWS: usize = 4;
const COLS: usize = 3;
pub struct KeypadGrid {
    visible_area: Rect,
    border_rects: [[Rect; COLS]; ROWS],
    touch_insets: [[Insets; COLS]; ROWS],
    horizontal_button_overlap: i16,
    vertical_button_spacing: i16,
}

impl KeypadGrid {
    const ROWS: usize = 4;
    const COLS: usize = 3;
    const BUTTON_WIDTH: i16 = 121;
    const BUTTON_HEIGHT: i16 = 70;

    /// Creates a new `KeyboardGrid` with fixed dimensions of 4x3.
    pub const fn new(visible_area: Rect) -> Self {
        let vertical_button_spacing = (visible_area.height()
            - Self::ROWS as i16 * Self::BUTTON_HEIGHT)
            / (Self::ROWS as i16 + 1);
        let horizontal_button_overlap =
            visible_area.width() - Self::COLS as i16 * Self::BUTTON_WIDTH;

        let mut border_rects = [[Rect::zero(); 3]; 4];
        let mut touch_insets = [[Insets::uniform(0); 3]; 4];

        // Compute the border rects and touch insets for each grid entry.
        let mut row = 0;
        while row < Self::ROWS {
            let mut col = 0;
            while col < Self::COLS {
                touch_insets[row][col] = Insets::new(
                    -vertical_button_spacing / 2,
                    -horizontal_button_overlap / 2,
                    -vertical_button_spacing / 2,
                    -horizontal_button_overlap / 2,
                );

                if row == Self::ROWS - 1 {
                    touch_insets[row][col].bottom = 0;
                }
                if col == 0 {
                    touch_insets[row][col].left = 0;
                } else if col == Self::COLS - 1 {
                    touch_insets[row][col].right = 0;
                }

                border_rects[row][col] = Rect::from_top_left_and_size(
                    visible_area.top_left().ofs(Offset::new(
                        col as i16 * Self::BUTTON_WIDTH,
                        row as i16 * (Self::BUTTON_HEIGHT + vertical_button_spacing),
                    )),
                    Offset::new(
                        Self::BUTTON_WIDTH + 2 * horizontal_button_overlap / 2,
                        Self::BUTTON_HEIGHT + 2 * vertical_button_spacing,
                    ),
                );

                col += 1;
            }
            row += 1;
        }

        Self {
            visible_area,
            border_rects,
            touch_insets,
            horizontal_button_overlap,
            vertical_button_spacing,
        }
    }

    /// Retrieves the button border `Rect` at the specified index.
    pub const fn border_of_cell(&self, index: usize) -> Rect {
        let (row, col) = self.cell2row_col(index);
        self.border_of_row_col(row, col)
    }

    /// Converts a cell index to a (row, col) tuple.
    const fn cell2row_col(&self, index: usize) -> (usize, usize) {
        (index / Self::COLS, index % Self::COLS)
    }

    /// Retrieves the button border `Rect` for the given row and column.
    pub const fn border_of_row_col(&self, row: usize, col: usize) -> Rect {
        assert!(row < Self::ROWS);
        assert!(col < Self::COLS);
        self.border_rects[row][col]
    }

    /// Retrieves the button touch `Insets` at the specified index.
    pub const fn insets_of_cell(&self, index: usize) -> Insets {
        let (row, col) = self.cell2row_col(index);
        self.insets_of_row_col(row, col)
    }

    /// Retrieves the button touch `Insets` for the given row and column.
    pub const fn insets_of_row_col(&self, row: usize, col: usize) -> Insets {
        assert!(row < Self::ROWS);
        assert!(col < Self::COLS);
        self.touch_insets[row][col]
    }
}
