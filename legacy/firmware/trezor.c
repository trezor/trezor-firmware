/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "trezor.h"
#include "bitmaps.h"
#include "bl_check.h"
#include "buttons.h"
#include "common.h"
#include "config.h"
#include "gettext.h"
#include "layout.h"
#include "layout2.h"
#include "memzero.h"
#include "oled.h"
#include "rng.h"
#include "setup.h"
#include "timer.h"
#include "usb.h"
#include "util.h"
#if !EMULATOR
#include <libopencm3/stm32/desig.h>
#include "otp.h"
#endif

#include <stdio.h>

enum GameDir { DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT };

enum GameState { STATE_PLAYING, STATE_GAMEOVER };

int SCORE = 0;
int HISCORE = 0;

#define FIELD_WIDTH (OLED_WIDTH / 2)
#define FIELD_HEIGHT (OLED_HEIGHT / 2)

struct Game {
  int16_t field[FIELD_WIDTH * FIELD_HEIGHT];
  int16_t len;
  int16_t bug_lifetime;  // negative number, grows to zero
  uint32_t delay;        // how much to sleep after each game loop iter
  uint32_t spawn_rate;   // spawn_rate < random32() => a bug spawns
  int growth_rate;       // how much to grow after eating
  int x;
  int y;
  enum GameDir dir;
  enum GameState state;
};

static struct Game game;

#define GAME_CELL(x, y) game.field[y * FIELD_WIDTH + x]

void gameInit(void) {
  memset(game.field, 0, sizeof(game.field));
  game.state = STATE_PLAYING;
  game.dir = DIR_DOWN;
  game.x = 25;
  game.y = 0;
  game.len = 16;
  game.delay = 3e6;
  game.growth_rate = 3;
  game.bug_lifetime = INT16_MIN / 128;
  game.spawn_rate = UINT32_MAX - (UINT32_MAX / 32);
  SCORE = 0;

  oledDrawBitmap(0, 0, &bmp_snake);
  oledRefresh();

  for (;;) {
    delay(game.delay);
    buttonUpdate();
    if (button.YesUp) {
      break;
    }
  }
}

void gamePlayingUpdate(void) {
  // input

  buttonUpdate();
  if (button.YesUp) {  // right
    switch (game.dir) {
      case DIR_UP:
        game.dir = DIR_RIGHT;
        break;
      case DIR_LEFT:
        game.dir = DIR_UP;
        break;
      case DIR_DOWN:
        game.dir = DIR_LEFT;
        break;
      case DIR_RIGHT:
        game.dir = DIR_DOWN;
        break;
    }
  }
  if (button.NoUp) {  // left
    switch (game.dir) {
      case DIR_UP:
        game.dir = DIR_LEFT;
        break;
      case DIR_LEFT:
        game.dir = DIR_DOWN;
        break;
      case DIR_DOWN:
        game.dir = DIR_RIGHT;
        break;
      case DIR_RIGHT:
        game.dir = DIR_UP;
        break;
    }
  }

  // update head

  switch (game.dir) {
    case DIR_UP:
      game.y--;
      break;
    case DIR_LEFT:
      game.x--;
      break;
    case DIR_DOWN:
      game.y++;
      break;
    case DIR_RIGHT:
      game.x++;
      break;
  }

  // collisions

  if ((game.x < 0 || game.x >= FIELD_WIDTH) ||  // hit left or right
      (game.y < 0 || game.y >= FIELD_HEIGHT))   // hit top or bottom
  {
    game.state = STATE_GAMEOVER;
    return;
  }

  if (GAME_CELL(game.x, game.y) > 0) {  // hit the body
    game.state = STATE_GAMEOVER;
    return;
  }

  if (GAME_CELL(game.x, game.y) < 0) {  // ate a bug
    game.len++;                         // cell gets replaced by head later
    SCORE++;
    if (SCORE > HISCORE) {
      HISCORE = SCORE;
    }
  }

  // move

  int y, x;

  for (y = 0; y < FIELD_HEIGHT; y++) {
    for (x = 0; x < FIELD_WIDTH; x++) {
      if (GAME_CELL(x, y) > 0) {
        GAME_CELL(x, y)--;
      } else if (GAME_CELL(x, y) < 0) {
        GAME_CELL(x, y)++;
      }
    }
  }

  GAME_CELL(game.x, game.y) = game.len;

  // spawn a bug maybe?

  if (game.spawn_rate < random32()) {
    int16_t bug_x = random32() % FIELD_WIDTH;
    int16_t bug_y = random32() % FIELD_HEIGHT;
    GAME_CELL(bug_x, bug_y) = INT16_MIN / 128;
  }
}

void gamePlayingDraw(void) {
  int y, x;

  for (y = 0; y < OLED_HEIGHT; y++) {
    for (x = 0; x < OLED_WIDTH; x++) {
      if (GAME_CELL(x / 2, y / 2) != 0) {
        oledDrawPixel(x, y);
      }
    }
  }
}

void gameOverUpdate(void) {
  buttonUpdate();
  if (button.YesUp) {
    gameInit();
  }
}

void gameOverDraw(void) {
  char score[100];
  char hiscore[100];
  snprintf(score, sizeof(score), "Score: %d", SCORE);
  snprintf(hiscore, sizeof(hiscore), "Hi-Score: %d", HISCORE);
  oledDrawStringCenter(OLED_WIDTH / 2, OLED_HEIGHT / 2 - 20, "GAME OVER", FONT_STANDARD);
  oledDrawStringCenter(OLED_WIDTH / 2, OLED_HEIGHT / 2, score, FONT_STANDARD);
  oledDrawStringCenter(OLED_WIDTH / 2, OLED_HEIGHT / 2 + 20, hiscore, FONT_STANDARD);
}

void gameUpdate(void) {
  switch (game.state) {
    case STATE_PLAYING:
      gamePlayingUpdate();
      break;
    case STATE_GAMEOVER:
      gameOverUpdate();
      break;
  }
}

void gameDraw(void) {
  oledClear();
  switch (game.state) {
    case STATE_PLAYING:
      gamePlayingDraw();
      break;
    case STATE_GAMEOVER:
      gameOverDraw();
      break;
  }
  oledRefresh();
}


static void collect_hw_entropy(bool privileged) {
#if EMULATOR
  (void)privileged;
  memzero(HW_ENTROPY_DATA, HW_ENTROPY_LEN);
#else
  if (privileged) {
    desig_get_unique_id((uint32_t *)HW_ENTROPY_DATA);
    // set entropy in the OTP randomness block
    if (!flash_otp_is_locked(FLASH_OTP_BLOCK_RANDOMNESS)) {
      uint8_t entropy[FLASH_OTP_BLOCK_SIZE] = {0};
      random_buffer(entropy, FLASH_OTP_BLOCK_SIZE);
      flash_otp_write(FLASH_OTP_BLOCK_RANDOMNESS, 0, entropy,
                      FLASH_OTP_BLOCK_SIZE);
      flash_otp_lock(FLASH_OTP_BLOCK_RANDOMNESS);
    }
    // collect entropy from OTP randomness block
    flash_otp_read(FLASH_OTP_BLOCK_RANDOMNESS, 0, HW_ENTROPY_DATA + 12,
                   FLASH_OTP_BLOCK_SIZE);
  } else {
    // unprivileged mode => use fixed HW_ENTROPY
    memset(HW_ENTROPY_DATA, 0x3C, HW_ENTROPY_LEN);
  }
#endif
}

int main(void) {
#ifndef APPVER
  setup();
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
  oledInit();
#else
  // check_bootloader(true);
  setupApp();
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
#endif

  drbg_init();

  if (!is_mode_unprivileged()) {
    collect_hw_entropy(true);
    timer_init();
#ifdef APPVER
    // enable MPU (Memory Protection Unit)
    mpu_config_firmware();
#endif
  } else {
    collect_hw_entropy(false);
  }

#if DEBUG_LINK
  oledSetDebugLink(1);
#if !EMULATOR
  config_wipe();
#endif
#endif

  gameInit();
  for (;;) {
    gameUpdate();
    gameDraw();
    delay(game.delay);
  }

  return 0;
}
