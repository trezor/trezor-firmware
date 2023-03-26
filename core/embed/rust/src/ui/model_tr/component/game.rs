use crate::{
    time::Duration,
    trezorhal::random,
    ui::{
        component::{Child, Component, Event, EventCtx, Pad, TimerToken},
        display::{self, Font, Icon},
        geometry::{self, Offset, Point, Rect},
        model_tr::constant,
    },
};

use super::{theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos};

use heapless::{String, Vec};

const SCREEN: Rect = constant::screen();
const BOTTOM_Y: i16 = SCREEN.bottom_left().y - theme::BUTTON_HEIGHT - BTN_OFFSET;
const RIGHT_X: i16 = SCREEN.top_right().x;

const MAX_JUMP_HEIGHT: u32 = 20;
const BTN_OFFSET: i16 = 5;

const MAX_OBSTACLES: usize = 1;
const OBSTACLE_FONT: Font = Font::BOLD;

// Speed in pixels per frame
const OBSTACLE_SPEED: f32 = 2.7;
const TREZOR_SPEED: f32 = 1.0;

const TREZOR_ICON: Icon = Icon::new(theme::ICON_LOGO);

const FUD_LENGTH: usize = 20;
#[rustfmt::skip]
const FUD_LIST: [&str; FUD_LENGTH] = [
    "USA",
    "USD",
    "SEC",
    "EU",
    "EUR",
    "ECB",
    "IMF",
    "KYC",
    "AML",
    "ICO",
    "PoS",
    "NFT",
    "ETH",
    "BCH",
    "MtG",
    "PRC",
    "JPM",
    "FTX",
    "SBF",
    "CSW",
];

pub enum GameMsg {
    Dismissed,
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum GameState {
    Initial,
    Started,
    Finished,
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum TrezorState {
    Bottom,
    Jumped(u32),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Obstacle {
    spawned_frame: u32,
    fud_name: &'static str,
    width: i16,
    height: i16,
}

impl Obstacle {
    pub fn new(spawned_frame: u32, fud_name: &'static str) -> Self {
        Self {
            spawned_frame,
            fud_name,
            width: OBSTACLE_FONT.text_width(fud_name) + 2,
            height: 8,
        }
    }

    pub fn get_rect(&self, frame_count: u32) -> Rect {
        let x_diff = (OBSTACLE_SPEED * (frame_count - self.spawned_frame) as f32) as i16;
        let left_x = SCREEN.top_right().x - x_diff;
        let bottom_left = Point::new(left_x, BOTTOM_Y);
        let size = Offset::new(self.width, self.height);
        Rect::from_bottom_left_and_size(bottom_left, size)
    }

    pub fn is_out_of_screen(&self, frame_count: u32) -> bool {
        self.get_rect(frame_count).x1 < 0
    }

    pub fn is_colliding(&self, trezor_rect: Rect, frame_count: u32) -> bool {
        let obstacle_rect = self.get_rect(frame_count);
        trezor_rect.collides(obstacle_rect)
    }

    pub fn paint(&self, frame_count: u32) {
        let rect = self.get_rect(frame_count);
        display::rect_fill(rect, theme::FG);
        display::text_center(
            rect.bottom_center(),
            self.fud_name,
            OBSTACLE_FONT,
            theme::BG,
            theme::FG,
        );
    }
}

pub struct Game {
    game_state: GameState,
    trezor_state: TrezorState,
    trezor_jump_height: i16,
    obstacles: Vec<Obstacle, MAX_OBSTACLES>,
    remaining_fuds: Vec<&'static str, FUD_LENGTH>,
    collided_fud: Option<&'static str>,
    timer: Option<TimerToken>,
    timer_duration: Duration,
    frame_count: u32,
    highest_score: u32,
    pad: Pad,
    buttons: Child<ButtonController>,
    needs_left_release: bool,
}

impl Game {
    pub fn new() -> Self {
        Self {
            game_state: GameState::Initial,
            trezor_state: TrezorState::Bottom,
            trezor_jump_height: 0,
            obstacles: Vec::new(),
            remaining_fuds: create_heapless_vec_from_array(FUD_LIST),
            collided_fud: None,
            timer: None,
            timer_duration: Duration::from_millis(30),
            frame_count: 0,
            highest_score: 0,
            pad: Pad::with_background(theme::BG).with_clear(),
            buttons: Child::new(ButtonController::new(Self::get_button_layout(
                GameState::Initial,
            ))),
            needs_left_release: false,
        }
    }

    fn get_score(&self) -> u32 {
        self.frame_count / 10
    }

    fn get_button_layout(state: GameState) -> ButtonLayout {
        match state {
            GameState::Initial | GameState::Finished => {
                ButtonLayout::text_none_text("START".into(), "CANCEL".into())
            }
            GameState::Started => ButtonLayout::text_none_text("JUMP".into(), "STOP".into()),
        }
    }

    /// Reflecting the current page in the buttons.
    fn update_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = Self::get_button_layout(self.game_state);
        self.buttons.mutate(ctx, |ctx, buttons| {
            buttons.set(btn_layout);
            ctx.request_paint();
        });
    }

    fn start(&mut self, ctx: &mut EventCtx) {
        if self.game_state == GameState::Initial || self.game_state == GameState::Finished {
            self.game_state = GameState::Started;
            self.trezor_state = TrezorState::Bottom;
            self.trezor_jump_height = 0;
            self.obstacles.clear();
            self.collided_fud = None;
            self.frame_count = 0;
            self.remaining_fuds = create_heapless_vec_from_array(FUD_LIST);
            self.timer = Some(ctx.request_timer(self.timer_duration));
            self.update_buttons(ctx);
            ctx.request_paint();
        }
    }

    fn stop(&mut self, ctx: &mut EventCtx) {
        if self.game_state == GameState::Started {
            self.game_state = GameState::Finished;
            self.timer = None;
            self.update_buttons(ctx);
            ctx.request_paint();
        }
    }

    fn jump(&mut self, ctx: &mut EventCtx) {
        if self.trezor_state == TrezorState::Bottom && self.game_state == GameState::Started {
            self.trezor_state = TrezorState::Jumped(self.frame_count);
            ctx.request_paint();
        };
    }

    fn update_trezor_jump_height(&mut self) {
        self.trezor_jump_height = match self.trezor_state {
            TrezorState::Bottom => 0,
            TrezorState::Jumped(frame_count) => {
                let diff = (TREZOR_SPEED * (self.frame_count - frame_count) as f32) as u32;
                if diff >= 2 * MAX_JUMP_HEIGHT {
                    self.trezor_state = TrezorState::Bottom;
                }
                if diff < MAX_JUMP_HEIGHT {
                    diff as i16
                } else {
                    (2 * MAX_JUMP_HEIGHT - diff) as i16
                }
            }
        };
    }

    fn paint_floor(&self) {
        for x in SCREEN.x0..SCREEN.x1 {
            let point = Point::new(x, BOTTOM_Y);
            display::paint_point(&point, theme::FG);
        }
    }

    fn paint_header(&self) {
        display::text_right(
            SCREEN.top_right() + Offset::y(10),
            "Jump over FUD!",
            Font::BOLD,
            theme::FG,
            theme::BG,
        );
    }

    fn paint_score(&self) {
        let score_line = if self.highest_score > 0 {
            build_string!(
                20,
                inttostr!(self.get_score()),
                " HI ",
                inttostr!(self.highest_score)
            )
        } else {
            build_string!(20, inttostr!(self.get_score()))
        };
        display::text_right(
            SCREEN.top_right() + Offset::y(20),
            &score_line,
            Font::BOLD,
            theme::FG,
            theme::BG,
        );
    }

    fn paint_game_over(&self) {
        let text = build_string!(20, "Defeated by ", self.collided_fud.unwrap_or("FUD"));
        display::text_right(
            SCREEN.top_right() + Offset::y(30),
            &text,
            Font::BOLD,
            theme::FG,
            theme::BG,
        );
    }

    fn paint_trezor(&mut self) {
        let current_y = BOTTOM_Y - self.trezor_jump_height as i16;
        TREZOR_ICON.draw(
            Point::new(SCREEN.x0, current_y),
            geometry::BOTTOM_LEFT,
            theme::FG,
            theme::BG,
        );
    }

    fn paint_obstacles(&self) {
        for obstacle in self.obstacles.iter() {
            obstacle.paint(self.frame_count);
        }
    }

    fn update_obstacles(&mut self) {
        if self.frame_count % 30 == 0 && self.obstacles.len() < MAX_OBSTACLES {
            let fud_index = random::uniform(self.remaining_fuds.len() as u32);
            let fud_name = self.remaining_fuds[fud_index as usize];
            let obstacle = Obstacle::new(self.frame_count, fud_name);
            unwrap!(self.obstacles.push(obstacle));
            // So that we do not show duplicated fuds - always circle through the whole list
            self.remaining_fuds = filter_heapless_vec(&self.remaining_fuds, |fud| fud != &fud_name);
            if self.remaining_fuds.is_empty() {
                self.remaining_fuds = create_heapless_vec_from_array(FUD_LIST);
            }
        }
        self.obstacles = filter_heapless_vec(&self.obstacles, |obstacle| {
            !obstacle.is_out_of_screen(self.frame_count)
        });
    }

    fn check_for_collision(&self) -> Option<Obstacle> {
        let trezor_bottom_y = BOTTOM_Y - self.trezor_jump_height;
        let trezor_rect = Rect::new(
            Point::new(SCREEN.x0, trezor_bottom_y - TREZOR_ICON.toif.height()),
            Point::new(SCREEN.x0 + TREZOR_ICON.toif.width(), trezor_bottom_y),
        );
        for obstacle in self.obstacles.iter() {
            if obstacle.is_colliding(trezor_rect, self.frame_count) {
                return Some(*obstacle);
            }
        }
        None
    }
}

fn filter_heapless_vec<T, F, const N: usize, const M: usize>(
    input: &Vec<T, N>,
    mut predicate: F,
) -> Vec<T, M>
where
    T: core::clone::Clone,
    F: FnMut(&T) -> bool,
{
    let mut filtered = Vec::<T, M>::new();
    for item in input.iter() {
        if predicate(item) {
            unwrap!(filtered.push(item.clone()));
        }
    }
    filtered
}

fn create_heapless_vec_from_array<const N: usize>(
    array: [&'static str; N],
) -> Vec<&'static str, N> {
    let mut vec = Vec::<&'static str, N>::new();

    for &item in array.iter() {
        vec.push(item)
            .unwrap_or_else(|_| panic!("Vector capacity exceeded"));
    }

    vec
}

impl Component for Game {
    type Msg = GameMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = SCREEN.split_bottom(theme::BUTTON_HEIGHT);
        self.pad.place(content_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let button_event = self.buttons.event(ctx, event);

        // For the JUMP release not to trigger the START button (after collision)
        if self.needs_left_release {
            if let Some(ButtonControllerMsg::Triggered(ButtonPos::Left)) = button_event {
                self.needs_left_release = false;
                return None;
            }
        }

        match self.game_state {
            GameState::Initial | GameState::Finished => {
                if let Some(ButtonControllerMsg::Triggered(triggered_btn)) = button_event {
                    match triggered_btn {
                        ButtonPos::Left => self.start(ctx),
                        ButtonPos::Right => return Some(GameMsg::Dismissed),
                        _ => {}
                    }
                }
            }
            GameState::Started => {
                if let Some(ButtonControllerMsg::Pressed(ButtonPos::Left)) = button_event {
                    self.jump(ctx);
                    self.needs_left_release = true;
                }
                if let Some(ButtonControllerMsg::Triggered(ButtonPos::Right)) = button_event {
                    self.stop(ctx);
                }
            }
        }
        if let Event::Timer(token) = event {
            if self.timer == Some(token) {
                self.update_trezor_jump_height();
                self.update_obstacles();
                if let Some(collision) = self.check_for_collision() {
                    self.highest_score = self.highest_score.max(self.get_score());
                    self.collided_fud = Some(collision.fud_name);
                    self.stop(ctx);
                } else {
                    self.frame_count += 1;
                    self.timer = Some(ctx.request_timer(self.timer_duration));
                };
            }
        }
        self.pad.clear();
        ctx.request_paint();
        None
    }

    fn paint(&mut self) {
        self.pad.paint();
        self.buttons.paint();
        self.paint_floor();
        self.paint_trezor();
        self.paint_obstacles();
        self.paint_header();
        self.paint_score();
        if let GameState::Finished = self.game_state {
            self.paint_game_over();
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.pad.area);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Game {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Game");
        d.close();
    }
}
