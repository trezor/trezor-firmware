use crate::{
    trezorhal::random,
    ui::{
        component::{Component, Event, EventCtx, Maybe},
        geometry::{Alignment, Insets, Offset, Rect},
        shape::Renderer,
    },
};

use super::{
    super::super::{
        component::button::{Button, ButtonContent, ButtonMsg, ButtonStyleSheet},
        constant::SCREEN,
        theme,
    },
    common::KEYPAD_VISIBLE_HEIGHT,
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

pub struct KeypadState {
    pub back: ButtonState,
    pub erase: ButtonState,
    pub cancel: ButtonState,
    pub confirm: ButtonState,
    pub keys: ButtonState,
}

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

    /// Create a new keypad with numeric keys. The keys are shown and active and
    /// are shuffled if `shuffle` is true. The special buttons are hidden.
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

    /// Create a new keypad with empty keys. The keys and special buttons are
    /// hidden.
    pub fn new_hidden() -> Self {
        Self::new_inner(false, false, theme::button_keyboard())
    }

    /// Create a new keypad with empty keys. The keys are shown and the special
    /// buttons are hidden.
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

    /// Set the content of all keyboard keys.
    pub fn with_keys_content(mut self, keypad_content: &[ButtonContent]) -> Self {
        // Make sure the content fits the keypad.
        debug_assert!(keypad_content.len() <= Self::MAX_KEYS);

        for (i, key_content) in keypad_content.into_iter().enumerate() {
            self.keys[i].inner_mut().set_content(key_content.clone());
        }
        self
    }

    /// Get the content of a key at the specified index.
    pub fn get_key_content(&self, idx: usize) -> &ButtonContent {
        // Make sure the index is within bounds.
        debug_assert!(idx < Self::MAX_KEYS);

        &self.keys[idx].inner().content()
    }

    /// Set the state of the keypad.
    pub fn set_state(&mut self, state: KeypadState, ctx: &mut EventCtx) {
        Self::apply_button_state(&mut self.back, &state.back, ctx);
        Self::apply_button_state(&mut self.erase, &state.erase, ctx);
        Self::apply_button_state(&mut self.cancel, &state.cancel, ctx);
        Self::apply_button_state(&mut self.confirm, &state.confirm, ctx);
        self.set_keys_state(ctx, &state.keys);
    }

    /// Set the content of a key at the specified index.
    pub fn set_key_content(&mut self, idx: usize, content: ButtonContent) {
        // Make sure the index is within bounds.
        debug_assert!(idx < Self::MAX_KEYS);

        self.keys[idx].inner_mut().set_content(content);
    }

    fn get_button_mut(&mut self, button: &KeypadButton) -> &mut Maybe<Button> {
        match button {
            KeypadButton::Key(idx) => &mut self.keys[*idx],
            KeypadButton::Erase => &mut self.erase,
            KeypadButton::Cancel => &mut self.cancel,
            KeypadButton::Confirm => &mut self.confirm,
            KeypadButton::Back => &mut self.back,
        }
    }

    fn get_button(&self, button: &KeypadButton) -> &Maybe<Button> {
        match button {
            KeypadButton::Key(idx) => &self.keys[*idx],
            KeypadButton::Erase => &self.erase,
            KeypadButton::Cancel => &self.cancel,
            KeypadButton::Confirm => &self.confirm,
            KeypadButton::Back => &self.back,
        }
    }

    /// Set the stylesheet of one keypad button.
    pub fn set_button_stylesheet(&mut self, button: KeypadButton, styles: ButtonStyleSheet) {
        self.get_button_mut(&button)
            .inner_mut()
            .set_stylesheet(styles);
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

    /// Set the state of all key buttons
    pub fn set_keys_state(&mut self, ctx: &mut EventCtx, state: &ButtonState) {
        for btn in self.keys.iter_mut() {
            Self::apply_button_state(btn, state, ctx);
        }
    }

    /// Set the state of one keypad button.
    pub fn set_button_state(
        &mut self,
        ctx: &mut EventCtx,
        button: KeypadButton,
        state: &ButtonState,
    ) {
        Self::apply_button_state(self.get_button_mut(&button), state, ctx);
    }

    /// Check if any button is currently pressed.
    pub fn pressed(&self) -> bool {
        self.pressed.is_some()
    }

    fn render_button<'s>(btn: &'s Maybe<Button>, target: &mut impl Renderer<'s>) {
        if btn.is_visible() {
            btn.render(target);
        }
    }

    /// Render pressed button.
    fn render_pressed_button<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // TODO: Render special shape for the edge buttons.
        if let Some(button) = &self.pressed {
            Self::render_button(self.get_button(button), target);
        }
    }

    /// Convert key index to grid cell index.
    fn key_2_grid_cell(key: usize) -> usize {
        // Make sure the key is within bounds.
        debug_assert!(key < Self::MAX_KEYS);
        // Key with index 9 must be mapped after the cancel button.
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
        // assert precise size and position of the keypad
        debug_assert_eq!(bounds.width(), SCREEN.width());
        debug_assert_eq!(bounds.height(), KEYPAD_VISIBLE_HEIGHT);
        debug_assert!(bounds.bottom_right() == SCREEN.bottom_right());

        // Decrease touch area for buttons.
        let erase_touch_inset = KeypadGrid::insets_of_cell(Self::ERASE_BUTTON_INDEX);
        let confirm_touch_inset = KeypadGrid::insets_of_cell(Self::CONFIRM_BUTTON_INDEX);

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
                .set_expanded_touch_area(KeypadGrid::insets_of_cell(Self::key_2_grid_cell(i)));
        }

        // Place buttons
        let erase_area = KeypadGrid::border_of_cell(Self::ERASE_BUTTON_INDEX);
        let confirm_area = KeypadGrid::border_of_cell(Self::CONFIRM_BUTTON_INDEX);

        self.erase.place(erase_area);
        self.cancel.place(erase_area);
        self.back.place(erase_area);
        self.confirm.place(confirm_area);
        for (i, btn) in self.keys.iter_mut().enumerate() {
            btn.place(KeypadGrid::border_of_cell(Self::key_2_grid_cell(i)));
        }
        bounds
    }
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let click_mapping = [
            (KeypadButton::Confirm, KeypadMsg::Confirm),
            (KeypadButton::Erase, KeypadMsg::EraseShort),
            (KeypadButton::Cancel, KeypadMsg::Cancel),
            (KeypadButton::Back, KeypadMsg::Back),
        ];

        for (button, msg) in click_mapping {
            match self.get_button_mut(&button).event(ctx, event) {
                // Detect click of all special buttons
                Some(ButtonMsg::Clicked) => {
                    self.pressed = None;
                    return Some(msg);
                }
                // Detect long press of the erase button
                Some(ButtonMsg::LongPressed) if button == KeypadButton::Erase => {
                    self.pressed = None;
                    return Some(KeypadMsg::EraseLong);
                }
                // Detect press of all special buttons for rendering purposes
                Some(ButtonMsg::Pressed) => {
                    self.pressed = Some(button);
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

// Dimensions of the grid.
const ROWS: usize = 4;
const COLS: usize = 3;

/// Represents a grid of buttons with fixed dimensions of 4x3.
/// Borders of buttons overlap each other and the input component because in
/// pressed state, they are rendered larger. To avoid touch interference between
/// buttons, negative insets are used to reduce the touch area of each button
/// not to overlap.
pub struct KeypadGrid;

impl KeypadGrid {
    /// The visible area of the keypad.
    const VISIBLE_AREA: Rect = Self::visible_area();

    // Button dimensions.
    const BUTTON_WIDTH: i16 = 136;
    const BUTTON_HEIGHT: i16 = 134;

    // Overlap parameters.
    const VERTICAL_BUTTON_SPACING: i16 = 32;
    const HORIZONTAL_BUTTON_PADDING: i16 = 7;

    // Precomputed border rects and touch insets for each grid entry.
    const BORDER_RECTS: [[Rect; COLS]; ROWS] = KeypadGrid::compute_border_rects();
    const TOUCH_INSETS: [[Insets; COLS]; ROWS] = KeypadGrid::compute_touch_insets();

    // Keypad touch area is smaller than the visible area.
    // Sum input and keypad gives the
    const KEYPAD_TOUCH_HEIGHT: i16 = KEYPAD_VISIBLE_HEIGHT - Self::VERTICAL_BUTTON_SPACING / 2;

    const fn visible_area() -> Rect {
        let (_, visible_area) = SCREEN.split_bottom(KEYPAD_VISIBLE_HEIGHT);
        visible_area
    }

    /// Computes the border rects for each grid entry.
    const fn compute_border_rects() -> [[Rect; COLS]; ROWS] {
        let mut rects = [[Rect::zero(); COLS]; ROWS];
        let mut row = 0;
        while row < ROWS {
            let mut col = 0;
            while col < COLS {
                rects[row][col] = Rect::from_top_left_and_size(
                    Self::VISIBLE_AREA.top_left().ofs(Offset::new(
                        col as i16 * (Self::BUTTON_WIDTH - 2 * Self::HORIZONTAL_BUTTON_PADDING),
                        row as i16 * (Self::BUTTON_HEIGHT - Self::VERTICAL_BUTTON_SPACING),
                    )),
                    Offset::new(Self::BUTTON_WIDTH, Self::BUTTON_HEIGHT),
                );
                col += 1;
            }
            row += 1;
        }
        rects
    }

    /// Computes negative touch insets for each grid entry for
    /// `set_expanded_touch_area` Buttonfunction
    const fn compute_touch_insets() -> [[Insets; COLS]; ROWS] {
        let mut insets = [[Insets::uniform(0); COLS]; ROWS];
        let mut row = 0;
        while row < ROWS {
            let mut col = 0;
            while col < COLS {
                insets[row][col] = Insets::new(
                    -Self::VERTICAL_BUTTON_SPACING / 2,
                    -Self::HORIZONTAL_BUTTON_PADDING,
                    -Self::VERTICAL_BUTTON_SPACING / 2,
                    -Self::HORIZONTAL_BUTTON_PADDING,
                );
                // No bottom inset for the last row
                if row == ROWS - 1 {
                    insets[row][col].bottom = 0;
                }
                // no left inset for the first column
                if col == 0 {
                    insets[row][col].left = 0;
                // no right inset for the last column
                } else if col == COLS - 1 {
                    insets[row][col].right = 0;
                }
                col += 1;
            }
            row += 1;
        }
        insets
    }

    /// Retrieves the button border `Rect` at the specified index.
    pub const fn border_of_cell(index: usize) -> Rect {
        let (row, col) = Self::cell2row_col(index);
        Self::border_of_row_col(row, col)
    }

    // Converts a cell index to a (row, col) tuple.
    const fn cell2row_col(index: usize) -> (usize, usize) {
        (index / COLS, index % COLS)
    }

    /// Retrieves the button border `Rect` for the given row and column.
    pub const fn border_of_row_col(row: usize, col: usize) -> Rect {
        debug_assert!(row < ROWS);
        debug_assert!(col < COLS);
        Self::BORDER_RECTS[row][col]
    }

    /// Retrieves the button touch `Insets` at the specified index.
    pub const fn insets_of_cell(index: usize) -> Insets {
        let (row, col) = Self::cell2row_col(index);
        Self::insets_of_row_col(row, col)
    }

    /// Retrieves the button touch `Insets` for the given row and column.
    pub const fn insets_of_row_col(row: usize, col: usize) -> Insets {
        debug_assert!(row < ROWS);
        debug_assert!(col < COLS);
        Self::TOUCH_INSETS[row][col]
    }
}

#[cfg(test)]
mod tests {

    use super::{
        super::{super::constant::SCREEN, common::INPUT_TOUCH_HEIGHT},
        *,
    };

    #[test]
    fn test_layout_constraints() {
        debug_assert_eq!(
            KeypadGrid::KEYPAD_TOUCH_HEIGHT + INPUT_TOUCH_HEIGHT,
            SCREEN.height(),
            "Keypad and input touch areas do not sum into the screen height"
        );

        assert_eq!(
            (ROWS as i16) * KeypadGrid::BUTTON_HEIGHT,
            KeypadGrid::KEYPAD_TOUCH_HEIGHT
                + (ROWS as i16 - 1) * KeypadGrid::VERTICAL_BUTTON_SPACING,
            "Keypad height does not match expected layout constraints"
        );

        assert_eq!(
            (COLS as i16) * KeypadGrid::BUTTON_WIDTH,
            KeypadGrid::VISIBLE_AREA.width()
                + (COLS as i16 - 1) * 2 * KeypadGrid::HORIZONTAL_BUTTON_PADDING,
            "Keypad width does not match expected layout constraints"
        );
    }

    #[test]
    fn test_borders_within_visible_area_by_cell() {
        for index in 0..(ROWS * COLS) {
            let border = KeypadGrid::border_of_cell(index);
            // The border is within the visible area if the intersection is equal to the
            // border.
            let intersection = border.clamp(KeypadGrid::VISIBLE_AREA);
            assert!(
                border.width() == intersection.width() && border.height() == intersection.height(),
                "Border at index {} is out of keypad visible bounds",
                index
            );
        }
    }

    #[test]
    fn test_no_touch_overlap() {
        for idx1 in 0..(ROWS * COLS) {
            let touch_border_1 =
                KeypadGrid::border_of_cell(idx1).outset(KeypadGrid::insets_of_cell(idx1));

            for idx2 in 0..(ROWS * COLS) {
                if idx1 == idx2 {
                    continue; // Skip comparing the same cell
                }

                let touch_border_2 =
                    KeypadGrid::border_of_cell(idx2).outset(KeypadGrid::insets_of_cell(idx2));

                assert!(
                    touch_border_1.clamp(touch_border_2).is_empty(),
                    "Touch border of cell {} overlaps the touch border of
                cell {}",
                    idx1,
                    idx2,
                );
            }
        }
    }
}
