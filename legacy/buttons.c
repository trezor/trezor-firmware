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

#include "buttons.h"
#include "timer.h"

struct buttonState button;

#if !EMULATOR
uint16_t buttonRead(void) { return gpio_port_read(BTN_PORT); }
#endif

void buttonUpdate() {
  static uint16_t last_state = BTN_PIN_YES | BTN_PIN_NO;

  uint16_t state = buttonRead();

  if ((state & BTN_PIN_YES) == 0) {         // Yes button is down
    if ((last_state & BTN_PIN_YES) == 0) {  // last Yes was down
      if (button.YesDown < 2000000000) button.YesDown++;
      button.YesUp = false;
    } else {  // last Yes was up
      button.YesDown = 0;
      button.YesUp = false;
    }
  } else {                                  // Yes button is up
    if ((last_state & BTN_PIN_YES) == 0) {  // last Yes was down
      button.YesDown = 0;
      button.YesUp = true;
    } else {  // last Yes was up
      button.YesDown = 0;
      button.YesUp = false;
    }
  }
#if !EMULATOR
  if ((state & BTN_PIN_NO)) {         // No button is down
    if ((last_state & BTN_PIN_NO)) {  // last No was down
      if (button.NoDown < 2000000000) button.NoDown++;
      button.NoUp = false;
    } else {  // last No was up
      button.NoDown = 0;
      button.NoUp = false;
    }
  } else {                            // No button is up
    if ((last_state & BTN_PIN_NO)) {  // last No was down
      button.NoDown = 0;
      button.NoUp = true;
    } else {  // last No was up
      button.NoDown = 0;
      button.NoUp = false;
    }
  }
#else
  if ((state & BTN_PIN_NO) == 0) {         // No button is down
    if ((last_state & BTN_PIN_NO) == 0) {  // last No was down
      if (button.NoDown < 2000000000) button.NoDown++;
      button.NoUp = false;
    } else {  // last No was up
      button.NoDown = 0;
      button.NoUp = false;
    }
  } else {                                 // No button is up
    if ((last_state & BTN_PIN_NO) == 0) {  // last No was down
      button.NoDown = 0;
      button.NoUp = true;
    } else {  // last No was up
      button.NoDown = 0;
      button.NoUp = false;
    }
  }
#endif
  if ((state & BTN_PIN_UP) == 0) {         // UP button is down
    if ((last_state & BTN_PIN_UP) == 0) {  // last UP was down
      if (button.UpDown < 2000000000) button.UpDown++;
      button.UpUp = false;
    } else {  // last UP was up
      button.UpDown = 0;
      button.UpUp = false;
    }
  } else {                                 // UP button is up
    if ((last_state & BTN_PIN_UP) == 0) {  // last UP was down
      button.UpDown = 0;
      button.UpUp = true;
    } else {  // last UP was up
      button.UpDown = 0;
      button.UpUp = false;
    }
  }

  if ((state & BTN_PIN_DOWN) == 0) {         // down button is down
    if ((last_state & BTN_PIN_DOWN) == 0) {  // last down was down
      if (button.DownDown < 2000000000) button.DownDown++;
      button.DownUp = false;
    } else {  // last down was up
      button.DownDown = 0;
      button.DownUp = false;
    }
  } else {                                   // down button is up
    if ((last_state & BTN_PIN_DOWN) == 0) {  // last down was down
      button.DownDown = 0;
      button.DownUp = true;
    } else {  // last down was up
      button.DownDown = 0;
      button.DownUp = false;
    }
  }
  if (button.YesUp ||button.NoUp || button.UpUp ||button.DownUp) {
    system_millis_poweroff_start = 0;
  }

  last_state = state;
}

bool hasbutton(void) 
{
  buttonUpdate();
  if (button.YesUp ||button.NoUp || button.UpUp ||button.DownUp) {
    return true;
         
  }
  return false;
}