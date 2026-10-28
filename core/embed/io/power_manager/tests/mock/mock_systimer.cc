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

#include "mock_systimer.h"

#include <algorithm>

using ::testing::_;

static MockSystimer* g_mock_systimer = nullptr;

MockSystimer::MockSystimer() {
  EXPECT_EQ(g_mock_systimer, nullptr) << "Only one MockSystimer may exist";
  g_mock_systimer = this;

  ON_CALL(*this, Create(_, _))
      .WillByDefault([this](systimer_callback_t callback, void* context) {
        return FakeCreate(callback, context);
      });
  ON_CALL(*this, Delete(_)).WillByDefault([this](systimer_t* timer) {
    FakeDelete(timer);
  });
  ON_CALL(*this, Set(_, _))
      .WillByDefault([this](systimer_t* timer, uint32_t delay_ms) {
        if (systimer_t* t = Find(timer)) {
          t->expiration_us = now_us_ + (uint64_t)delay_ms * 1000;
          t->period_us = 0;
          t->scheduled = true;
        }
      });
  ON_CALL(*this, SetPeriodic(_, _))
      .WillByDefault([this](systimer_t* timer, uint32_t period_ms) {
        if (systimer_t* t = Find(timer)) {
          t->period_us = (uint64_t)period_ms * 1000;
          t->expiration_us = now_us_ + t->period_us;
          t->scheduled = true;
        }
      });
  ON_CALL(*this, Unset(_)).WillByDefault([this](systimer_t* timer) {
    systimer_t* t = Find(timer);
    if (t == nullptr) {
      return false;
    }
    bool was_scheduled = t->scheduled;
    t->scheduled = false;
    return was_scheduled;
  });
  ON_CALL(*this, Suspend(_)).WillByDefault([this](systimer_t* timer) {
    systimer_t* t = Find(timer);
    if (t == nullptr) {
      return false;
    }
    bool was_suspended = t->suspended;
    t->suspended = true;
    return was_suspended;
  });
  ON_CALL(*this, Resume(_, _))
      .WillByDefault([this](systimer_t* timer, systimer_key_t key) {
        if (systimer_t* t = Find(timer)) {
          t->suspended = key;
        }
      });
}

MockSystimer::~MockSystimer() { g_mock_systimer = nullptr; }

void MockSystimer::AdvanceUs(uint64_t us) {
  const uint64_t end_us = now_us_ + us;

  for (;;) {
    // Earliest timer that expires until `end_us`
    systimer_t* next = nullptr;
    for (const auto& t : timers_) {
      if (t->scheduled && !t->suspended && t->expiration_us <= end_us &&
          (next == nullptr || t->expiration_us < next->expiration_us)) {
        next = t.get();
      }
    }
    if (next == nullptr) {
      break;
    }

    now_us_ = std::max(now_us_, next->expiration_us);

    if (next->period_us > 0) {
      next->expiration_us += next->period_us;
    } else {
      next->scheduled = false;
    }

    // The callback may create, set or delete timers
    next->callback(next->context);
  }

  now_us_ = std::max(now_us_, end_us);
}

bool MockSystimer::IsScheduled(const systimer_t* timer) const {
  systimer_t* t = Find(timer);
  return t != nullptr && t->scheduled;
}

systimer_t* MockSystimer::FakeCreate(systimer_callback_t callback,
                                     void* context) {
  if (callback == nullptr) {
    return nullptr;
  }
  timers_.push_back(std::make_unique<systimer_t>(
      systimer_t{callback, context, false, false, 0, 0}));
  return timers_.back().get();
}

void MockSystimer::FakeDelete(systimer_t* timer) {
  auto it = std::find_if(timers_.begin(), timers_.end(),
                         [timer](const auto& t) { return t.get() == timer; });
  if (it == timers_.end()) {
    ADD_FAILURE() << "Unknown or deleted systimer " << timer;
    return;
  }
  timers_.erase(it);
}

systimer_t* MockSystimer::Find(const systimer_t* timer) const {
  for (const auto& t : timers_) {
    if (t.get() == timer) {
      return t.get();
    }
  }
  ADD_FAILURE() << "Unknown or deleted systimer " << timer;
  return nullptr;
}

static MockSystimer* active_mock(const char* fn) {
  if (g_mock_systimer == nullptr) {
    ADD_FAILURE() << fn << "() called without a MockSystimer instance";
  }
  return g_mock_systimer;
}

extern "C" {

systimer_t* systimer_create(systimer_callback_t callback, void* context) {
  if (MockSystimer* mock = active_mock(__func__)) {
    return mock->Create(callback, context);
  }
  return NULL;
}

void systimer_delete(systimer_t* timer) {
  if (MockSystimer* mock = active_mock(__func__)) {
    mock->Delete(timer);
  }
}

void systimer_set(systimer_t* timer, uint32_t delay_ms) {
  if (MockSystimer* mock = active_mock(__func__)) {
    mock->Set(timer, delay_ms);
  }
}

void systimer_set_periodic(systimer_t* timer, uint32_t period_ms) {
  if (MockSystimer* mock = active_mock(__func__)) {
    mock->SetPeriodic(timer, period_ms);
  }
}

bool systimer_unset(systimer_t* timer) {
  if (MockSystimer* mock = active_mock(__func__)) {
    return mock->Unset(timer);
  }
  return false;
}

systimer_key_t systimer_suspend(systimer_t* timer) {
  if (MockSystimer* mock = active_mock(__func__)) {
    return mock->Suspend(timer);
  }
  return false;
}

void systimer_resume(systimer_t* timer, systimer_key_t key) {
  if (MockSystimer* mock = active_mock(__func__)) {
    mock->Resume(timer, key);
  }
}

// The fake clock counts cycles in microseconds
uint64_t systick_cycles(void) { return systick_us(); }

uint64_t systick_us_to_cycles(uint64_t us) { return us; }

uint64_t systick_us(void) {
  if (MockSystimer* mock = active_mock(__func__)) {
    return mock->NowUs();
  }
  return 0;
}

uint32_t systick_ms(void) {
  if (MockSystimer* mock = active_mock(__func__)) {
    return mock->NowMs();
  }
  return 0;
}

void systick_delay_us(uint64_t us) {
  if (MockSystimer* mock = active_mock(__func__)) {
    mock->AdvanceUs(us);
  }
}

void systick_delay_ms(uint32_t ms) {
  if (MockSystimer* mock = active_mock(__func__)) {
    mock->AdvanceMs(ms);
  }
}

}  // extern "C"
