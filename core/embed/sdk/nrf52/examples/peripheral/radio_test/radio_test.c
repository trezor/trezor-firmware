/**
 * Copyright (c) 2009-2020 - 2021, Nordic Semiconductor ASA
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form, except as embedded into a Nordic
 *    Semiconductor ASA integrated circuit in a product or a software update for
 *    such product, must reproduce the above copyright notice, this list of
 *    conditions and the following disclaimer in the documentation and/or other
 *    materials provided with the distribution.
 *
 * 3. Neither the name of Nordic Semiconductor ASA nor the names of its
 *    contributors may be used to endorse or promote products derived from this
 *    software without specific prior written permission.
 *
 * 4. This software, with or without modification, must only be used with a
 *    Nordic Semiconductor ASA integrated circuit.
 *
 * 5. Any software provided in binary form under this license must not be reverse
 *    engineered, decompiled, modified and/or disassembled.
 *
 * THIS SOFTWARE IS PROVIDED BY NORDIC SEMICONDUCTOR ASA "AS IS" AND ANY EXPRESS
 * OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY, NONINFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL NORDIC SEMICONDUCTOR ASA OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
 * GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 */
/** @file
 * @addtogroup nrf_radio_test_example_main
 * @{
 */

#include "radio_test.h"
#include <stdbool.h>
#include "nrf.h"
#include "nrf_log.h"
#include "app_util_platform.h"

#include "nrf_nvmc.h"
#include "nrf_radio.h"
#include "nrf_rng.h"
#include "nrfx_timer.h"
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
#include "nrf21540.h"
#endif

#define IEEE_DEFAULT_FREQ         (5)   /**< IEEE 802.15.4 default frequency. */
#define RADIO_LENGTH_LENGTH_FIELD (8UL) /**< Length on air of the LENGTH field. */


#define IEEE_FREQ_CALC(_channel) (IEEE_DEFAULT_FREQ + \
                                  (IEEE_DEFAULT_FREQ * ((_channel) - IEEE_MIN_CHANNEL))) /**< Frequency calculation for a given channel in the IEEE 802.15.4 radio mode. */
#define CHAN_TO_FREQ(_channel)   (2400 + _channel)                                       /**< Frequency calculation for a given channel. */

static uint8_t m_tx_packet[RADIO_MAX_PAYLOAD_LEN];                                       /**< Buffer for the radio TX packet. */
static uint8_t m_rx_packet[RADIO_MAX_PAYLOAD_LEN];                                       /**< Buffer for the radio RX packet. */
static uint32_t m_tx_packet_cnt;                                                         /**< Number of transmitted packets. */
static uint32_t m_rx_packet_cnt;                                                         /**< Number of received packets with valid CRC. */
static uint8_t m_current_channel;                                                        /**< Radio current channel (frequency). */
static const nrfx_timer_t m_timer = NRFX_TIMER_INSTANCE(0);                              /**< Timer used for channel sweeps and tx with duty cycle. */
static const radio_test_config_t * m_p_test_config = NULL;                               /**< Test configuration descriptor. */

/**
 * @brief Function for generating an 8-bit random number with the internal random generator.
 */
static uint8_t rnd8(void)
{
    nrf_rng_event_clear(NRF_RNG_EVENT_VALRDY);

    while (!nrf_rng_event_get(NRF_RNG_EVENT_VALRDY))
    {
        /* Do nothing. */
    }

    return nrf_rng_random_value_get();
}


/**brief Function for setting the channel for radio.
 *
 * @param[in] mode    Radio mode.
 * @param[in] channel Radio channel.
 */
static void radio_channel_set(nrf_radio_mode_t mode, uint8_t channel)
{
#if USE_MORE_RADIO_MODES
    if (mode == NRF_RADIO_MODE_IEEE802154_250KBIT)
    {
        if ((channel >= IEEE_MIN_CHANNEL) && (channel <= IEEE_MAX_CHANNEL))
        {
            nrf_radio_frequency_set(CHAN_TO_FREQ(IEEE_FREQ_CALC(channel)));
        }
        else
        {
            nrf_radio_frequency_set(CHAN_TO_FREQ(IEEE_DEFAULT_FREQ));
        }
    } else {
        nrf_radio_frequency_set(CHAN_TO_FREQ(channel));
    }
#else
    nrf_radio_frequency_set(CHAN_TO_FREQ(channel));
#endif /* USE_MORE_RADIO_MODES */
}


/**@brief Function for configuring the radio in every possible mode.
 *
 * @param[in] mode    Radio mode.
 * @param[in] pattern Radio transmission pattern.
 */
static void radio_config(nrf_radio_mode_t mode, transmit_pattern_t pattern)
{
    nrf_radio_packet_conf_t packet_conf;

    /* Reset Radio ramp-up time. */
    nrf_radio_modecnf0_set(false, RADIO_MODECNF0_DTX_Center);
    nrf_radio_crc_configure(RADIO_CRCCNF_LEN_Disabled, NRF_RADIO_CRC_ADDR_INCLUDE, 0);

    /* Set the device address 0 to use when transmitting. */
    nrf_radio_txaddress_set(0);
    /* Enable the device address 0 to use to select which addresses to
     * receive
     */
    nrf_radio_rxaddresses_set(1);

    /* Set the address according to the transmission pattern. */
    switch (pattern)
    {
        case TRANSMIT_PATTERN_RANDOM:
            nrf_radio_prefix0_set(0xAB);
            nrf_radio_base0_set(0xABABABAB);
            break;

        case TRANSMIT_PATTERN_11001100:
            nrf_radio_prefix0_set(0xCC);
            nrf_radio_base0_set(0xCCCCCCCC);
            break;

        case TRANSMIT_PATTERN_11110000:
            nrf_radio_prefix0_set(0x6A);
            nrf_radio_base0_set(0x58FE811B);
            break;

        default:
            return;
    }

    /* Packet configuration:
     * payload length size = 8 bits,
     * 0-byte static length, max 255-byte payload,
     * 4-byte base address length (5-byte full address length),
     * Bit 24: 1 Big endian,
     * Bit 25: 1 Whitening enabled.
     */
    memset(&packet_conf, 0, sizeof(packet_conf));
    packet_conf.lflen = RADIO_LENGTH_LENGTH_FIELD;
    packet_conf.maxlen = (sizeof(m_tx_packet) - 1);
    packet_conf.statlen = 0;
    packet_conf.balen = 4;
    packet_conf.big_endian = true;
    packet_conf.whiteen = true;

    switch (mode)
    {
#if USE_MORE_RADIO_MODES
        case NRF_RADIO_MODE_IEEE802154_250KBIT:
            /* Packet configuration:
             * S1 size = 0 bits,
             * S0 size = 0 bytes,
             * 32-bit preamble.
             */
            packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_32BIT_ZERO;
            packet_conf.maxlen = IEEE_MAX_PAYLOAD_LEN;
            packet_conf.balen = 0;
            packet_conf.big_endian = false;
            packet_conf.whiteen = false;

            /* Set fast ramp-up time. */
            nrf_radio_modecnf0_set(true, RADIO_MODECNF0_DTX_Center);
            break;

        case NRF_RADIO_MODE_BLE_LR500KBIT:
        case NRF_RADIO_MODE_BLE_LR125KBIT:
            /* Packet configuration:
             * S1 size = 0 bits,
             * S0 size = 0 bytes,
             * 10-bit preamble.
             */
            packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_LONG_RANGE;
            packet_conf.maxlen = IEEE_MAX_PAYLOAD_LEN;
            packet_conf.cilen = 2;
            packet_conf.termlen = 3;
            packet_conf.big_endian = false;
            packet_conf.balen = 3;

            /* Set fast ramp-up time. */
            nrf_radio_modecnf0_set(true, RADIO_MODECNF0_DTX_Center);

            /* Set CRC length; CRC calculation does not include the address
             * field.
             */
            nrf_radio_crc_configure(RADIO_CRCCNF_LEN_Three, NRF_RADIO_CRC_ADDR_SKIP, 0);
            break;
#endif /* USE_MORE_RADIO_MODES */

        case NRF_RADIO_MODE_BLE_2MBIT:
            /* Packet configuration:
             * S1 size = 0 bits,
             * S0 size = 0 bytes,
             * 16-bit preamble.
             */
            packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_16BIT;
            break;

        default:
            /* Packet configuration:
             * S1 size = 0 bits,
             * S0 size = 0 bytes,
             * 8-bit preamble.
             */
            packet_conf.plen = NRF_RADIO_PREAMBLE_LENGTH_8BIT;
            break;
    }

    nrf_radio_packet_configure(&packet_conf);
}


/**
 * @brief Function for configuring the radio to use a random address and a 254-byte random payload.
 * The S0 and S1 fields are not used.
 *
 * @param[in] mode Radio mode.
 * @param[in] pattern Radio transmission pattern.
 */
static void generate_modulated_rf_packet(nrf_radio_mode_t mode, transmit_pattern_t pattern)
{
    radio_config(mode, pattern);

    /* One byte used for size, actual size is SIZE-1 */
#if USE_MORE_RADIO_MODES
    if (mode == NRF_RADIO_MODE_IEEE802154_250KBIT)
    {
        m_tx_packet[0] = IEEE_MAX_PAYLOAD_LEN - 1;
    }
    else
    {
        m_tx_packet[0] = sizeof(m_tx_packet) - 1;
    }
#else
    m_tx_packet[0] = sizeof(m_tx_packet) - 1;
#endif /* USE_MORE_RADIO_MODES */

    /* Fill payload with random data. */
    for (uint8_t i = 0; i < sizeof(m_tx_packet) - 1; i++)
    {
        if (pattern == TRANSMIT_PATTERN_RANDOM)
        {
            m_tx_packet[i + 1] = rnd8();
        }
        else if (pattern == TRANSMIT_PATTERN_11001100)
        {
            m_tx_packet[i + 1] = 0xCC;
        }
        else if (pattern == TRANSMIT_PATTERN_11110000)
        {
            m_tx_packet[i + 1] = 0xF0;
        }
        else {
            /* Do nothing. */
        }
    }

    nrf_radio_packetptr_set(m_tx_packet);
}


/**@brief Function for disabling radio.
 */
static void radio_disable(void)
{
    nrf_radio_shorts_set(0);
    nrf_radio_int_disable(~0);
    nrf_radio_event_clear(NRF_RADIO_EVENT_DISABLED);

#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
    (void)nrf21540_power_down(NRF21540_EXECUTE_NOW, NRF21540_EXEC_MODE_BLOCKING);
#else
    nrf_radio_task_trigger(NRF_RADIO_TASK_DISABLE);
    while (!nrf_radio_event_check(NRF_RADIO_EVENT_DISABLED))
    {
        /* Do nothing */
    }
#endif
    nrf_radio_event_clear(NRF_RADIO_EVENT_DISABLED);
}


static void radio_unmodulated_tx_carrier(nrf_radio_mode_t mode,
                                         nrf_radio_txpower_t txpower,
                                         uint8_t channel)
{
    radio_disable();

    nrf_radio_mode_set(mode);
#if !defined(NRF21540_DRIVER_ENABLE) || (NRF21540_DRIVER_ENABLE == 0)
    nrf_radio_shorts_enable(NRF_RADIO_SHORT_READY_START_MASK);
#endif
    nrf_radio_txpower_set(txpower);

    radio_channel_set(mode, channel);

#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
    (void)nrf21540_tx_set(NRF21540_EXECUTE_NOW, NRF21540_EXEC_MODE_NON_BLOCKING);
#else
    nrf_radio_task_trigger(NRF_RADIO_TASK_TXEN);
#endif
}


/**
 * @brief Function for starting the modulated TX carrier by repeatedly sending a packet with a random address and
 * a random payload.
 */
static void radio_modulated_tx_carrier(nrf_radio_mode_t mode,
                                       nrf_radio_txpower_t txpower,
                                       uint8_t channel,
                                       transmit_pattern_t pattern)
{
    radio_disable();
    generate_modulated_rf_packet(mode, pattern);

    switch (mode)
    {
#if USE_MORE_RADIO_MODES
        case NRF_RADIO_MODE_IEEE802154_250KBIT:
        case NRF_RADIO_MODE_BLE_LR125KBIT:
        case NRF_RADIO_MODE_BLE_LR500KBIT:
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
            nrf_radio_shorts_enable(NRF_RADIO_SHORT_PHYEND_START_MASK);
#else
            nrf_radio_shorts_enable(NRF_RADIO_SHORT_READY_START_MASK |
                                    NRF_RADIO_SHORT_PHYEND_START_MASK);
#endif
            break;
#endif /* USE_MORE_RADIO_MODES */

        case NRF_RADIO_MODE_BLE_1MBIT:
        case NRF_RADIO_MODE_BLE_2MBIT:
        case NRF_RADIO_MODE_NRF_1MBIT:
        case NRF_RADIO_MODE_NRF_2MBIT:
        default:
#ifdef NRF52832_XXAA
        case NRF_RADIO_MODE_NRF_250KBIT:
#endif /* NRF52832_XXAA */
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
            nrf_radio_shorts_enable(NRF_RADIO_SHORT_END_START_MASK);
#else
            nrf_radio_shorts_enable(NRF_RADIO_SHORT_READY_START_MASK |
                                    NRF_RADIO_SHORT_END_START_MASK);
#endif
            break;
    }

    nrf_radio_mode_set(mode);
    nrf_radio_txpower_set(txpower);

    radio_channel_set(mode, channel);

    m_tx_packet_cnt = 0;

    nrf_radio_event_clear(NRF_RADIO_EVENT_END);
    nrf_radio_int_enable(NRF_RADIO_INT_END_MASK);
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
    (void)nrf21540_tx_set(NRF21540_EXECUTE_NOW, NRF21540_EXEC_MODE_NON_BLOCKING);
#else
    nrf_radio_task_trigger(NRF_RADIO_TASK_TXEN);
#endif
    while (!nrf_radio_event_check(NRF_RADIO_EVENT_END))
    {
        /* Do nothing */
    }

}


static void radio_modulated_tx_carrier_duty_cycle(nrf_radio_mode_t mode,
                                                  nrf_radio_txpower_t txpower,
                                                  uint8_t channel,
                                                  transmit_pattern_t pattern,
                                                  uint32_t duty_cycle)
{
    // Lookup table with time per byte in each radio MODE
    // Mapped per NRF_RADIO->MODE available on nRF5-series devices @ref <insert ref to mode register>
    static const uint8_t time_in_us_per_byte[16] =
    {8, 4, 32, 8, 4, 64, 16, 0, 0, 0, 0, 0, 0, 0, 0, 32};
    // 1 byte preamble, 5 byte address (BALEN + PREFIX), and sizeof(payload), no CRC
    const uint32_t total_payload_size     = 1 + 5 + sizeof(m_tx_packet);
    const uint32_t total_time_per_payload = time_in_us_per_byte[mode] * total_payload_size;
    // Duty cycle = 100 * Time_on / (time_on + time_off), we need to calculate "time_off" for delay.
    // In addition, the timer includes the "total_time_per_payload", so we need to add this to the total timer cycle.
    uint32_t delay_time = total_time_per_payload +
                          ((100 * total_time_per_payload -
                            (total_time_per_payload * duty_cycle)) / duty_cycle);

    CRITICAL_REGION_ENTER();
    radio_disable();
    generate_modulated_rf_packet(mode, pattern);

    nrf_radio_mode_set(mode);
    nrf_radio_shorts_enable(NRF_RADIO_SHORT_READY_START_MASK |
                            NRF_RADIO_SHORT_END_DISABLE_MASK);
    nrf_radio_txpower_set(txpower);
    radio_channel_set(mode, channel);

    /* We let the TIMER start the radio transmission again. */
    nrfx_timer_disable(&m_timer);
    nrf_timer_shorts_disable(m_timer.p_reg, ~0);
    nrf_timer_int_disable(m_timer.p_reg, ~0);

    nrfx_timer_extended_compare(&m_timer,
                                NRF_TIMER_CC_CHANNEL1,
                                nrfx_timer_us_to_ticks(&m_timer, delay_time),
                                NRF_TIMER_SHORT_COMPARE1_CLEAR_MASK,
                                true);

    nrfx_timer_clear(&m_timer);
    nrfx_timer_enable(&m_timer);
    CRITICAL_REGION_EXIT();
}


static void radio_rx(nrf_radio_mode_t mode, uint8_t channel, transmit_pattern_t pattern)
{
    radio_disable();

    nrf_radio_mode_set(mode);
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
    nrf_radio_shorts_enable(NRF_RADIO_SHORT_END_START_MASK);
#else
    nrf_radio_shorts_enable(NRF_RADIO_SHORT_READY_START_MASK |
                            NRF_RADIO_SHORT_END_START_MASK);
#endif
    nrf_radio_packetptr_set(m_rx_packet);

    radio_config(mode, pattern);
    radio_channel_set(mode, channel);

    m_rx_packet_cnt = 0;

    nrf_radio_int_enable(NRF_RADIO_INT_CRCOK_MASK);
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
    (void)nrf21540_rx_set(NRF21540_EXECUTE_NOW, NRF21540_EXEC_MODE_NON_BLOCKING);
#else
    nrf_radio_task_trigger(NRF_RADIO_TASK_RXEN);
#endif
}


static void radio_sweep_start(uint8_t channel, uint32_t delay_ms)
{
    m_current_channel = channel;

    nrfx_timer_disable(&m_timer);
    nrf_timer_shorts_disable(m_timer.p_reg, ~0);
    nrf_timer_int_disable(m_timer.p_reg, ~0);

    nrfx_timer_extended_compare(&m_timer,
            NRF_TIMER_CC_CHANNEL0,
            nrfx_timer_ms_to_ticks(&m_timer, delay_ms),
            NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK,
            true);

    nrfx_timer_clear(&m_timer);
    nrfx_timer_enable(&m_timer);
}


void radio_test_start(radio_test_config_t * p_config)
{
    switch (p_config->type)
    {
        case UNMODULATED_TX:
            radio_unmodulated_tx_carrier(p_config->mode,
                                         p_config->params.unmodulated_tx.txpower,
                                         p_config->params.unmodulated_tx.channel);
            break;
        case MODULATED_TX:
            radio_modulated_tx_carrier(p_config->mode,
                                       p_config->params.modulated_tx.txpower,
                                       p_config->params.modulated_tx.channel,
                                       p_config->params.modulated_tx.pattern);
            break;
        case RX:
            radio_rx(p_config->mode,
                     p_config->params.rx.channel,
                     p_config->params.rx.pattern);
            break;
        case TX_SWEEP:
            radio_sweep_start(p_config->params.tx_sweep.channel_start,
                              p_config->params.tx_sweep.delay_ms);
            break;
        case RX_SWEEP:
            radio_sweep_start(p_config->params.rx_sweep.channel_start,
                              p_config->params.rx_sweep.delay_ms);
            break;
        case MODULATED_TX_DUTY_CYCLE:
            radio_modulated_tx_carrier_duty_cycle(p_config->mode,
                                                  p_config->params.modulated_tx_duty_cycle.txpower,
                                                  p_config->params.modulated_tx_duty_cycle.channel,
                                                  p_config->params.modulated_tx_duty_cycle.pattern,
                                                  p_config->params.modulated_tx_duty_cycle.duty_cycle);
            break;
    }
}


void radio_test_cancel(void)
{
    nrfx_timer_disable(&m_timer);
    radio_disable();
}


void radio_rx_stats_get(radio_rx_stats_t * p_rx_stats)
{
    size_t size;

#if USE_MORE_RADIO_MODES
    nrf_radio_mode_t radio_mode;

    radio_mode = nrf_radio_mode_get();
    if (radio_mode == NRF_RADIO_MODE_IEEE802154_250KBIT)
    {
        size = IEEE_MAX_PAYLOAD_LEN;
    }
    else
    {
        size = sizeof(m_rx_packet);
    }
#else
    size = sizeof(m_rx_packet);
#endif /* USE_MORE_RADIO_MODES */

    p_rx_stats->last_packet.buf = m_rx_packet;
    p_rx_stats->last_packet.len = size;
    p_rx_stats->packet_cnt = m_rx_packet_cnt;
}


void toggle_dcdc_state(uint8_t dcdc_state)
{
#ifdef NRF52840_XXAA
    if (dcdc_state == 0)
    {
        NRF_POWER->DCDCEN0 = (NRF_POWER->DCDCEN0 == POWER_DCDCEN0_DCDCEN_Disabled) ? 1 : 0;
    }
    else if (dcdc_state == 1)
    {
        NRF_POWER->DCDCEN = (NRF_POWER->DCDCEN == POWER_DCDCEN_DCDCEN_Disabled) ? 1 : 0;
    }
    else
    {
        // Do nothing.
    }
#else
    if (dcdc_state <= 1)
    {
        NRF_POWER->DCDCEN = dcdc_state;
    }
#endif // NRF52840_XXAA
}


/**
 * @brief Function for handling the Timer 0 interrupt used for the TX or RX sweep. The carrier is started with the new channel,
 * and the channel is incremented for the next interrupt.
 */
static void timer_handler(nrf_timer_event_t event_type, void * p_context)
{
    const radio_test_config_t * p_config = (const radio_test_config_t *) p_context;

    if (event_type == NRF_TIMER_EVENT_COMPARE0)
    {
        uint8_t channel_start;
        uint8_t channel_end;

        if (p_config->type == TX_SWEEP)
        {
            radio_unmodulated_tx_carrier(p_config->mode,
                                         p_config->params.tx_sweep.txpower,
                                         m_current_channel);

            channel_start = p_config->params.tx_sweep.channel_start;
            channel_end   = p_config->params.tx_sweep.channel_end;
        }
        else if (p_config->type == RX_SWEEP)
        {
            radio_rx(p_config->mode, m_current_channel, p_config->params.rx.pattern);

            channel_start = p_config->params.rx_sweep.channel_start;
            channel_end   = p_config->params.rx_sweep.channel_end;
        }
        else
        {
            NRF_LOG_ERROR("Unexpected test type: %d\n", p_config->type);
            return;
        }

        m_current_channel++;
        if (m_current_channel > channel_end)
        {
                m_current_channel = channel_start;
        }
    }

    if (event_type == NRF_TIMER_EVENT_COMPARE1)
    {
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
        (void)nrf21540_tx_set(NRF21540_EXECUTE_NOW, NRF21540_EXEC_MODE_NON_BLOCKING);
#else
        nrf_radio_task_trigger(NRF_RADIO_TASK_TXEN);
#endif
    }
}


static void timer_init(const radio_test_config_t * p_config)
{
    nrfx_err_t          err;
    nrfx_timer_config_t timer_cfg =
    {
        .frequency = NRF_TIMER_FREQ_1MHz,
        .mode      = NRF_TIMER_MODE_TIMER,
        .bit_width = NRF_TIMER_BIT_WIDTH_24,
        .p_context = (void *) p_config,
#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
        // nRF21540 driver interrupts need to have higher interrupts priorities than interrupt which services nRF21540.
        .interrupt_priority = NRFX_TIMER_DEFAULT_CONFIG_IRQ_PRIORITY + 1,
#else
        .interrupt_priority = NRFX_TIMER_DEFAULT_CONFIG_IRQ_PRIORITY,
#endif
    };

    err = nrfx_timer_init(&m_timer, &timer_cfg, timer_handler);
    if (err != NRFX_SUCCESS)
    {
        NRF_LOG_ERROR("nrfx_timer_init failed with: %d\n", err);
    }
}


void RADIO_IRQHandler(void)
{
    if (nrf_radio_event_check(NRF_RADIO_EVENT_CRCOK))
    {
        nrf_radio_event_clear(NRF_RADIO_EVENT_CRCOK);
        m_rx_packet_cnt++;
    }

    if (nrf_radio_event_check(NRF_RADIO_EVENT_END))
    {
        nrf_radio_event_clear(NRF_RADIO_EVENT_END);

        m_tx_packet_cnt++;
        if (m_tx_packet_cnt == m_p_test_config->params.modulated_tx.packets_num)
        {
            radio_disable();
            m_p_test_config->params.modulated_tx.cb();
        }
    }
}


void radio_test_init(radio_test_config_t * p_config)
{
    if (!m_p_test_config)
    {
        nrf_rng_task_trigger(NRF_RNG_TASK_START);

#ifdef NVMC_ICACHECNF_CACHEEN_Msk
        nrf_nvmc_icache_config_set(NRF_NVMC, NRF_NVMC_ICACHE_ENABLE);
#endif // NVMC_ICACHECNF_CACHEEN_Msk

        timer_init(p_config);

#if defined(NRF21540_DRIVER_ENABLE) && (NRF21540_DRIVER_ENABLE == 1)
        // nRF21540 driver interrupts need to have higher interrupts priorities than interrupt which services nRF21540.
        NVIC_SetPriority(RADIO_IRQn, NRFX_TIMER_DEFAULT_CONFIG_IRQ_PRIORITY + 1);
#endif
        NVIC_EnableIRQ(RADIO_IRQn);
        __enable_irq();

        m_p_test_config = p_config;
    }
    else
    {
        // Already initialized, do nothing
    }
}

/**
 * @}
 */
