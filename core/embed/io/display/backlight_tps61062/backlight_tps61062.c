/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <trezor_bsp.h>
#include <trezor_rtl.h>
#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#include "backlight_tps61062.h"

#ifdef KERNEL_MODE

#define BACKLIGHT_CONTROL_T_START_US  110  // may be in range 100-150
#define BACKLIGHT_CONTROL_T_UP_US     30   // may be in range 1-75
#define BACKLIGHT_CONTROL_T_DOWN_US   200  // may be in range 180-300
#define BACKLIGHT_CONTROL_T_D_US      2
#define BACKLIGHT_CONTROL_T_OFF_US    550
#define BACKLIGHT_CONTROL_T_DS_US     50000


// Backlight driver state
typedef struct {
  // Set if driver is initialized
  bool initialized;
  // Current backlight level in range 0-32
  int current_level;
  // Timer used for backlide fading
  systimer_t *timer;
  int fade_target;
  int fade_step_ms;
  bool fade_in_progress;
} backlight_tps61062_driver_t;

static backlight_tps61062_driver_t g_backlight_driver = {
    .initialized = false,
};

static void backlight_control_up(int num_of_ctr_steps);
static void backlight_control_down(int num_of_ctr_steps);
static void backlight_shutdown();
static void backlight_timer_callback(void *context);

// Initialize the backlight driver
//
// If the action is set to `BACKLIGHT_RESET`, the backlight level
// is set to zero level. If the action is set to `BACKLIGHT_RETAIN`,
// the backlight level is not changed (if possible).
void backlight_init(backlight_action_t action){

backlight_tps61062_driver_t *drv = &g_backlight_driver;

  if(drv->initialized){
    return;
  }

  memset(drv, 0, sizeof(backlight_tps61062_driver_t));

  BACKLIGHT_ILED_CLK_ENA();
  BACKLIGHT_EN_CLK_ENA();

  // Initialize ILED GPIO
  GPIO_InitTypeDef GPIO_ILED_InitStructure = {0};
  GPIO_ILED_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_ILED_InitStructure.Pull = GPIO_NOPULL;
  GPIO_ILED_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_ILED_InitStructure.Pin = BACKLIGHT_ILED_PIN;
  HAL_GPIO_Init(BACKLIGHT_ILED_PORT, &GPIO_ILED_InitStructure);

  // Initialize EN GPIO
  GPIO_InitTypeDef GPIO_EN_InitStructure = {0};
  GPIO_EN_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_EN_InitStructure.Pull = GPIO_NOPULL;
  GPIO_EN_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_EN_InitStructure.Pin = BACKLIGHT_EN_PIN;
  HAL_GPIO_Init(BACKLIGHT_EN_PORT, &GPIO_EN_InitStructure);

  switch (action)
  {
  case BACKLIGHT_KEEP_OFF:

    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_RESET);
    drv->current_level = 0;

    break;

  case BACKLIGHT_RESET:

    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_SET);

    systick_delay_us(BACKLIGHT_CONTROL_T_START_US);

    drv->current_level = 16;

    break;

  default:
    // Should not happen
    break;
  }

  drv->initialized = true;

}

// Deinitialize the backlight driver
//
// If the action is set to `BACKLIGHT_RESET`, the backlight driver
// is completely deinitialized. If the action is set to `BACKLIGHT_RETAIN`,
// the driver is deinitialized as much as possible but the backlight
// is kept on.
void backlight_deinit(backlight_action_t action){

  backlight_tps61062_driver_t *drv = &g_backlight_driver;

  if(!drv->initialized){
    return;
  }

  HAL_GPIO_DeInit(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN);
  HAL_GPIO_DeInit(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN);

  drv->initialized = false;

}

// Sets the backlight level in range 0-32 and returns the actual level set.
//
// If the level is outside the range, the function has no effect
// and just returns the actual level set. If the backlight driver
// is not initialized, the function returns 0.
int backlight_set_level(int val){

  backlight_tps61062_driver_t *drv = &g_backlight_driver;

  if(!drv->initialized || (drv->current_level == val)){
    return 0;
  }

  // Clip max value
  if(val > 32){
    val = 32;
  }

  if(drv->current_level == 0 && val != 0){

    // if brightness controll is shutdown, start with initial pulse
    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_SET);
    systick_delay_us(BACKLIGHT_CONTROL_T_START_US);
    drv->current_level = 16; // DAC go to midpoint after reset

  }

  int irq_key = irq_lock();

  if(val == 0){

    backlight_shutdown();

  }else if(val > drv->current_level){

    backlight_control_up(val-drv->current_level);

  }else if(val < drv->current_level){

    backlight_control_down(drv->current_level-val);

  }

  irq_unlock(irq_key);

  drv->current_level = val;

  return drv->current_level;

}

// Gets the backlight level in range 0-25/5
//
// Returns 0 if the backlight driver is not initialized.
int backlight_get_level(void){
  backlight_tps61062_driver_t *drv = &g_backlight_driver;
  return drv->current_level;
}

// Fade backlight to desired value with in range 0-32 and selected speed
//
// if the value is outside the range, backlight fade to mix or max backlight setting
// and stop
void backlight_fade(int val, int step_ms){

  backlight_tps61062_driver_t *drv = &g_backlight_driver;

  if(!drv->initialized){
    return;
  }

  drv->fade_in_progress = true;
  drv->fade_target = val;
  drv->fade_step_ms = step_ms;
  drv->timer = systimer_create(backlight_timer_callback, drv);

  systimer_set(drv->timer, drv->fade_step_ms);

}

bool backlight_fade_in_progress(){
  backlight_tps61062_driver_t *drv = &g_backlight_driver;
  return drv->fade_in_progress;
}

//void backlight_fade_abort();

static void backlight_control_up(int num_of_ctr_steps){

  for(int i = 0; i < num_of_ctr_steps; i++){

    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_SET);
    systick_delay_us(BACKLIGHT_CONTROL_T_D_US);

    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_RESET);
    systick_delay_us(BACKLIGHT_CONTROL_T_UP_US);

  }

  HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_SET);
  HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_SET);

}

static void backlight_control_down(int num_of_ctr_steps){

  for(int i = 0; i < num_of_ctr_steps; i++){

    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_SET);
    systick_delay_us(BACKLIGHT_CONTROL_T_D_US);

    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_RESET);
    systick_delay_us(BACKLIGHT_CONTROL_T_DOWN_US);

  }

  HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_SET);
  HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_SET);

}

static void backlight_shutdown(){

  HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_RESET);

}

static void backlight_timer_callback(void *context){

  backlight_tps61062_driver_t *drv = (backlight_tps61062_driver_t *)context;

  if(drv->current_level == 0 && drv->fade_target != 0){

    // if brightness controll is shutdown, start with initial pulse
    HAL_GPIO_WritePin(BACKLIGHT_EN_PORT, BACKLIGHT_EN_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(BACKLIGHT_ILED_PORT, BACKLIGHT_ILED_PIN, GPIO_PIN_SET);
    systick_delay_us(BACKLIGHT_CONTROL_T_START_US);

    // DAC starts at zero and midpoint and controll down by 16 steps
    backlight_control_down(15);
    drv->current_level = 1;

  } else if(drv->fade_target == 0 && drv->current_level == 1){

    backlight_shutdown();
    drv->current_level = 0;

  } else if(drv->current_level < drv->fade_target){

    backlight_control_up(1);
    drv->current_level++;

  } else if(drv->current_level > drv->fade_target){

    backlight_control_down(1);
    drv->current_level--;
  }

  if(drv->current_level == drv->fade_target){

    drv->fade_in_progress = false;
    systimer_delete(drv->timer);
    return;
  }

  systimer_set(drv->timer, drv->fade_step_ms);

}


#endif