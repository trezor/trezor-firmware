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

#ifdef USE_BLE

#include <trezor_rtl.h>
#include <trezor_bsp.h>

#include <io/ble.h>
#include <io/usb.h>
#include <rtl/cli.h>
#include <sys/systick.h>
#include <sys/systimer.h>

void ble_timer_cb(void* context) {
  ble_event_t e = {0};
  ble_command_t cmd = {0};

  bool event_received = ble_get_event(&e);

  if (event_received) {
    switch (e.type) {
      case BLE_PAIRING_REQUEST:
        cmd.cmd_type = BLE_ALLOW_PAIRING;
        ble_issue_command(&cmd);
      default:
        break;
    }
  }
}

static bool ensure_ble_init(cli_t* cli) {
  cli_trace(cli, "Initializing the BLE...");
  if (!ble_init()) {
    cli_error(cli, CLI_ERROR, "Cannot initialize BLE.");
    return false;
  }

  static systimer_t* timer = NULL;

  if (timer == NULL) {
    timer = systimer_create(ble_timer_cb, NULL);
    if (timer == NULL) {
      cli_error(cli, CLI_ERROR, "Cannot create timer.");
      return false;
    }
    systimer_set_periodic(timer, 10);
  }

  return true;
}

static void prodtest_ble_adv_start(cli_t* cli) {
  const char* name = cli_arg(cli, "name");

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  uint16_t name_len =
      strlen(name) > BLE_ADV_NAME_LEN ? BLE_ADV_NAME_LEN : strlen(name);

  ble_command_t cmd = {0};
  cmd.cmd_type = BLE_PAIRING_MODE;
  cmd.data_len = sizeof(cmd.data.adv_start);
  cmd.data.adv_start.static_mac = true;
  memcpy(cmd.data.adv_start.name, name, name_len);

  if (!ble_issue_command(&cmd)) {
    cli_error(cli, CLI_ERROR, "Could not start advertising.");
    return;
  }

  uint32_t timeout = ticks_timeout(1000);

  bool result = false;
  while (!ticks_expired(timeout)) {
    ble_state_t state = {0};
    ble_get_state(&state);

    if (state.pairing) {
      result = true;
      break;
    }
  }

  if (!result) {
    cli_error(cli, CLI_ERROR, "Could not start advertising.");
    return;
  }

  cli_trace(cli, "Advertising started.");
  cli_ok(cli, "");
}

static void prodtest_ble_adv_stop(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  ble_command_t cmd = {0};
  cmd.cmd_type = BLE_SWITCH_OFF;
  cmd.data_len = 0;

  if (!ble_issue_command(&cmd)) {
    cli_error(cli, CLI_ERROR, "Could not stop advertising.");
    return;
  }

  uint32_t timeout = ticks_timeout(1000);

  bool result = false;
  while (!ticks_expired(timeout)) {
    ble_state_t state = {0};
    ble_get_state(&state);

    if (!state.pairing && !state.connectable) {
      result = true;
      break;
    }
  }

  if (!result) {
    cli_error(cli, CLI_ERROR, "Could not stop advertising.");
    return;
  }

  cli_trace(cli, "Advertising stopped.");
  cli_ok(cli, "");
}

static void prodtest_ble_info(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  uint8_t mac[6] = {0};

  if (!ble_get_mac(mac, 6)) {
    cli_error(cli, CLI_ERROR, "Could not read MAC.");
    return;
  }

  cli_trace(cli, "MAC: %02x:%02x:%02x:%02x:%02x:%02x", mac[5], mac[4], mac[3],
            mac[2], mac[1], mac[0]);
  cli_ok(cli, "");
}

bool prodtest_ble_erase_bonds(cli_t* cli) {
  ble_command_t cmd = {0};
  cmd.cmd_type = BLE_ERASE_BONDS;

  ble_state_t state = {0};
  ble_issue_command(&cmd);

  uint32_t timeout = ticks_timeout(100);

  while (!ticks_expired(timeout)) {
    ble_get_state(&state);
    if (state.peer_count == 0 && state.state_known) {
      return true;
    }
  }

  return false;
}

static void prodtest_ble_erase_bonds_cmd(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_ble_init(cli)) {
    return;
  }

  ble_state_t state = {0};

  ble_get_state(&state);

  if (!state.state_known) {
    cli_error(cli, CLI_ERROR, "BLE state unknown.");
  }

  if (state.peer_count == 0) {
    cli_ok(cli, "No bonds to erase.");
    return;
  }

  if (!prodtest_ble_erase_bonds(cli)) {
    cli_error(cli, CLI_ERROR, "Could not erase bonds.");
  }

  cli_trace(cli, "Erased %d bonds.", state.peer_count);
  cli_ok(cli, "");
}

static void prodtest_ble_radio_test_cmd(cli_t* cli){

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  GPIO_InitTypeDef GPIO_InitStruct = {0};

  // UART3 settings
  // UART connected to NRF via unmeasurable wires, TX line for some reason do not work
  // RAD TX (PB10 - P0.09)
  // RAD RX (PA5  - P0.06)

  /* Enable clock for USART1 */
  __HAL_RCC_USART3_FORCE_RESET();
  __HAL_RCC_USART3_RELEASE_RESET();
  __HAL_RCC_USART3_CLK_ENABLE();

  /* Enable clock for GPIO port */
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  // RAD_RX PA5   USART3_RX AF7
  GPIO_InitStruct.Pin = GPIO_PIN_5;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF7_USART3;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  // RAD TX PB10  USART3_TX AF7
  GPIO_InitStruct.Pin = GPIO_PIN_10;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF7_USART3;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);


  // UART3 settings
  // UART connected to NRF via QI I2C line reconfigured to UART
  // This line requires physical connection between TP3-TP37 and TP4-TP36
  // RAD TX (PF0 - P0.16)
  // RAD RX (PF1 - P0.15)

  /* Enable clock for USART1 */
  __HAL_RCC_USART6_FORCE_RESET();
  __HAL_RCC_USART6_RELEASE_RESET();
  __HAL_RCC_USART6_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();

  // USART6_RX AF7
  GPIO_InitStruct.Pin = GPIO_PIN_1;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF7_USART6;
  HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);

  // USART6 TX AF7
  GPIO_InitStruct.Pin = GPIO_PIN_0;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF7_USART6;
  HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);


  // NRF Reset pin
  GPIO_InitStruct.Pin = GPIO_PIN_0;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOG, &GPIO_InitStruct);

  UART_HandleTypeDef huart = {0};

  /* Configure the UART peripheral */
  huart.Instance = USART6; // USART3
  huart.Init.BaudRate = 115200;
  huart.Init.WordLength = UART_WORDLENGTH_8B;
  huart.Init.StopBits = UART_STOPBITS_1;
  huart.Init.Parity = UART_PARITY_NONE;
  huart.Init.Mode = UART_MODE_TX_RX;
  huart.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart.Init.OverSampling = UART_OVERSAMPLING_16;
  huart.Init.ClockPrescaler = UART_PRESCALER_DIV1;
  huart.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;

  uint8_t cmd_line_byte;
  uint8_t nrf_byte;

  // Initialize UART
  if (HAL_UART_Init(&huart) != HAL_OK)
  {
    cli_error(cli, CLI_ERROR, "Could not initialize UART.");
    return;
  }

  // Reset NRF
  HAL_GPIO_WritePin(GPIOG, GPIO_PIN_0, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(GPIOG, GPIO_PIN_0, GPIO_PIN_SET);

  while(true){

    if(cli_aborted(cli)){
      cli_trace(cli, "Aborted.");
      break;
    }

    // Read byte from the command line and pass it to NRF UART;
    if( usb_vcp_read(0, &cmd_line_byte, 1) > 0){
      HAL_UART_Transmit(&huart, &cmd_line_byte, 1, 100);
    }

    // Read byte from the NRF UART and pass it to command line;
    if(HAL_UART_Receive(&huart, &nrf_byte, 1, 10) == HAL_OK){
      cli->write(cli, (const char *) &nrf_byte, 1);
    }

  }

  cli_ok(cli, "");

}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "ble-adv-start",
  .func = prodtest_ble_adv_start,
  .info = "Start BLE advertising",
  .args = "<name>"
);

PRODTEST_CLI_CMD(
  .name = "ble-adv-stop",
  .func = prodtest_ble_adv_stop,
  .info = "Stop BLE advertising",
  .args = "<name>"
);

PRODTEST_CLI_CMD(
  .name = "ble-info",
  .func = prodtest_ble_info,
  .info = "Get BLE information",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "ble-erase-bonds",
  .func = prodtest_ble_erase_bonds_cmd,
  .info = "Erase all BLE bonds",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "ble-radio-test",
  .func = prodtest_ble_radio_test_cmd,
  .info = "Connect to Radio test CLI",
  .args = ""
);

#endif
