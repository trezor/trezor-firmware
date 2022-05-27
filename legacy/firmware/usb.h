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

#ifndef __USB_H__
#define __USB_H__

#define USB_PACKET_SIZE 64

void usbInit(void);
void usbPoll(void);
void usbReconnect(void);

/*
 * Setting this value to 1 will limit the protobuf messages `usbPoll` and
 * `waitAndProcessUSBRequests` can handle to a few defined in `msg_read_tiny`.
 *
 * Also affects U2F and DebugLink messages.
 *
 * Setting to 1 is meant to prevent infinite recursion when you need to read a
 * message while being called from FSM.
 *
 * Setting to 0 allows processing all messages.
 */
char usbTiny(char set);

/*
 * This will wait given number of milliseconds for arrival of protobuf message.
 * If it arrives, it will service it before returning.
 *
 * If you call this function from any function that is called from FSM,
 * you must use `usbTiny(1)` before and `usbTiny(oldTinyValue)` or `usbTiny(0)`
 * after, otherwise there is possibility of stack exhaustion.
 */
void waitAndProcessUSBRequests(uint32_t millis);

/*
 * Flush out any messages still in USB bus FIFO while waiting given number
 * of milliseconds. Any incoming USB protobuf messages are not serviced.
 */
void usbFlush(uint32_t millis);

#endif
