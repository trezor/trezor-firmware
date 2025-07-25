.. _direct_test_mode:

Bluetooth: Direct Test Mode
###########################

.. contents::
   :local:
   :depth: 2

This sample enables the Direct Test Mode functions described in `Bluetooth® Core Specification <Bluetooth Core Specification_>`_ (Vol. 6, Part F).

Requirements
************

The sample supports the following development kits:

.. table-from-sample-yaml::

Additionally, the sample requires one of the following testing devices:

* Dedicated test equipment, like an Anritsu MT8852 tester.
  See :ref:`direct_test_mode_testing_anritsu`.
* Another development kit with the same sample.
  See :ref:`direct_test_mode_testing_board`.
* A computer with the `Direct Test Mode app`_ available in the `nRF Connect for Desktop`_.
  See :ref:`direct_test_mode_testing_app`.

Overview
********

The sample uses Direct Test Mode (DTM) to test the operation of the following features of the radio:

* Transmission power and receiver sensitivity
* Frequency offset and drift
* Modulation characteristics
* Packet error rate
* Intermodulation performance

Test procedures are defined in the document `Bluetooth Low Energy RF PHY Test Specification <Bluetooth Low Energy RF PHY Test Specification_>`_: Document number RF-PHY.TS.p15

You can carry out conformance tests using dedicated test equipment, such as the Anritsu MT8852 or similar, with an nRF5 running the DTM sample set as device under test (DUT).

Implementation
==============

The DTM sample includes two parts:

* The Direct Test Mode library that manages the nRF radio and controls the standard DTM procedures.
* A sample that provides an external interface to the library.

You can find the source code of both parts in :file:`samples/bluetooth/direct_test_mode/src`.
If you use the experimental HCI interface on the |nRF5340DKnoref|, you can find additional source code in :file:`samples/bluetooth/direct_test_mode/remote_hci/src` and :file:`samples/bluetooth/direct_test_mode/rpc`.

This sample contains a driver for a 2-wire UART interface and an experimental HCI UART interface.
Unless otherwise stated, all following commands and references describe the 2-wire interface.
The 2-wire driver maps two-octet commands and events to the DTM library, as specified by the Bluetooth Low Energy DTM specification.
The HCI driver accepts HCI commands in H4 format and implements a minimal set of HCI commands usually sufficient to run DTM testing.

.. figure:: /images/bt_dtm_dut.svg
   :alt: nRF5 with DTM as a DUT

The implementation is self-contained and requires no Bluetooth Low Energy protocol stack for its operation.
The MPU is initialized in the standard way.
The DTM library function :c:func:`dtm_init` configures all interrupts, timers, and the radio.

This sample may be extended with other interface implementations, such as an HCI interface, USB, or another interface required by the Upper Tester.
The extension should be done by adding an appropriate interface implementation in the :file:`transport` directory.
The transports must conform to the interface specified in the :file:`transport/dtm_transport.h` file.

The interface to the Lower Tester uses the antenna connector of the chosen development kit.
While in principle an aerial connection might be used, conformance tests cover the reading of the transmission power delivered by the DUT.
For this reason, a coaxial connection between the DUT and the Lower Tester is employed for all conformance testing.

DTM module interface
====================

The DTM module interface can be divided into the following three parts:

* The :c:func:`dtm_init` initialization function
* Setup functions:

  * :c:func:`dtm_setup_reset`
  * :c:func:`dtm_setup_set_phy`
  * :c:func:`dtm_setup_set_modulation`
  * :c:func:`dtm_setup_read_features`
  * :c:func:`dtm_setup_read_max_supported_value`
  * :c:func:`dtm_setup_set_cte_mode`
  * :c:func:`dtm_setup_set_cte_slot`
  * :c:func:`dtm_setup_set_antenna_params`
  * :c:func:`dtm_setup_set_transmit_power`

* Test functions:

  * :c:func:`dtm_test_receive`
  * :c:func:`dtm_test_transmit`
  * :c:func:`dtm_test_end`

The setup functions implement the DTM setup required by the Bluetooth Low Energy standard.
The test functions implement the tests defined by the Bluetooth Low Energy standard.

The sample is required to perform the following tasks:

  *  To parse the relevant encoding format - UART or HCI - for the command, and to use the DTM module interface accordingly.
  *  To interpret the return values of interface functions used in the DTM module, and to respond to the tester in the correct format.

.. figure:: /images/bt_dtm_engine.svg
   :alt: State machine overview of the DTM

Supported PHYs
==============

The DTM sample supports all four PHYs specified in DTM, but not all devices support all the PHYs.

.. list-table:: Supported PHYs
   :header-rows: 1

   * - PHY
     - nRF5340
   * - LE 1M
     - Yes
   * - LE 2M
     - Yes
   * - LE Coded S=8
     - Yes
   * - LE Coded S=2
     - Yes

TX output power
===============

This sample has several ways to set the device output power.
The behavior of the commands vary depending on the hardware configuration and Kconfig options as follows:

* DTM without front-end module support:

   * The official ``0x09`` DTM command sets the SoC TX output power closest to the requested one when the exact power level is not supported.
   * The ``SET_TX_POWER`` vendor-specific command sets the SoC TX output power.
     You must use only the TX power values supported by your SoC.
     See the actual values in the SoC Product Specification.

* DTM with front-end module support:

   * When the :ref:`CONFIG_DTM_POWER_CONTROL_AUTOMATIC <CONFIG_DTM_POWER_CONTROL_AUTOMATIC>` Kconfig option is enabled (default), the official ``0x09`` DTM command sets the final output power to the desired, or the closest available value by configuring the SoC output power and the front-end module gain automatically.

     .. note::
        The returned output power using this command is valid only for channel 0.
        If you perform the test on a different channel than the real output power measured by your tester device, it can be equal or less than the returned one.
        This is because the DTM specification has a limitation when it assumes that output power is the same for all channels.
        That is why the chosen output power might not be available for the given channel.

   * When the :ref:`CONFIG_DTM_POWER_CONTROL_AUTOMATIC <CONFIG_DTM_POWER_CONTROL_AUTOMATIC>` Kconfig option is disabled, the official ``0x09`` DTM command sets only the SoC output power.
     These commands behave in the same way for the DTM without front-end module support.
     Additionally, you can use following vendor-specific commands:

      * The ``SET_TX_POWER`` command sets the SoC TX output power.
      * The ``FEM_TX_POWER_CONTROL_SET`` command sets the front-end module gain.

Bluetooth Direction Finding support
===================================

The DTM sample supports all Bluetooth Direction Finding modes specified in DTM.

.. list-table:: Supported Bluetooth Direction Finding modes
   :header-rows: 1

   * - Direction Finding mode
     - nRF5340
   * - AoD 1 us slot
     - Yes
   * - AoD 2 us slot
     - Yes
   * - AoA
     - Yes

The following antenna switching patterns are possible:

* 1, 2, 3, ..., N
* 1, 2, 3, ..., N, N - 1, N - 2, ..., 1

The application supports a maximum of 19 antennas in the direction finding mode.
The radio can control up to eight GPIO pins for the purpose of controlling the external antenna switches used in direction finding.

Antenna matrix configuration
----------------------------

To use this sample to test the Bluetooth Direction Finding feature, additional configuration of GPIOs is required to control the antenna array.
An example of such configuration is provided in a devicetree overlay file :file:`nrf5340dk_nrf5340_cpunet.overlay`.

The overlay file provides the information about of the GPIOs to be used by the Radio peripheral to switch between antenna patches during the Constant Tone Extension (CTE) reception or transmission.
At least one GPIO must be provided to enable antenna switching.

The GPIOs are used by the radio peripheral in the order provided by the ``dfegpio#-gpios`` properties.
The order is important because it has an impact to the mapping of the antenna switching patterns to GPIOs (see `Antenna patterns`_).

To test Direction Finding, provide the following data related to antenna matrix design:

* GPIO pins to ``dfegpio#-gpios`` properties in the :file:`nrf5340dk_nrf5340_cpunet.overlay` file.
* The default antenna to be used to receive the PDU ``dfe-pdu-antenna`` property in the :file:`nrf5340dk_nrf5340_cpunet.overlay` file.

.. note::
   The PDU antenna is also used for the reference period transmission and reception.

Antenna patterns
----------------

The antenna switching pattern is a binary number where each bit is applied to a particular antenna GPIO pin.
For example, the pattern ``0x3`` means that antenna GPIOs at index ``0,1`` is set, while the next ones are left unset.

This also means that, for example, when using four GPIOs, the pattern count cannot be greater than 16 and the maximum allowed value is 15.

If the number of switch-sample periods is greater than the number of stored switching patterns, the radio loops back to the first pattern.

The following table presents the patterns that you can use to switch antennas on the Nordic-designed antenna matrix:

+--------+--------------+
|Antenna | PATTERN[3:0] |
+========+==============+
| ANT_12 |  0 (0b0000)  |
+--------+--------------+
| ANT_10 |  1 (0b0001)  |
+--------+--------------+
| ANT_11 |  2 (0b0010)  |
+--------+--------------+
| RFU    |  3 (0b0011)  |
+--------+--------------+
| ANT_3  |  4 (0b0100)  |
+--------+--------------+
| ANT_1  |  5 (0b0101)  |
+--------+--------------+
| ANT_2  |  6 (0b0110)  |
+--------+--------------+
| RFU    |  7 (0b0111)  |
+--------+--------------+
| ANT_6  |  8 (0b1000)  |
+--------+--------------+
| ANT_4  |  9 (0b1001)  |
+--------+--------------+
| ANT_5  | 10 (0b1010)  |
+--------+--------------+
| RFU    | 11 (0b1011)  |
+--------+--------------+
| ANT_9  | 12 (0b1100)  |
+--------+--------------+
| ANT_7  | 13 (0b1101)  |
+--------+--------------+
| ANT_8  | 14 (0b1110)  |
+--------+--------------+
| RFU    | 15 (0b1111)  |
+--------+--------------+

nRF21540 front-end module
=========================

.. include:: /includes/sample_dtm_radio_test_fem.txt

You can configure the transmitted power gain, antenna output and activation delay in nRF21540 using vendor-specific commands, see `Vendor-specific packet payload`_.

Skyworks front-end module
=========================

.. include:: /includes/sample_dtm_radio_test_skyworks.txt

You can configure the antenna output and activation delay for the Skyworks front-end module (FEM) using vendor-specific commands, see `Vendor-specific packet payload`_.

Vendor-specific packet payload
==============================

The Bluetooth Low Energy 2-wire UART DTM interface standard reserves the Packet Type, also called payload parameter, with binary value ``11`` for a Vendor Specific packet payload.

The DTM command is interpreted as vendor-specific when both of the following conditions are met:

* Its CMD field is set to Transmitter Test, binary ``10``.
* Its PKT field is set to vendor-specific, binary ``11``.

Vendor-specific commands can be divided into different categories as follows:

* If the **Length** field is set to ``0`` (symbol ``CARRIER_TEST``), an unmodulated carrier is turned on at the channel indicated by the **Frequency** field.
  It remains turned on until a ``TEST_END`` or ``RESET`` command is issued.
* If the **Length** field is set to ``1`` (symbol ``CARRIER_TEST_STUDIO``), the field value is used by the nRFgo Studio to indicate that an unmodulated carrier is turned on at the channel.
  It remains turned on until a ``TEST_END`` or ``RESET`` command is issued.
* If the **Length** field is set ``2`` (symbol ``SET_TX_POWER``), the **Frequency** field sets the TX power in dBm.
  The valid TX power values are specified in the product specification ranging from -40 to +4, where ``0`` dBm is the reset value.
  Only the six least significant bits will fit in the **Length** field.
  The two most significant bits are calculated by the DTM module.
  This is possible because the six least significant bits of all valid TX power values are unique.
  The TX power can be modified only when no Transmitter Test or Receiver Test is running.
* If the **Length** field is set to ``3`` (symbol ``FEM_ANTENNA_SELECT``), the **Frequency** field sets the front-end module (FEM) antenna output.
  The valid values are:

     * ``0`` - ANT1 enabled, ANT2 disabled
     * ``1`` - ANT1 disabled, ANT2 enabled

* If the **Length** field is set to ``4`` (symbol ``FEM_TX_POWER_CONTROL_SET``), the **Frequency** field sets the front-end module (FEM) TX power control value and is specific to the FEM type in use.
  The valid gain values are specified in your product-specific front-end module (FEM).
  For example, in the nRF21540 front-end module with GPIO interface, the tx power control range is 0 (POUTA) to 1 (POUTB).
  For example, in the nRF21540 front-end module with GPIO/SPI, the tx power control range is 0 - 31 and is the value of TX_GAIN field of CONFREG0 register.
* If the **Length** field is set to ``5`` (symbol ``FEM_ACTIVE_DELAY_SET``), the **Frequency** field sets the front-end module (FEM) activation delay in microseconds relative to the radio start.
  By default, this value is set to ``radio ramp-up time - front-end module (FEM) TX/RX settling time``.
* If the **Length** field is set to ``6`` (symbol ``FEM_DEFAULT_PARAMS_SET``) and the **Frequency** field to any value, the front-end module parameters, such as ``antenna output``, ``gain``, and ``delay``, are set to their default values.
* All other values of **Frequency** and **Length** field are reserved.

.. note::
   Front-end module configuration parameters, such as ``antenna output``, ``gain``, and ``active delay``, are not set to their default values after the DTM reset command.
   Testers, for example Anritsu MT8852, issue a reset command at the beginning of every test.
   Therefore, you cannot run automated test scripts for front-end modules with other than the default parameters.

   If you have changed the default parameters of the front-end module, you can restore them.
   You can either send the ``FEM_DEFAULT_PARAMS_SET`` command or power cycle the front-end module.

.. note::
   When you build the DTM sample with support for front-end modules and the :ref:`CONFIG_DTM_POWER_CONTROL_AUTOMATIC <CONFIG_DTM_POWER_CONTROL_AUTOMATIC>` Kconfig option is enabled, the following vendor-specific command are not available:

   * ``SET_TX_POWER``
   * ``FEM_TX_POWER_CONTROL_SET``

   You can disable the :ref:`CONFIG_DTM_POWER_CONTROL_AUTOMATIC <CONFIG_DTM_POWER_CONTROL_AUTOMATIC>` Kconfig option if you want to set the SoC output power and the front-end module gain by separate commands.
   The official DTM command ``0x09`` for setting power level takes into account the SoC output power and the front-end module gain to set the total requested output power.

The DTM-to-Serial adaptation layer
==================================

The :file:`dtm_uart_twowire.c` file is an implementation of the UART interface specified in the `Bluetooth Core Specification`_, Volume 6, Part F, Chapter 3.

The :file:`dtm_hci.c` and :file:`hci_uart.c` files are an implementation of the HCI UART interface specified in the `Bluetooth Core Specification`_, Volume 4, Part A (the flow control can be configured by an overlay file).

The default selection of UART pins is defined in :file:`zephyr/boards/arm/board_name/board_name.dts`.
You can change the defaults using the symbols ``tx-pin`` and ``rx-pin`` in the DTS overlay file of the child image at the project level.
The configuration files for the :ref:`nrf5340_remote_shell` subimage are located in the :file:`child_image/remote_shell` or :file:`sysbuild/remote_shell` directory.
The HCI interface allows for a custom ``remote_hci`` image to be used with |nRF5340DKnoref|.

.. note::
   On the nRF5340 development kit, the physical UART interface of the application core is used for communication with the tester device.
   This sample uses the :ref:`uart_ipc` for sending responses and receiving commands through the UART interface of the application core.

Debugging
*********

In this sample, the UART console is used to exchange commands and events defined in the DTM specification.
Debug messages are not displayed in the UART console.
Instead, they are printed by the RTT logger.

If you want to view the debug messages, follow the procedure in :ref:`testing_rtt_connect`.
For more information about debugging in the |NCS|, see :ref:`debugging`.

Configuration
*************
|config|

Configuration options
=====================

The following configuration parameters are associated with this sample:

.. _CONFIG_DTM_POWER_CONTROL_AUTOMATIC:

CONFIG_DTM_POWER_CONTROL_AUTOMATIC - Automatic power control
   Sets the SoC output power and the front-end module gain to achieve the TX output power requested by the user.
   If the exact value cannot be achieved, power is set to the closest possible value.
   If this option is disabled, you can set the SoC output power and the front-end module gain with the separate vendor-specific commands.

Building and running
********************

.. |sample path| replace:: :file:`samples/bluetooth/direct_test_mode`

.. include:: /includes/build_and_run.txt

.. include:: /includes/nRF54H20_erase_UICR.txt

.. note::
   On the nRF5340 development kit, this sample requires the :ref:`nrf5340_remote_shell` sample on the application core.
   The Remote IPC shell sample is built and programmed automatically by default.

Disabling Direction Finding feature
===================================

To build the sample without support for the Direction Finding feature, use the following command for the correct *board_target*:

.. parsed-literal::
   :class: highlight

   west build samples/bluetooth/direct_test_mode -b *board_target* -- -DSB_CONFIG_DTM_NO_DFE=y

Experimental HCI interface
==========================

To build the sample with an HCI interface, use the following command for the correct *board_target*:

.. parsed-literal::
   :class: highlight

   west build samples/bluetooth/direct_test_mode -b *board_target* -- -DFILE_SUFFIX=hci

On the |nRF5340DKnoref|, you can build the sample with HCI interface with the ``remote_hci`` image using the same command.

USB CDC ACM transport variant
=============================

On the nRF5340 development kit, you can build this sample configured to use the USB interface as a communication interface with the tester.
Use the following command:

.. code-block:: console

   west build samples/bluetooth/direct_test_mode -b nrf5340dk/nrf5340/cpunet -- -DFILE_SUFFIX=usb

You can also build this sample with support for the front-end module.
Use the following command:

.. code-block:: console

   west build samples/bluetooth/direct_test_mode -b nrf5340dk/nrf5340/cpunet -- -DSHIELD=nrf21540ek -DFILE_SUFFIX=usb

.. _dtm_testing:

Testing
=======

After programming the sample to your development kit, you can test it in three ways, as described in the following chapters.

.. note::
   For the |nRF5340DKnoref|, see :ref:`logging_cpunet` for information about the COM terminals on which the logging output is available.

.. note::
   |54H_engb_2_8|

.. _direct_test_mode_testing_anritsu:

Testing with a certified tester
-------------------------------

Conformance testing is performed using a certified tester.
The setup depends on the tester used, and details about the test operation must be found in the tester documentation.

The Application note `nAN34`_ describes two alternatives for setting up a production test with DTM using one of our old devices.

.. _direct_test_mode_testing_board:

Testing with another development kit
------------------------------------

1. Connect both development kits to the computer using a USB cable.
   The computer assigns to the development kit a COM port on Windows or a ttyACM device on Linux, which is visible in the Device Manager.
#. Connect to both kits with a terminal emulator.
   See `Direct Test Mode terminal connection`_ for the required settings.
#. Start ``TRANSMITTER_TEST`` by sending the ``0x80 0x96`` DTM command to one of the connected development kits.
   This command will trigger TX activity on the 2402 MHz frequency (1st channel) with ``10101010`` packet pattern and 37-byte packet length.
#. Observe that you received the ``TEST_STATUS_EVENT`` packet in response with the SUCCESS status field: ``0x00 0x00``.
#. Start ``RECEIVER_TEST`` by sending the ``0x40 0x96`` DTM command to the second development kit.
   Command parameters are identical to the ones used for the ``TRANSMITTER_TEST`` command.
#. Observe that you received the ``TEST_STATUS_EVENT`` packet in response with the SUCCESS status field: ``0x00 0x00``.
#. Finish RX testing using the ``TEST_END DTM`` command by sending the ``0xC0 0x00`` packet.
#. Observe that you received the ``PACKET_REPORTING_EVENT`` packet in response.
   For example, the ``0xD6 0xAC`` message indicates that 22188 Radio packets have been received.
#. Experiment with other combinations of commands and their parameters.

.. _direct_test_mode_testing_app:

Testing with Direct Test Mode app
---------------------------------

1. |connect_kit|
#. Connect the kit with a terminal emulator that supports encoding and decoding in the HEX format.
   See `Direct Test Mode terminal connection`_ for the required settings.
#. Start the ``TRANSMITTER_TEST`` by sending the ``0x80 0x96`` DTM command to the connected development kit.
   This command triggers TX activity on 2402 MHz frequency (1st channel) with ``10101010`` packet pattern and 37-byte packet length.
#. Observe that you received the ``TEST_STATUS_EVENT`` packet in response with the SUCCESS status field: ``0x00 0x00``.
#. Start the `Direct Test Mode app`_ in `nRF Connect for Desktop`_ and select the development kit to communicate with.
#. Set the Receiver mode and 37th channel in the test configuration menu.
#. Start the test.
#. On the application chart, observe that the number of RX packets is increasing for the 2402 MHz channel.
#. Stop the test.
#. Swap roles.
   Set the application to the RX mode and the connected development kit to the TX mode.

Direct Test Mode terminal connection
------------------------------------

To send commands to and receive responses from the development kit that runs the Direct Test Mode sample, connect to it with RealTerm in Windows or Minicom in Linux.

The Bluetooth Low Energy DTM UART interface standard specifies the following configuration:

* Eight data bits
* No parity
* One stop bit
* No hardware flow control
* A selection of bit rates from 9600 to 1000000, one of which must be supported by the DUT.
  It might be possible to run other bit rates by experimenting with parameters.

.. note::
   The default bit rate of the DTM UART driver is 19200 bps, which is supported by most certified testers.

When using a 2-wire interface, you must send all commands as two-byte HEX numbers.
The responses must have the same format.

Connect with RealTerm (Windows)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The RealTerm terminal program offers a graphical interface for setting up your connection.

.. figure:: /images/realterm.png
   :alt: RealTerm start window

   The RealTerm start window

To test DTM with RealTerm, complete the following steps:

1. On the :guilabel:`Display` tab, set **Display As** to **Hex[space]**.

   .. figure:: /images/realterm_hex_display.png
      :alt: Set the RealTerm display format

#. Open the :guilabel:`Port` tab and configure the serial port parameters:

   a. Set the **Baud** to ``19200`` **(1)**.
   #. Select your J-Link serial port from the **Port** list **(2)**.
   #. Set the port status to ``Open`` **(3)**.

   .. figure:: /images/real_term_serial_port.png
      :alt: RealTerm serial port settings

#. Open the :guilabel:`Send` tab:

   a. Write the command as a hexadecimal number in the field **(1)**.
      For example, write ``0x00 0x00`` to send a **Reset** command.
   #. Click the :guilabel:`Send Numbers` button **(2)** to send the command.
   #. Observe the response in the DTM in area **(3)**.
      The response is encoded as hexadecimal numbers.

   .. figure:: /images/realterm_commands.png
      :alt: RealTerm commands sending

Connect with Minicom (Linux)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Minicom is a serial communication program that connects to the DTM device.

On the Linux operating system, install a Minicom terminal.
On Ubuntu, run:

.. code-block:: console

   sudo apt-get install minicom

1. Run the Minicom terminal:

   .. parsed-literal::
      :class: highlight

      sudo minicom -D *DTM serial port* -s

   For example:

   .. code-block:: console

      sudo minicom -D /dev/serial/by-id/usb-SEGGER_J-Link_000683580193-if00 -s

   The **-s** option switches you to Minicom setup mode.

#. Configure the Minicom terminal:

   .. figure:: /images/minicom_setup_window.png
      :alt: minicom configuration window

      Configuration window

   a. Select :guilabel:`Serial port setup` and set UART baudrate to ``19200``.

      .. figure:: /images/minicom_serial_port.png
         :alt: minicom serial port settings

   #. Select :guilabel:`Screen and keyboard` and press S on the keyboard to enable the **Hex Display**.
   #. Press Q on the keyboard to enable **Local echo**.

      .. figure:: /images/minicom_terminal_cfg.png
         :alt: minicom terminal screen and keyboard settings

   Minicom is now configured for receiving data.
   However, you cannot use it for sending DTM commands.

#. Send DTM commands:

   To send DTM commands, use ``echo`` with ``-ne`` options in another terminal.
   You must encode the data as hexadecimal numbers (\xHH, byte with hexadecimal value HH, 1 to 2 digits).

   .. parsed-literal::
      :class: highlight

      sudo echo -ne "*encoded command*" > *DTM serial port*

   To send a **Reset** command, for example, run the following command:

   .. code-block:: console

      sudo echo -ne "\x00\x00" > /dev/serial/by-id/usb-SEGGER_J-Link_000683580193-if00

Dependencies
************

This sample uses the following |NCS| library:

  * :ref:`fem_al_lib`

This sample uses the following |NCS| driver:

  * :ref:`uart_ipc`

This sample has the following nrfx dependencies:

  * :file:`nrfx/drivers/include/nrfx_timer.h`
  * :file:`nrfx/hal/nrf_nvmc.h`
  * :file:`nrfx/hal/nrf_radio.h`
  * :file:`nrfx/helpers/nrfx_gppi.h`

The sample also has the following nrfxlib dependency:

  * :ref:`nrfxlib:mpsl_fem`

In addition, it has the following Zephyr dependencies:

* :ref:`zephyr:device_model_api`:

   * :file:`drivers/clock_control.h`
   * :file:`drivers/uart.h`
