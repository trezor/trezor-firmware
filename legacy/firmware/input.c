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

#include "input.h"
#include "buttons.h"
#include "config.h"
#include "gettext.h"
#include "layout2.h"
#include "memory.h"
#include "oled.h"
#include "rng.h"
#include "usb.h"

#define CARET_SHOW 80
#define CARET_CYCLE (CARET_SHOW * 2)

void buttonCheckRepeat(bool *yes, bool *no, bool *confirm) {
  *yes = false;
  *no = false;
  *confirm = false;

  const int Threshold0 = 20;
  const int Thresholds[] = {Threshold0, 80, 20, 18, 16, 14, 12, 10, 8, 6, 4};
  const int MaxThresholdLevel = sizeof(Thresholds) / sizeof(Thresholds[0]) - 1;

  static int yesthreshold = Threshold0;
  static int nothreshold = Threshold0;

  static int yeslevel = 0;
  static int nolevel = 0;

  static bool both = false;

  usbSleep(5);
  buttonUpdate();

  if (both) {
    if (!button.YesDown && !button.NoDown) {
      both = false;
      yeslevel = 0;
      nolevel = 0;
      yesthreshold = Thresholds[0];
      nothreshold = Thresholds[0];
    }
  } else if ((button.YesDown && button.NoDown) ||
             (button.YesUp && button.NoDown) ||
             (button.YesDown && button.NoUp) || (button.YesUp && button.NoUp)) {
    if (!yeslevel && !nolevel) {
      both = true;
      *confirm = true;
    }
  } else {
    if (button.YesUp) {
      if (!yeslevel) *yes = true;
      yeslevel = 0;
      yesthreshold = Thresholds[0];
    } else if (button.YesDown >= yesthreshold) {
      if (yeslevel < MaxThresholdLevel) ++yeslevel;
      yesthreshold += Thresholds[yeslevel];
      *yes = true;
    }
    if (button.NoUp) {
      if (!nolevel) *no = true;
      nolevel = 0;
      nothreshold = Thresholds[0];
    } else if (button.NoDown >= nothreshold) {
      if (nolevel < MaxThresholdLevel) ++nolevel;
      nothreshold += Thresholds[nolevel];
      *no = true;
    }
  }
}

void buttonWaitForYesUp(void) {
  buttonUpdate();

  for (;;) {
    usbSleep(5);
    buttonUpdate();
    if (button.YesUp) break;
  }
}

void buttonWaitForIdle(void) {
  buttonUpdate();

  for (;;) {
    usbSleep(5);
    buttonUpdate();
    if (!button.YesDown && !button.YesUp && !button.NoDown && !button.NoUp)
      break;
  }
}

void requestOnDeviceTextInput(void) {
  layoutDialog(&bmp_icon_question, _("Cancel"), _("Confirm"), NULL,
               _("Do you like to use"), _("on-device text input?"), NULL, NULL,
               NULL, NULL);

  buttonUpdate();

  for (;;) {
    usbSleep(5);
    buttonUpdate();
    if (button.YesUp || button.NoUp) break;
  }

  layoutSwipe();

  session_setUseOnDeviceTextInput(button.YesUp);
}

int findCharIndex(const char entries[], char needle, int numtotal,
                  int startindex, bool forward) {
  if (numtotal <= 1 || entries[startindex] == needle) return startindex;
  int step = forward ? 1 : -1;
  int index = (startindex + step + numtotal) % numtotal;
  while (index != startindex) {
    if (entries[index] == needle) return index;
    index += step;
  }
  return startindex;
}

int inputTextScroll(char *text, int *textcharindex, int maxtextcharindex,
                    const char entries[], int textwidth, int entryindex,
                    int numtotal, int numscreen, int horizontalpadding,
                    const int groups[], int numgroup, int numskipingroups,
                    int *caret) {
  for (;; *caret = (*caret + 1) % CARET_CYCLE) {
    bool yes, no, confirm;
    buttonCheckRepeat(&yes, &no, &confirm);

    if (confirm) {
      buttonWaitForIdle();

      if (entries[entryindex] == CHAR_BCKSPC) {
        if (*textcharindex > 0) {
          --(*textcharindex);
          text[*textcharindex] = 0;
        }
      } else if (entries[entryindex] == CHAR_DONE) {
        return INPUT_DONE;
      } else {
        if (*textcharindex < maxtextcharindex) {
          text[*textcharindex] = entries[entryindex];
          ++(*textcharindex);
        }
        return entryindex;
      }

      entryindex = random32() % numtotal;
    } else {
      if (yes) entryindex = (entryindex + 1) % numtotal;
      if (no) entryindex = (entryindex - 1 + numtotal) % numtotal;
    }

    layoutScrollInput(text, textwidth, numtotal, numscreen, entryindex, entries,
                      horizontalpadding, numgroup, groups, numskipingroups,
                      *caret < CARET_SHOW);
  }
}

bool inputText(char *text, int maxtextlen, const char characters[],
               int numcharacters, char groupseparator, int width,
               bool requiredone, bool allowempty) {
#define MAX_NUM_CHARACTERS_GROUPS 32

  int charactersGroups[MAX_NUM_CHARACTERS_GROUPS];
  charactersGroups[0] = 0;
  int numcharactersgroups = 1;
  for (int i = 0; i < numcharacters; ++i) {
    if (characters[i] == groupseparator) {
      charactersGroups[numcharactersgroups] = i + 1;
      ++numcharactersgroups;
      if (numcharactersgroups >= MAX_NUM_CHARACTERS_GROUPS) {
        break;
      }
    }
  }

  usbSleep(5);
  buttonUpdate();

  int charindex = strlen(text);
  int caret = 0;

  for (;;) {
    int entryindex = random32() % numcharacters;
    if (charindex >= maxtextlen)
      entryindex = findCharIndex(characters, CHAR_DONE, numcharacters,
                                 entryindex, entryindex < numcharacters / 2);
    entryindex = inputTextScroll(
        text, &charindex, maxtextlen, characters, width, entryindex,
        numcharacters, 9, 9, charactersGroups, numcharactersgroups, 2, &caret);
    if ((!requiredone || entryindex == INPUT_DONE) &&
        (allowempty || charindex > 0)) {
      return entryindex == INPUT_DONE;
    }
  }
}
