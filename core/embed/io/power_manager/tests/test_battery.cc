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

// Unit tests of the alkaline fuel gauge driver (fuel_gauge/alkaline/battery.c)
// covering bat_init(), bat_fg_feed_sample() and bat_fg_initial_guess(), and
// a replay of the measured vectors/*.csv files.

#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <ostream>
#include <sstream>
#include <string>
#include <vector>

#include "mock/mock_hal_gpio.h"
#include "mock/mock_systimer.h"

extern "C" {
#include "battery.h"
#include "battery_model/include/soc_ocv.h"

// battery_test_access.c
void bat_test_reset(void);
}

using ::testing::_;
using ::testing::AllOf;
using ::testing::Field;
using ::testing::InSequence;
using ::testing::NiceMock;
using ::testing::NotNull;
using ::testing::Pointee;
using ::testing::Return;

// ts_t is a struct, teach gtest to compare and print it
static bool operator==(ts_t a, ts_t b) { return ts_code(a) == ts_code(b); }
static std::ostream& operator<<(std::ostream& os, ts_t status) {
  return os << "ts_t{" << ts_code(status) << "}";
}

namespace {

constexpr float kTempC = 25.0f;
// Accepted by the fuel gauge as a bootloader sample (25..50 mA)
constexpr float kBootCurrentmA = 40.0f;
// Accepted as a bootloader sample with the dummy load on (140..260 mA)
constexpr float kPulseCurrentmA = 190.0f;
// Duration of the dummy load pulse started by the bootloader sample
constexpr uint32_t kPulseTimeoutMs = 500;
// Minimum delay of first sample after the power-on
constexpr uint32_t kPowerOnMinDelayMs = 100;
// Minimum delay of the pulse sample after the bootloader sample
constexpr uint32_t kPulseMinDelayMs = 100;

// Directory with the *.csv vector files, set by the Makefile
#ifndef TEST_VECTORS_DIR
#define TEST_VECTORS_DIR "vectors"
#endif
// Largest allowed |estimate - soc_ref| on measured data
constexpr float kSocRefTolerance = 0.05f;

// One row of a vector file
struct VectorRow {
  uint32_t delay_ms;  // Time from this measurement to the next one
  float voltage_V;
  float current_mA;
  float temp_C;
  float soc_ref;  // Reference SoC (0..1) at the time of the measurement
};

std::vector<std::string> SplitCsvLine(const std::string& line) {
  std::vector<std::string> fields;
  std::istringstream stream(line);
  std::string field;
  while (std::getline(stream, field, ',')) {
    fields.push_back(field);
  }
  return fields;
}

bool ParseFloat(const std::string& text, float* value) {
  char* end;
  *value = strtof(text.c_str(), &end);
  return end != text.c_str() && *end == '\0';
}

bool ParseUint(const std::string& text, uint32_t* value) {
  char* end;
  const unsigned long parsed = strtoul(text.c_str(), &end, 10);
  *value = (uint32_t)parsed;
  return !text.empty() && isdigit((unsigned char)text[0]) && *end == '\0' &&
         parsed <= UINT32_MAX;
}

// Loads a vector file. Its header line names the columns, which may come in
// any order; voltage_V, current_mA, temp_C, soc_ref and delay_ms are
// required.
std::vector<VectorRow> LoadVectors(const std::string& path) {
  std::ifstream file(path);
  if (!file) {
    ADD_FAILURE() << "Cannot open " << path;
    return {};
  }

  enum { kDelay, kVoltage, kCurrent, kTemp, kSocRef, kColumns };
  const char* const names[kColumns] = {"delay_ms", "voltage_V", "current_mA",
                                       "temp_C", "soc_ref"};
  size_t col[kColumns];

  std::string line;
  std::getline(file, line);
  if (!line.empty() && line.back() == '\r') {
    line.pop_back();
  }
  const std::vector<std::string> header = SplitCsvLine(line);
  for (size_t c = 0; c < kColumns; c++) {
    auto it = std::find(header.begin(), header.end(), names[c]);
    if (it == header.end()) {
      ADD_FAILURE() << path << ": missing column " << names[c];
      return {};
    }
    col[c] = it - header.begin();
  }

  std::vector<VectorRow> rows;
  for (int line_no = 2; std::getline(file, line); line_no++) {
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }
    if (line.empty()) {
      continue;
    }
    const std::vector<std::string> fields = SplitCsvLine(line);
    auto field = [&](size_t c) {
      return col[c] < fields.size() ? fields[col[c]] : std::string();
    };
    VectorRow row;
    if (!ParseFloat(field(kVoltage), &row.voltage_V) ||
        !ParseFloat(field(kCurrent), &row.current_mA) ||
        !ParseFloat(field(kTemp), &row.temp_C) ||
        !ParseFloat(field(kSocRef), &row.soc_ref) ||
        !ParseUint(field(kDelay), &row.delay_ms)) {
      ADD_FAILURE() << path << ":" << line_no << ": invalid row '" << line
                    << "'";
      return {};
    }
    rows.push_back(row);
  }
  return rows;
}

class BatteryTest : public ::testing::Test {
 protected:
  void SetUp() override { bat_test_reset(); }

  static GPIO_PinState DummyLoadPin() {
    return MockHalGpio::PinState(CUR_DUMMY_EN_PORT, CUR_DUMMY_EN_PIN);
  }

  // Feeds the bootloader sample, then the dummy load pulse sample
  void FeedBootAndPulseSamples(float boot_V, float pulse_V) {
    ASSERT_EQ(bat_fg_feed_sample(boot_V, kBootCurrentmA, kTempC), TS_OK);
    systimer_.AdvanceMs(kPulseMinDelayMs + 50);
    ASSERT_EQ(bat_fg_feed_sample(pulse_V, kPulseCurrentmA, kTempC), TS_OK);
  }

  NiceMock<MockHalGpio> gpio_;
  NiceMock<MockSystimer> systimer_;
};

TEST_F(BatteryTest, InitDrivesDummyLoadLowBeforeEnablingOutput) {
  {
    InSequence seq;
    EXPECT_CALL(systimer_, Create(NotNull(), _));
    EXPECT_CALL(gpio_,
                WritePin(CUR_DUMMY_EN_PORT, CUR_DUMMY_EN_PIN, GPIO_PIN_RESET));
    EXPECT_CALL(
        gpio_, Init(CUR_DUMMY_EN_PORT,
                    Pointee(AllOf(
                        Field(&GPIO_InitTypeDef::Pin, CUR_DUMMY_EN_PIN),
                        Field(&GPIO_InitTypeDef::Mode, GPIO_MODE_OUTPUT_PP)))));
  }

  EXPECT_EQ(bat_init(), TS_OK);
  EXPECT_EQ(DummyLoadPin(), GPIO_PIN_RESET);
  EXPECT_FALSE(bat_fg_is_locked());
}

TEST_F(BatteryTest, InitTwiceKeepsDriverState) {
  EXPECT_CALL(systimer_, Create(_, _)).Times(1);

  ASSERT_EQ(bat_init(), TS_OK);
  systimer_.AdvanceMs(kPowerOnMinDelayMs);
  ASSERT_EQ(bat_fg_feed_sample(1.5f, kBootCurrentmA, kTempC), TS_OK);
  EXPECT_EQ(bat_init(), TS_OK);

  // Samples fed before the second call are not lost
  systimer_.AdvanceMs(kPulseMinDelayMs + 50);
  ASSERT_EQ(bat_fg_feed_sample(1.47f, kPulseCurrentmA, kTempC), TS_OK);
  EXPECT_EQ(bat_fg_initial_guess(), TS_OK);
}

TEST_F(BatteryTest, InitFailsWithoutPulseTimer) {
  EXPECT_CALL(systimer_, Create(_, _)).WillOnce(Return(nullptr));
  EXPECT_CALL(gpio_, Init(_, _)).Times(0);

  EXPECT_EQ(bat_init(), TS_ENOMEM);

  // The driver stays uninitialized
  EXPECT_EQ(bat_fg_feed_sample(1.5f, kBootCurrentmA, kTempC), TS_ENOINIT);
  EXPECT_EQ(bat_fg_initial_guess(), TS_ENOINIT);
  EXPECT_FALSE(bat_fg_is_locked());
}

TEST_F(BatteryTest, InitialGuessFailsWithoutSamples) {
  ASSERT_EQ(bat_init(), TS_OK);

  EXPECT_EQ(bat_fg_initial_guess(), TS_EINVAL);
  EXPECT_FALSE(bat_fg_is_locked());
}

TEST_F(BatteryTest, BootSampleStartsTimedDummyLoadPulse) {
  ASSERT_EQ(bat_init(), TS_OK);
  systimer_.AdvanceMs(kPowerOnMinDelayMs);

  EXPECT_CALL(systimer_, Set(NotNull(), kPulseTimeoutMs));
  EXPECT_EQ(bat_fg_feed_sample(1.5f, kBootCurrentmA, kTempC), TS_OK);
  EXPECT_EQ(DummyLoadPin(), GPIO_PIN_SET);

  // No pulse sample arrives, the timer switches the load off
  systimer_.AdvanceMs(kPulseTimeoutMs - 1);
  EXPECT_EQ(DummyLoadPin(), GPIO_PIN_SET);
  systimer_.AdvanceMs(1);
  EXPECT_EQ(DummyLoadPin(), GPIO_PIN_RESET);
}

TEST_F(BatteryTest, BootSampleOutsideCurrentWindowIsIgnored) {
  ASSERT_EQ(bat_init(), TS_OK);

  EXPECT_CALL(gpio_, WritePin(_, _, GPIO_PIN_SET)).Times(0);
  EXPECT_EQ(bat_fg_feed_sample(1.5f, 10.0f, kTempC), TS_OK);
  EXPECT_EQ(bat_fg_feed_sample(1.5f, 60.0f, kTempC), TS_OK);

  EXPECT_EQ(bat_fg_initial_guess(), TS_EINVAL);
}

TEST_F(BatteryTest, PulseSampleTooEarlyIsIgnored) {
  ASSERT_EQ(bat_init(), TS_OK);
  systimer_.AdvanceMs(kPowerOnMinDelayMs);
  ASSERT_EQ(bat_fg_feed_sample(1.35f, kBootCurrentmA, kTempC), TS_OK);

  systimer_.AdvanceMs(kPulseMinDelayMs - 50);
  ASSERT_EQ(bat_fg_feed_sample(1.32f, kPulseCurrentmA, kTempC), TS_OK);
  EXPECT_EQ(DummyLoadPin(), GPIO_PIN_SET);
  EXPECT_EQ(bat_fg_initial_guess(), TS_EINVAL);

  systimer_.AdvanceMs(100);
  ASSERT_EQ(bat_fg_feed_sample(1.32f, kPulseCurrentmA, kTempC), TS_OK);
  EXPECT_EQ(bat_fg_initial_guess(), TS_OK);
}

TEST_F(BatteryTest, InitialGuessEstimatesSocFromPulse) {
  ASSERT_EQ(bat_init(), TS_OK);
  systimer_.AdvanceMs(kPowerOnMinDelayMs);

  // ESR = (1.350 V - 1.320 V) / (190 mA - 40 mA) = 0.2 Ohm
  // OCV = 1.320 V + 190 mA * 0.2 Ohm = 1.358 V
  FeedBootAndPulseSamples(1.35f, 1.32f);
  EXPECT_EQ(DummyLoadPin(), GPIO_PIN_RESET);

  ASSERT_EQ(bat_fg_initial_guess(), TS_OK);
  EXPECT_TRUE(bat_fg_is_locked());

  bat_fg_state_t state;
  ASSERT_EQ(bat_fg_get_state(&state), TS_OK);
  const float expected_soc =
      soc_ocv_lut(1358, (int16_t)(kTempC * 10)) / (float)SOC_OCV_FULL;
  EXPECT_GT(expected_soc, 0.1f);
  EXPECT_LT(expected_soc, 0.9f);
  EXPECT_NEAR(state.soc, expected_soc, 0.01f);
  EXPECT_FLOAT_EQ(state.soc_latched, state.soc);
}

// Replays a vector file as the power manager feeds the measurements: rows go
// to bat_fg_feed_sample() until bat_fg_initial_guess() succeeds, the rest to
// bat_fg_update(), each delay_ms of the previous row after it. The rows are
// taken as recorded, so the dummy load current must be in the data.
class BatteryVectorTest : public BatteryTest,
                          public ::testing::WithParamInterface<const char*> {
 protected:
  void SetUp() override {
    BatteryTest::SetUp();
    rows_ = LoadVectors(std::string(TEST_VECTORS_DIR "/") + GetParam());
    ASSERT_FALSE(rows_.empty());
    ASSERT_EQ(bat_init(), TS_OK);
  }

  // Waits the delay after row i, returns it
  uint32_t WaitAfterRow(size_t i) {
    systimer_.AdvanceMs(rows_[i].delay_ms);
    return rows_[i].delay_ms;
  }

  // Feeds the rows to the unlocked fuel gauge until it makes the initial
  // guess. Returns the index of the last row fed, rows_.size() if no guess.
  size_t ColdBoot() {
    for (size_t i = 0; i < rows_.size(); i++) {
      if (i > 0) {
        WaitAfterRow(i - 1);
      }
      const VectorRow& row = rows_[i];
      EXPECT_EQ(bat_fg_feed_sample(row.voltage_V, row.current_mA, row.temp_C),
                TS_OK)
          << Where(i);
      if (ts_ok(bat_fg_initial_guess())) {
        return i;
      }
    }
    return rows_.size();
  }

  void ExpectReferenceSoc(size_t i) {
    bat_fg_state_t state;
    ASSERT_EQ(bat_fg_get_state(&state), TS_OK);
    EXPECT_NEAR(state.soc_latched, rows_[i].soc_ref, kSocRefTolerance)
        << Where(i);
  }

  // File and line of the row
  std::string Where(size_t i) const {
    return std::string(GetParam()) + ":" + std::to_string(i + 2);
  }

  std::vector<VectorRow> rows_;
};

TEST_P(BatteryVectorTest, InitialGuessMatchesReferenceSoc) {
  const size_t guess_row = ColdBoot();
  ASSERT_LT(guess_row, rows_.size())
      << "No initial guess: the file needs a bootloader row (25..50 mA) "
         "followed by a dummy load pulse row";

  EXPECT_TRUE(bat_fg_is_locked());
  EXPECT_EQ(DummyLoadPin(), GPIO_PIN_RESET);
  ExpectReferenceSoc(guess_row);
}

TEST_P(BatteryVectorTest, UpdateFollowsReferenceSoc) {
  const size_t guess_row = ColdBoot();
  ASSERT_LT(guess_row, rows_.size());

  for (size_t i = guess_row + 1; i < rows_.size(); i++) {
    const uint32_t dt_ms = WaitAfterRow(i - 1);
    const VectorRow& row = rows_[i];
    ASSERT_EQ(bat_fg_update(dt_ms, row.voltage_V, row.current_mA, row.temp_C),
              TS_OK)
        << Where(i);
    ExpectReferenceSoc(i);
  }
}

INSTANTIATE_TEST_SUITE_P(Vectors, BatteryVectorTest,
                         ::testing::Values("test_0pct.csv", "test_15pct.csv",
                                           "test_59pct.csv", "test_68pct.csv",
                                           "test_88pct.csv"),
                         [](const ::testing::TestParamInfo<const char*>& info) {
                           std::string name = info.param;
                           return name.substr(0, name.find('.'));
                         });

}  // namespace
