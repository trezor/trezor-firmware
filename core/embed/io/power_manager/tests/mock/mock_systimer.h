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

#pragma once

#include <gmock/gmock.h>

#include <memory>
#include <vector>

extern "C" {
#include <sys/systick.h>
#include <sys/systimer.h>
}

// Timer object handed out by MockSystimer
struct systimer {
  systimer_callback_t callback;
  void* context;
  bool scheduled;
  bool suspended;
  uint64_t expiration_us;
  uint64_t period_us;  // 0 for a one-shot timer
};

// gMock mock of the system timer driver (<sys/systimer.h>) together with a
// fake time base for <sys/systick.h>.
//
// While an instance exists, the systimer_* and systick_* functions use it;
// calling them without one fails the test. By default the mock behaves like
// the real driver running on a fake clock. The clock starts at 0 and moves
// only when the test calls AdvanceMs() or the code under test calls
// systick_delay_ms(). Callbacks of timers that expire on the way are invoked
// synchronously, in the order of their expiration.
class MockSystimer {
 public:
  MockSystimer();
  ~MockSystimer();

  MockSystimer(const MockSystimer&) = delete;
  MockSystimer& operator=(const MockSystimer&) = delete;

  MOCK_METHOD(systimer_t*, Create,
              (systimer_callback_t callback, void* context));
  MOCK_METHOD(void, Delete, (systimer_t * timer));
  MOCK_METHOD(void, Set, (systimer_t * timer, uint32_t delay_ms));
  MOCK_METHOD(void, SetPeriodic, (systimer_t * timer, uint32_t period_ms));
  MOCK_METHOD(bool, Unset, (systimer_t * timer));
  MOCK_METHOD(systimer_key_t, Suspend, (systimer_t * timer));
  MOCK_METHOD(void, Resume, (systimer_t * timer, systimer_key_t key));

  uint64_t NowUs() const { return now_us_; }
  uint32_t NowMs() const { return (uint32_t)(now_us_ / 1000); }

  // Move the clock forward, invoking callbacks of the expired timers
  void AdvanceUs(uint64_t us);
  void AdvanceMs(uint32_t ms) { AdvanceUs((uint64_t)ms * 1000); }

  // True if the timer is scheduled to expire
  bool IsScheduled(const systimer_t* timer) const;

 private:
  systimer_t* FakeCreate(systimer_callback_t callback, void* context);
  void FakeDelete(systimer_t* timer);
  systimer_t* Find(const systimer_t* timer) const;

  uint64_t now_us_ = 0;
  std::vector<std::unique_ptr<systimer_t>> timers_;
};
