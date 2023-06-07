/*********************************************************************
*                    SEGGER Microcontroller GmbH                     *
*                        The Embedded Experts                        *
**********************************************************************
*                                                                    *
*            (c) 1995 - 2018 SEGGER Microcontroller GmbH             *
*                                                                    *
*       www.segger.com     Support: support@segger.com               *
*                                                                    *
**********************************************************************
*                                                                    *
* All rights reserved.                                               *
*                                                                    *
* SEGGER strongly recommends to not make any changes                 *
* to or modify the source code of this software in order to stay     *
* compatible with the monitor mode protocol and J-Link.              *
*                                                                    *
* Redistribution and use in source and binary forms, with or         *
* without modification, are permitted provided that the following    *
* conditions are met:                                                *
*                                                                    *
* - Redistributions of source code must retain the above copyright   *
*   notice, this list of conditions and the following disclaimer.    *
*                                                                    *
* - Redistributions in binary form must reproduce the above          *
*   copyright notice, this list of conditions and the following      *
*   disclaimer in the documentation and/or other materials provided  *
*   with the distribution.                                           *
*                                                                    *
* - Neither the name of SEGGER Microcontroller GmbH                  *
*   nor the names of its contributors may be used to endorse or      *
*   promote products derived from this software without specific     *
*   prior written permission.                                        *
*                                                                    *
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND             *
* CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,        *
* INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF           *
* MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE           *
* DISCLAIMED. IN NO EVENT SHALL SEGGER Microcontroller BE LIABLE FOR *
* ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR           *
* CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT  *
* OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;    *
* OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF      *
* LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT          *
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE  *
* USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH   *
* DAMAGE.                                                            *
*                                                                    *
**********************************************************************
----------------------------------------------------------------------
File    : JLINK_MONITOR.c
Purpose : Implementation of debug monitor for J-Link monitor mode debug on Cortex-M devices.
--------  END-OF-HEADER  ---------------------------------------------
*/

#include "JLINK_MONITOR.h"

/*********************************************************************
*
*       Configuration
*
**********************************************************************
*/

/*********************************************************************
*
*       Defines
*
**********************************************************************
*/

/*********************************************************************
*
*       Types
*
**********************************************************************
*/

/*********************************************************************
*
*       Static data
*
**********************************************************************
*/

/*********************************************************************
*
*       Local functions
*
**********************************************************************
*/

/*********************************************************************
*
*       Global functions
*
**********************************************************************
*/

/********************************************************************* 
* 
*       JLINK_MONITOR_OnExit()
* 
*  Function description 
*    Called from DebugMon_Handler(), once per debug exit.
*    May perform some target specific operations to be done on debug mode exit.
* 
*  Notes 
*    (1) Must not keep the CPU busy for more than 100 ms
*/ 
void JLINK_MONITOR_OnExit(void) {
  //
  // Add custom code here
  //
//  BSP_ClrLED(0);
}

/********************************************************************* 
* 
*       JLINK_MONITOR_OnEnter()
* 
*  Function description 
*    Called from DebugMon_Handler(), once per debug entry.
*    May perform some target specific operations to be done on debug mode entry
* 
*  Notes 
*    (1) Must not keep the CPU busy for more than 100 ms
*/ 
void JLINK_MONITOR_OnEnter(void) {
  //
  // Add custom code here
  //
//  BSP_SetLED(0);
//  BSP_ClrLED(1);
}

/********************************************************************* 
* 
*       JLINK_MONITOR_OnPoll()
* 
*  Function description 
*    Called periodically from DebugMon_Handler(), to perform some actions that need to be performed periodically during debug mode.
* 
*  Notes 
*    (1) Must not keep the CPU busy for more than 100 ms
*/
void JLINK_MONITOR_OnPoll(void) {
  //
  // Add custom code here
  //
//  BSP_ToggleLED(0);
//  _Delay(500000);
}

/****** End Of File *************************************************/
