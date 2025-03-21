.. _radio_test:

Radio test (short-range)
########################

.. contents::
   :local:
   :depth: 2

The Radio test sample demonstrates how to configure the 2.4 GHz short-range radio (Bluetooth® LE, IEEE 802.15.4 and proprietary) in a specific mode and then test its performance.
The sample provides a set of predefined commands that allow you to configure the radio in three modes:

* Constant RX or TX carrier
* Modulated TX carrier
* RX or TX sweep

Requirements
************

The sample supports the following development kits:

.. table-from-sample-yaml::

You can use any one of the development kits listed above.

.. note::
   On nRF5340 DK and nRF7002 DK, the sample is designed to run on the network core and requires the :ref:`nrf5340_remote_shell` running on the application core.
   This sample uses the :ref:`shell_ipc_readme` library to forward shell data through the physical UART interface of the application core.

The sample also requires one of the following testing devices:

  * Another development kit with the same sample.
    See :ref:`radio_test_testing_board`.
  * Another development kit connected to a PC with the `RSSI Viewer app`_ (available in the `nRF Connect for Desktop`_).
    See :ref:`radio_test_testing_rssi`.

.. note::
   You can perform the radio test also using a spectrum analyzer.
   This method of testing is not covered by this documentation.

nRF21540 front-end module
=========================

.. include:: /includes/sample_dtm_radio_test_fem.txt

You can configure the nRF21540 front-end module (FEM) transmitted power control, antenna output and activation delay using the main shell commands of the :ref:`radio_test_ui`.

Skyworks front-end module
=========================

.. include:: /includes/sample_dtm_radio_test_skyworks.txt

You can configure the Skyworks front-end module (FEM) antenna output and activation delay using the main shell commands of the :ref:`radio_test_ui`.

Overview
********

To run the tests, connect to the development kit through the serial port and send shell commands.
Zephyr's :ref:`zephyr:shell_api` module is used to handle the commands.
At any time during the tests, you can dynamically set the radio parameters, such as output power, bit rate, and channel.
In sweep mode, you can set the time for which the radio scans each channel from one millisecond to 99 milliseconds, in steps of one millisecond.
The sample also allows you to send a data pattern to another development kit.

The sample first enables the high frequency crystal oscillator and configures the shell.
You can then start running commands to set up and control the radio.
See :ref:`radio_test_ui` for a list of available commands.

.. note::
   For the IEEE 802.15.4 mode, the start channel and the end channel must be within the channel range of 11 to 26.
   Use the ``start_channel`` and ``end_channel`` commands to control this setting.


.. _radio_test_ui:

User interface
**************
.. list-table:: Main shell commands (in alphabetical order)
   :header-rows: 1

   * - Command
     - Argument
     - Description
   * - cancel
     -
     - Cancel the sweep or the carrier.
   * - data_rate
     - <sub_cmd>
     - Set the data rate.
   * - end_channel
     - <channel>
     - End channel for the sweep (in MHz, as difference from 2400 MHz).
   * - fem
     - <sub_cmd>
     - Set front-end module (FEM) parameters.
   * - output_power
     - <sub_cmd>
     - Output power set.
       If a front-end module is attached and the :ref:`CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC <CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC>` Kconfig option is enabled, it has the same effect as the ``total_output_power`` command.
   * - parameters_print
     -
     - Print current delay, channel, and other parameters.
   * - print_rx
     -
     - Print the received RX payload.
   * - start_channel
     - <channel>
     - Start channel for the sweep or the channel for the constant carrier (in MHz, as difference from 2400 MHz).
   * - start_duty_cycle_modulated_tx
     - <duty_cycle>
     - Duty cycle in percent (two decimal digits, between 01 and 90).
   * - start_rx
     - <packet_num>
     - Start RX (continuous RX mode is used if no argument is provided).
   * - start_rx_sweep
     -
     - Start the RX sweep.
   * - start_tx_carrier
     -
     - Start the TX carrier.
   * - start_tx_modulated_carrier
     - <packet_num>
     - Start the modulated TX carrier (continuous TX mode is used if no argument is provided).
   * - start_tx_sweep
     -
     - Start the TX sweep.
   * - time_on_channel
     - <time>
     - Time on each channel in ms (between 1 and 99).
   * - toggle_dcdc_state
     - <state>
     - Toggle DC/DC converter state.
   * - transmit_pattern
     - <sub_cmd>
     - Set transmission pattern.
   * - total_output_power
     - <tx output power>
     - Set total output power in dBm.
       This value includes SoC output power and front-end module gain.

TX output power
===============

This sample has a few commands that you can use to test the device output power.
The behavior of the commands vary depending on the hardware configuration and Kconfig options as follows:

* Radio Test without front-end module support:

  * The ``output_power`` command sets the SoC output command with a subcommand set.
    The output power is set directly in the radio peripheral.

* Radio Test with front-end module support in default configuration (the :ref:`CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC <CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC>` Kconfig option is enabled):

  * The ``output_power`` command sets the total output power, including front-end module gain.
  * The ``total_output_power`` command sets the total output power, including front-end module gain with a value in dBm unit provided by user.
  * For these commands, the radio peripheral and FEM transmit power control is calculated and set automatically to meet your requirements.
  * If an exact output power value cannot be set, a lower value is used.

* Radio Test with front-end module support and manual TX output power control (the :ref:`CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC <CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC>` Kconfig option is disabled):

  * The ``output_power`` command sets the SoC output command with a subcommands set.
  * The ``fem`` command with the ``tx_power_control`` subcommand sets the front-end module transmit power control to a value for given specific front-end module.
  * You can use this configuration to perform tests on your hardware design.

Configuration
*************

|config|

Configuration options
=====================

Check and configure the following Kconfig options:

.. _CONFIG_RADIO_TEST_USB:

CONFIG_RADIO_TEST_USB
   Selects USB instead of UART as the Radio Test shell transport.
   For nRF5340 the USB from application core is used as the communication interface.

.. _CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC:

CONFIG_RADIO_TEST_POWER_CONTROL_AUTOMATIC
   Sets the SoC output power and front-end module gain to achieve the requested TX output power.
   If the exact value cannot be achieved, power is set to closest value that does not exceed the limits.
   If this option is disabled, set the SoC output power and FEM gain with separate commands.

Building and running
********************

.. |sample path| replace:: :file:`samples/peripheral/radio_test`

.. include:: /includes/build_and_run.txt

.. include:: /includes/nRF54H20_erase_UICR.txt

.. note::
   |54H_engb_2_8|

.. note::
   On the nRF5340 or nRF7002 development kit, the Radio Test sample requires the :ref:`nrf5340_remote_shell` sample on the application core.
   The Remote IPC shell sample is built and programmed automatically by default.
   If you want to program your custom solution for the application core, unset the :kconfig:option:`CONFIG_NCS_SAMPLE_REMOTE_SHELL_CHILD_IMAGE` Kconfig option.

Remote USB CDC ACM Shell variant
================================

This sample can run the remote IPC Service Shell through the USB on the nRF5340 DK application core.
For example, when building on the command line, use the following command:

.. code-block:: console

   west build samples/peripheral/radio_test -b nrf5340dk/nrf5340/cpunet -- -DFILE_SUFFIX=usb

You can also build this sample with the remote IPC Service Shell and support for the front-end module.
You can use the following command:

.. code-block:: console

   west build samples/peripheral/radio_test -b nrf5340dk/nrf5340/cpunet -- -DSHIELD=nrf21540ek -DFILE_SUFFIX=usb

.. include:: /includes/nRF54H20_erase_UICR.txt

.. note::
   You can also build the sample with the remote IPC Service Shell for the |nRF7002DKnoref| using the ``nrf7002dk/nrf5340/cpunet`` board target in the commands.

.. _radio_test_testing:

Testing
=======

After programming the sample to your development kit, complete the following steps to test it in one of the following two ways:

.. note::
   For the |nRF5340DKnoref| or |nRF7002DKnoref|, see :ref:`logging_cpunet` for information about the COM terminals on which the logging output is available.

.. _radio_test_testing_board:

Testing with another development kit
------------------------------------

Complete the following steps:

1. Connect both development kits to the computer using a USB cable.
   The kits are assigned a COM port (Windows) or ttyACM device (Linux), which is visible in the Device Manager.
#. |connect_terminal_both_ANSI|
#. Run the following commands on one of the kits:

   a. Set the data rate with the ``data_rate`` command to ``ble_2Mbit``.
   #. Set the transmission pattern with the ``transmit_pattern`` command to ``pattern_11110000``.
   #. Set the radio channel with the ``start_channel`` command to 40.

#. Repeat all steps for the second kit.
#. On both kits, run the ``parameters_print`` command to confirm that the radio configuration is the same on both kits.
#. Set one kit in the Modulated TX Carrier mode using the ``start_tx_modulated_carrier`` command.
#. Set the other kit in the RX Carrier mode using the ``start_rx`` command.
#. Print the received data with the ``print_rx`` command and confirm that they match the transmission pattern (0xF0).

.. _radio_test_testing_rssi:

Testing with the RSSI Viewer app
--------------------------------

Complete the following steps:

1. Connect the kit to the computer using a USB cable.
   The kit is assigned a COM port (Windows) or ttyACM device (Linux), which is visible in the Device Manager.
#. |connect_terminal_ANSI|
#. Set the start channel with the ``start_channel`` command to 20.
#. Set the end channel with the ``end_channel`` command to 60.
#. Set the time on channel with the ``time_on_channel`` command to 50 ms.
#. Set the kit in the TX sweep mode using the ``start_tx_sweep`` command.
#. Start the `RSSI Viewer app`_ and select the kit to communicate with.
#. On the application chart, observe the TX sweep in the form of a wave that starts at 2420 MHz frequency and ends with 2480 MHz.

Dependencies
************

This sample uses the following |NCS| libraries:

  * :ref:`shell_ipc_readme`
  * :ref:`fem_al_lib`

This sample has the following nrfx dependencies:

  * :file:`nrfx/drivers/include/nrfx_timer.h`
  * :file:`nrfx/hal/nrf_power.h`
  * :file:`nrfx/hal/nrf_radio.h`

The sample also has the following nrfxlib dependency:

  * :ref:`nrfxlib:mpsl_fem`

In addition, it uses the following Zephyr libraries:

* :ref:`zephyr:device_model_api`:

   * :file:`drivers/clock_control.h`

* :ref:`zephyr:kernel_api`:

  * :file:`include/init.h`

* :ref:`zephyr:shell_api`:

  * :file:`include/shell/shell.h`
