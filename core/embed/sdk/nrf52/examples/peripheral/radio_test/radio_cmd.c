/**
 * Copyright (c) 2018-2020 - 2021, Nordic Semiconductor ASA
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
#include <stdlib.h>
#include "nrf_cli.h"
#include "nrf_log.h"
#include "radio_test.h"

/** Indicates devices that support BLE LR and 802.15.4 radio modes. */
#if defined(NRF52840_XXAA) || defined(NRF52833_XXAA) || defined(NRF52820_XXAA)
    #define USE_MORE_NRF52_RADIO_POWER_OPTIONS 1
#else
    #define USE_MORE_NRF52_RADIO_POWER_OPTIONS 0
#endif

#if defined(NRF52832_XXAA) || defined(NRF52833_XXAA)
    #define TOGGLE_DCDC_HELP \
    "Toggle DCDC state <state>, if state = 1 then DC/DC converter is enabled"
#else
    #define TOGGLE_DCDC_HELP                                       \
    "Toggle DCDC state <state>, "                                  \
    "if state = 1 then toggle DC/DC REG1 state, or if state = 0 "  \
    "then toggle DC/DC REG0 state"
#endif


/**@brief Radio parameter configuration.
 */
typedef struct radio_param_config {
    transmit_pattern_t tx_pattern; /**< Radio transmission pattern. */
    nrf_radio_mode_t mode;         /**< Radio mode. Data rate and modulation. */
    nrf_radio_txpower_t txpower;   /**< Radio output power. */
    uint8_t channel_start;         /**< Radio start channel (frequency). */
    uint8_t channel_end;           /**< Radio end channel (frequency). */
    uint32_t delay_ms;             /**< Delay time in milliseconds. */
    uint32_t duty_cycle;           /**< Duty cycle. */
} radio_param_config_t;

static radio_test_config_t  m_test_config;      /**< Radio test configuration. */
static bool                 m_test_in_progress; /**< If true, RX sweep, TX sweep or duty cycle test is performed. */
static radio_param_config_t m_config =
{
    .tx_pattern = TRANSMIT_PATTERN_RANDOM,
    .mode = NRF_RADIO_MODE_BLE_1MBIT,
    .txpower = NRF_RADIO_TXPOWER_0DBM,
    .channel_start = 0,
    .channel_end = 80,
    .delay_ms = 10,
    .duty_cycle = 50,
};


void radio_cmd_init(void)
{
    radio_test_init(&m_test_config);
}


#if USE_MORE_RADIO_MODES
static void ieee_channel_check(nrf_cli_t const * p_cli, uint8_t channel)
{
    if (m_config.mode == RADIO_MODE_MODE_Ieee802154_250Kbit)
    {
        if ((channel < IEEE_MIN_CHANNEL) || (channel > IEEE_MAX_CHANNEL))
        {
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_ERROR, 
                            "For %s mode channel must be between %d and %d.\r\n",
                            STRINGIFY_(RADIO_MODE_MODE_Ieee802154_250Kbit),
                            IEEE_MIN_CHANNEL,
                            IEEE_MAX_CHANNEL);

            nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Channel set to %d.\r\n", IEEE_MIN_CHANNEL);
        }

    }
}
#endif // USE_MORE_RADIO_MODES


static void cmd_start_channel_set(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count.\r\n", argv[0]);
        return;
    }

    uint32_t channel;

    channel = atoi(argv[1]);

    if (channel > 80)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "Channel must be between 0 and 80.\r\n");
        return;
    }

    m_config.channel_start = (uint8_t)channel;

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Start channel set to: %d.\r\n", channel);
}


static void cmd_end_channel_set(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count.\r\n", argv[0]);
        return;
    }

    uint32_t channel;

    channel = atoi(argv[1]);

    if (channel > 80)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "Channel must be between 0 and 80.\r\n");
        return;
    }

    m_config.channel_end = (uint8_t)channel;

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "End channel set to: %d.\r\n", channel);
}


static void cmd_time_set(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count.\r\n", argv[0]);
        return;
    }

    uint32_t time;

    time = atoi(argv[1]);

    if (time > 99)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "Delay time must be between 0 and 99 ms.\r\n");
        return;
    }

    m_config.delay_ms = time;

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Delay time set to: %d.\r\n", time);
}


static void cmd_cancel(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    radio_test_cancel();
}


static void cmd_data_rate_set(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count.\r\n", argv[0]);
        return;
    }

    if (argc == 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "Uknown argument: %s.\r\n", argv[1]);
    }
}


static void cmd_tx_carrier_start(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (m_test_in_progress)
    {
        radio_test_cancel();
        m_test_in_progress = false;
    }

#if USE_MORE_RADIO_MODES
    ieee_channel_check(p_cli, m_config.channel_start);
#endif /* USE_MORE_RADIO_MODES */

    memset(&m_test_config, 0, sizeof(m_test_config));
    m_test_config.type                          = UNMODULATED_TX;
    m_test_config.mode                          = m_config.mode;
    m_test_config.params.unmodulated_tx.txpower = m_config.txpower;
    m_test_config.params.unmodulated_tx.channel = m_config.channel_start;

    radio_test_start(&m_test_config);

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Start the TX carrier.\r\n");
}

static void tx_modulated_carrier_end(void)
{
    NRF_LOG_INFO("The modulated TX has finished\n");
}

static void cmd_tx_modulated_carrier_start(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (m_test_in_progress)
    {
        radio_test_cancel();
        m_test_in_progress = false;
    }

#if USE_MORE_RADIO_MODES
    ieee_channel_check(p_cli, m_config.channel_start);
#endif /* USE_MORE_RADIO_MODES */

    memset(&m_test_config, 0, sizeof(m_test_config));
    m_test_config.type                        = MODULATED_TX;
    m_test_config.mode                        = m_config.mode;
    m_test_config.params.modulated_tx.txpower = m_config.txpower;
    m_test_config.params.modulated_tx.channel = m_config.channel_start;
    m_test_config.params.modulated_tx.pattern = m_config.tx_pattern;

    if (argc == 2) {
        m_test_config.params.modulated_tx.packets_num = atoi(argv[1]);
        m_test_config.params.modulated_tx.cb = tx_modulated_carrier_end;
    }

    radio_test_start(&m_test_config);

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Start the modulated TX carrier.\r\n");
}


static void cmd_duty_cycle_set(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count.\r\n", argv[0]);
        return;
    }

    uint32_t duty_cycle;

    duty_cycle = atoi(argv[1]);

    if (duty_cycle > 100)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Duty cycle must be between 1 and 99.\r\n");
        return;
    }

    m_config.duty_cycle = duty_cycle;

#if USE_MORE_RADIO_MODES
    ieee_channel_check(p_cli, m_config.channel_start);
#endif /* USE_MORE_RADIO_MODES */

    memset(&m_test_config, 0, sizeof(m_test_config));
    m_test_config.type                                      = MODULATED_TX_DUTY_CYCLE;
    m_test_config.mode                                      = m_config.mode;
    m_test_config.params.modulated_tx_duty_cycle.txpower    = m_config.txpower;
    m_test_config.params.modulated_tx_duty_cycle.pattern    = m_config.tx_pattern;
    m_test_config.params.modulated_tx_duty_cycle.channel    = m_config.channel_start;
    m_test_config.params.modulated_tx_duty_cycle.duty_cycle = m_config.duty_cycle;

    radio_test_start(&m_test_config);
    m_test_in_progress = true;
}


static void cmd_output_power_set(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count.\r\n", argv[0]);
    }

    if (argc == 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "Uknown argument: %s.\r\n", argv[1]);
    }
}


#if USE_MORE_NRF52_RADIO_POWER_OPTIONS
static void cmd_pos8dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_POS8DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_POS8DBM));
}


static void cmd_pos7dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_POS7DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_POS7DBM));
}


static void cmd_pos6dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_POS6DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_POS6DBM));
}


static void cmd_pos5dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_POS5DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_POS5DBM));
}


static void cmd_pos2dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_POS2DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_POS2DBM));
}


#endif // USE_MORE_NRF52_RADIO_POWER_OPTIONS


static void cmd_pos3dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_POS3DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_POS3DBM));
}


static void cmd_pos4dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_POS4DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_POS4DBM));
}


static void cmd_pos0dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_0DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n", 
                    STRINGIFY_(NRF_RADIO_TXPOWER_0DBM));
}


static void cmd_neg4dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_NEG4DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_NEG4DBM));
}


static void cmd_neg8dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_NEG8DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_NEG8DBM));
}


static void cmd_neg12dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_NEG12DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_NEG12DBM));
}


static void cmd_neg16dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_NEG16DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_NEG16DBM));
}


static void cmd_neg20dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_NEG20DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_NEG20DBM));
}


static void cmd_neg30dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_NEG30DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_NEG30DBM));
}


static void cmd_neg40dbm(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.txpower = NRF_RADIO_TXPOWER_NEG40DBM;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "TX power: %s\r\n",
                    STRINGIFY_(NRF_RADIO_TXPOWER_NEG40DBM));
}


static void cmd_transmit_pattern_set(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count.\r\n", argv[0]);
        return;
    }

    if (argc == 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "Uknown argument: %s.\r\n", argv[1]);
    }
}


static void cmd_print(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Parameters:\r\n");

    switch (m_config.mode)
    {
#ifdef NRF52832_XXAA
        case NRF_RADIO_MODE_NRF_250KBIT:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_NRF_250KBIT));
            break;

#endif // NRF52832_XXAA
        case NRF_RADIO_MODE_NRF_1MBIT:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_NRF_1MBIT));
            break;

        case NRF_RADIO_MODE_NRF_2MBIT:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_NRF_2MBIT));
            break;

        case NRF_RADIO_MODE_BLE_1MBIT:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_BLE_1MBIT));
            break;

        case NRF_RADIO_MODE_BLE_2MBIT:
            nrf_cli_fprintf(p_cli,
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_BLE_2MBIT));
            break;

#if USE_MORE_RADIO_MODES
        case NRF_RADIO_MODE_BLE_LR125KBIT:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_BLE_LR125KBIT));
            break;

        case NRF_RADIO_MODE_BLE_LR500KBIT:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_BLE_LR500KBIT));
            break;

        case NRF_RADIO_MODE_IEEE802154_250KBIT:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate: %s\r\n",
                            STRINGIFY_(NRF_RADIO_MODE_IEEE802154_250KBIT));
            break;

#endif // USE_MORE_RADIO_MODES
        default:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "Data rate unknown or deprecated: %lu\n\r", 
                            m_config.mode);
            break;
    }

    switch (m_config.txpower)
    {
#if USE_MORE_NRF52_RADIO_POWER_OPTIONS
        case NRF_RADIO_TXPOWER_POS8DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_POS8DBM));
            break;

        case NRF_RADIO_TXPOWER_POS7DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_POS7DBM));
            break;

        case NRF_RADIO_TXPOWER_POS6DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_POS6DBM));
            break;

        case NRF_RADIO_TXPOWER_POS5DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_POS5DBM));
            break;

        case NRF_RADIO_TXPOWER_POS2DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_POS2DBM));
            break;

#endif // USE_MORE_NRF52_RADIO_POWER_OPTIONS
        case NRF_RADIO_TXPOWER_POS4DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_POS4DBM));
            break;

        case NRF_RADIO_TXPOWER_POS3DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_POS3DBM));
            break;

        case NRF_RADIO_TXPOWER_0DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_0DBM));
            break;

        case NRF_RADIO_TXPOWER_NEG4DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_NEG4DBM));
            break;

        case NRF_RADIO_TXPOWER_NEG8DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_NEG8DBM));
            break;

        case NRF_RADIO_TXPOWER_NEG12DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_NEG12DBM));
            break;

        case NRF_RADIO_TXPOWER_NEG16DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_NEG16DBM));
            break;

        case NRF_RADIO_TXPOWER_NEG20DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_NEG20DBM));
            break;

        case NRF_RADIO_TXPOWER_NEG40DBM:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power: %s\r\n",
                            STRINGIFY_(NRF_RADIO_TXPOWER_NEG40DBM));
            break;

        default:
            nrf_cli_fprintf(p_cli, 
                            NRF_CLI_INFO, 
                            "TX power unknown: %d", 
                            m_config.txpower);
            break;
    }

    switch (m_config.tx_pattern)
    {
        case TRANSMIT_PATTERN_RANDOM:
            nrf_cli_fprintf(p_cli,
                            NRF_CLI_INFO,
                            "Transmission pattern: %s\r\n",
                            STRINGIFY_(TRANSMIT_PATTERN_RANDOM));
            break;

        case TRANSMIT_PATTERN_11110000:
            nrf_cli_fprintf(p_cli,
                            NRF_CLI_INFO,
                            "Transmission pattern: %s\r\n",
                            STRINGIFY_(TRANSMIT_PATTERN_11110000));
            break;

        case TRANSMIT_PATTERN_11001100:
            nrf_cli_fprintf(p_cli,
                            NRF_CLI_INFO,
                            "Transmission pattern: %s\r\n",
                            STRINGIFY_(TRANSMIT_PATTERN_11001100));
            break;

        default:
            nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Transmission pattern unknown: %d", m_config.tx_pattern);
            break;
    }

nrf_cli_fprintf(p_cli, 
                NRF_CLI_INFO, 
                "Start Channel:\t%lu\r\n"
                "End Channel:\t%lu\r\n"
                "Time on each channel: %lu ms\r\n"
                "Duty cycle:\t%lu percent\r\n",
                m_config.channel_start,
                m_config.channel_end,
                m_config.delay_ms,
                m_config.duty_cycle);
}


static void cmd_rx_sweep_start(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    memset(&m_test_config, 0, sizeof(m_test_config));
    m_test_config.type                          = RX_SWEEP;
    m_test_config.mode                          = m_config.mode;
    m_test_config.params.rx_sweep.channel_start = m_config.channel_start;
    m_test_config.params.rx_sweep.channel_end   = m_config.channel_end;
    m_test_config.params.rx_sweep.delay_ms      = m_config.delay_ms;

    radio_test_start(&m_test_config);

    m_test_in_progress = true;

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "RX sweep\r\n");
}


static void cmd_tx_sweep_start(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    memset(&m_test_config, 0, sizeof(m_test_config));
    m_test_config.type                          = TX_SWEEP;
    m_test_config.mode                          = m_config.mode;
    m_test_config.params.tx_sweep.channel_start = m_config.channel_start;
    m_test_config.params.tx_sweep.channel_end   = m_config.channel_end;
    m_test_config.params.tx_sweep.delay_ms      = m_config.delay_ms;
    m_test_config.params.tx_sweep.txpower       = m_config.txpower;

    radio_test_start(&m_test_config);

    m_test_in_progress = true;

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "TX sweep\r\n");
}


static void cmd_rx_start(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (m_test_in_progress)
    {
        radio_test_cancel();
        m_test_in_progress = false;
    }

#if USE_MORE_RADIO_MODES
    ieee_channel_check(p_cli, m_config.channel_start);
#endif /* USE_MORE_RADIO_MODES */

    memset(&m_test_config, 0, sizeof(m_test_config));
    m_test_config.type              = RX;
    m_test_config.mode              = m_config.mode;
    m_test_config.params.rx.channel = m_config.channel_start;
    m_test_config.params.rx.pattern = m_config.tx_pattern;

    radio_test_start(&m_test_config);
}


static void cmd_nrf_1mbit(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.mode = NRF_RADIO_MODE_NRF_1MBIT;
    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Data rate: %s\r\n", STRINGIFY_(NRF_RADIO_MODE_NRF_1MBIT));
}


static void cmd_nrf_2mbit(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.mode = NRF_RADIO_MODE_NRF_2MBIT;
    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Data rate: %s\r\n", STRINGIFY_(NRF_RADIO_MODE_NRF_2MBIT));
}


#ifdef  NRF52832_XXAA
static void cmd_nrf_250kbit(nrf_cli_t const * p_cli, size_t argc, char * * argv)
{
    m_config.mode = NRF_RADIO_MODE_NRF_250KBIT;
    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Data rate: %s\r\n", STRINGIFY(NRF_RADIO_MODE_NRF_250KBIT));
}


#endif // NRF52832_XXAA


static void cmd_ble_1mbit(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.mode = NRF_RADIO_MODE_BLE_1MBIT;
    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Data rate: %s\r\n", STRINGIFY_(NRF_RADIO_MODE_BLE_1MBIT));
}


static void cmd_ble_2mbit(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.mode = NRF_RADIO_MODE_BLE_2MBIT;
    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Data rate: %s\r\n", STRINGIFY_(NRF_RADIO_MODE_BLE_2MBIT));
}


#if USE_MORE_RADIO_MODES
static void cmd_ble_lr125kbit(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.mode = NRF_RADIO_MODE_BLE_LR125KBIT;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "Data rate: %s\r\n",
                    STRINGIFY_(NRF_RADIO_MODE_BLE_LR125KBIT));
}


static void cmd_ble_lr500kbit(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.mode = NRF_RADIO_MODE_BLE_LR500KBIT;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "Data rate: %s\r\n",
                    STRINGIFY_(NRF_RADIO_MODE_BLE_LR500KBIT));
}


static void cmd_ble_ieee(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.mode = NRF_RADIO_MODE_IEEE802154_250KBIT;
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "Data rate: %s\r\n",
                    STRINGIFY_(NRF_RADIO_MODE_IEEE802154_250KBIT));
}


#endif // USE_MORE_RADIO_MODES


static void cmd_pattern_random(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.tx_pattern = TRANSMIT_PATTERN_RANDOM;
    nrf_cli_fprintf(p_cli,
                    NRF_CLI_INFO,
                    "Transmission pattern: %s.\r\n",
                    STRINGIFY_(TRANSMIT_PATTERN_RANDOM));
}


static void cmd_pattern_11110000(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.tx_pattern = TRANSMIT_PATTERN_11110000;
    nrf_cli_fprintf(p_cli,
                    NRF_CLI_INFO,
                    "Transmission pattern: %s.\r\n",
                    STRINGIFY_(TRANSMIT_PATTERN_11110000));
}


static void cmd_pattern_11001100(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    m_config.tx_pattern = TRANSMIT_PATTERN_11001100;
    nrf_cli_fprintf(p_cli,
                    NRF_CLI_INFO,
                    "Transmission pattern: %s.\r\n",
                    STRINGIFY_(TRANSMIT_PATTERN_11001100));
}


static void cmd_toggle_dc(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if ((argc == 1) || nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    if (argc > 2)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "%s: bad parameters count\r\n", argv[0]);
    }

    uint32_t state = atoi(argv[1]);

    if (state > 1)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_ERROR, "Invalid DCDC value provided\n\r");
    }

    toggle_dcdc_state((uint8_t)state);

#ifdef NRF52840_XXAA
    uint32_t dcdcen = NRF_POWER->DCDCEN;

    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "DCDC REG0 state %lu\r\n",
                    "DCDC REG1 state %lu\r\n",
                     "Write '0' to toggle state of DCDC REG0\r\n",
                     "Write '1' to toggle state of DCDC REG1",
                    NRF_POWER->DCDCEN0,
                    dcdcen);
#else
    nrf_cli_fprintf(p_cli, 
                    NRF_CLI_INFO, 
                    "DCDC state %lu\r\n",
                    "Write '1' to enable, '0' to disable\r\n",
                    NRF_POWER->DCDCEN);
#endif
}


static void cmd_print_payload(nrf_cli_t const * p_cli, size_t argc, char ** argv)
{
    if (nrf_cli_help_requested(p_cli))
    {
        nrf_cli_help_print(p_cli, NULL, 0);
        return;
    }

    radio_rx_stats_t rx_stats;

    memset(&rx_stats, 0, sizeof(rx_stats));

    radio_rx_stats_get(&rx_stats);

    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Received payload:\r\n");
    for (uint32_t i = 0; i < rx_stats.last_packet.len; i++)
    {
        nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Data: %d\r\n", rx_stats.last_packet.buf[i]);
    }
    nrf_cli_fprintf(p_cli, NRF_CLI_INFO, "Number of packets: %d\r\n", rx_stats.packet_cnt);
}


NRF_CLI_CREATE_STATIC_SUBCMD_SET(m_sub_data_rate)
{
    NRF_CLI_CMD(nrf_1Mbit, NULL, "1 Mbit/s Nordic proprietary radio mode", cmd_nrf_1mbit),
    NRF_CLI_CMD(nrf_2Mbit, NULL, "2 Mbit/s Nordic proprietary radio mode", cmd_nrf_2mbit),
#ifdef NRF52832_XXAA
    NRF_CLI_CMD(nrf_250Kbit, NULL, "250 kbit/s Nordic proprietary radio mode", cmd_nrf_250kbit),
#endif // NRF52832_XXAA
    NRF_CLI_CMD(ble_1Mbit, NULL, "1 Mbit/s Bluetooth Low Energy", cmd_ble_1mbit),
    NRF_CLI_CMD(ble_2Mbit, NULL, "2 Mbit/s Bluetooth Low Energy", cmd_ble_2mbit),

#if USE_MORE_RADIO_MODES
    NRF_CLI_CMD(ble_lr250Kbit,
                NULL,
                "Long range 125 kbit/s TX, 125 kbit/s and 500 kbit/s RX",
                cmd_ble_lr125kbit),
    NRF_CLI_CMD(ble_lr500Kbit,
                NULL,
                "Long range 500 kbit/s TX, 125 kbit/s and 500 kbit/s RX",
                cmd_ble_lr500kbit),
    NRF_CLI_CMD(ieee802154_250Kbit, NULL, "IEEE 802.15.4-2006 250 kbit/s", cmd_ble_ieee),
#endif // USE_MORE_RADIO_MODES

    NRF_CLI_SUBCMD_SET_END
};


NRF_CLI_CREATE_STATIC_SUBCMD_SET(m_sub_output_power)
{
#if USE_MORE_NRF52_RADIO_POWER_OPTIONS
    NRF_CLI_CMD(pos8dBm, NULL, "TX power: +8 dBm", cmd_pos8dbm),
    NRF_CLI_CMD(pos7dBm, NULL, "TX power: +7 dBm", cmd_pos7dbm),
    NRF_CLI_CMD(pos6dBm, NULL, "TX power: +6 dBm", cmd_pos6dbm),
    NRF_CLI_CMD(pos5dBm, NULL, "TX power: +5 dBm", cmd_pos5dbm),
    NRF_CLI_CMD(pos2dBm, NULL, "TX power: +2 dBm", cmd_pos2dbm),
#endif // USE_MORE_NRF52_RADIO_POWER_OPTIONS
    NRF_CLI_CMD(pos3dBm, NULL, "TX power: +3 dBm", cmd_pos3dbm),
    NRF_CLI_CMD(pos4dBm, NULL, "TX power: +4 dBm", cmd_pos4dbm),
    NRF_CLI_CMD(pos0dBm, NULL, "TX power: 0 dBm", cmd_pos0dbm),
    NRF_CLI_CMD(neg4dBm, NULL, "TX power: -4 dBm", cmd_neg4dbm),
    NRF_CLI_CMD(neg8dBm, NULL, "TX power: -8 dBm", cmd_neg8dbm),
    NRF_CLI_CMD(neg12dBm, NULL, "TX power: -12 dBm", cmd_neg12dbm),
    NRF_CLI_CMD(neg16dBm, NULL, "TX power: -16 dBm", cmd_neg16dbm),
    NRF_CLI_CMD(neg20dBm, NULL, "TX power: -20 dBm", cmd_neg20dbm),
    NRF_CLI_CMD(neg30dBm, NULL, "TX power: -30 dBm", cmd_neg30dbm),
    NRF_CLI_CMD(neg40dBm, NULL, "TX power: -40 dBm", cmd_neg40dbm),
    NRF_CLI_SUBCMD_SET_END
};


NRF_CLI_CREATE_STATIC_SUBCMD_SET(m_sub_transmit_pattern)
{
    NRF_CLI_CMD(pattern_random, NULL, "Set the transmission pattern to random.", cmd_pattern_random),
    NRF_CLI_CMD(pattern_11110000, NULL, "Set the transmission pattern to 11110000.", cmd_pattern_11110000),
    NRF_CLI_CMD(pattern_11001100, NULL, "Set the transmission pattern to 10101010.", cmd_pattern_11001100),
    NRF_CLI_SUBCMD_SET_END
};


NRF_CLI_CMD_REGISTER(start_channel,
                     NULL,
                     "Start the channel for the sweep or the channel for the constant carrier <channel>",
                     cmd_start_channel_set);
NRF_CLI_CMD_REGISTER(end_channel, NULL, "End the channel for the sweep <channel>", cmd_end_channel_set);
NRF_CLI_CMD_REGISTER(time_on_channel,
                     NULL,
                     "Time on each channel (between 1 ms and 99 ms) <time>",
                     cmd_time_set);
NRF_CLI_CMD_REGISTER(cancel, NULL, "Cancel the sweep or the carrier", cmd_cancel);
NRF_CLI_CMD_REGISTER(data_rate, &m_sub_data_rate, "Set data rate <sub_cmd>", cmd_data_rate_set);
NRF_CLI_CMD_REGISTER(start_tx_carrier, NULL, "Start the TX carrier", cmd_tx_carrier_start);
NRF_CLI_CMD_REGISTER(start_tx_modulated_carrier,
                     NULL,
                     "Start the modulated TX carrier [packet_num]",
                     cmd_tx_modulated_carrier_start);
NRF_CLI_CMD_REGISTER(output_power,
                     &m_sub_output_power,
                     "Output power set <sub_cmd>",
                     cmd_output_power_set);
NRF_CLI_CMD_REGISTER(transmit_pattern,
                     &m_sub_transmit_pattern,
                     "Set the transmission pattern",
                     cmd_transmit_pattern_set);
NRF_CLI_CMD_REGISTER(start_duty_cycle_modulated_tx,
                     NULL,
                     "Duty cycle in percent (two decimal digits, between 01 and 99) <duty_cycle>",
                     cmd_duty_cycle_set);
NRF_CLI_CMD_REGISTER(parameters_print, NULL, "Print current delay, channel and so on", cmd_print);
NRF_CLI_CMD_REGISTER(start_rx_sweep, NULL, "Start RX sweep", cmd_rx_sweep_start);
NRF_CLI_CMD_REGISTER(start_tx_sweep, NULL, "Start TX sweep", cmd_tx_sweep_start);
NRF_CLI_CMD_REGISTER(start_rx, NULL, "Start RX", cmd_rx_start);
NRF_CLI_CMD_REGISTER(toggle_dcdc_state, NULL, TOGGLE_DCDC_HELP, cmd_toggle_dc);
NRF_CLI_CMD_REGISTER(print_rx, NULL, "Print received payload", cmd_print_payload);
