/*********************************************************************
*                    SEGGER Microcontroller GmbH                     *
*                        The Embedded Experts                        *
**********************************************************************
*                                                                    *
*            (c) 2014 - 2020 SEGGER Microcontroller GmbH             *
*                                                                    *
*           www.segger.com     Support: support@segger.com           *
*                                                                    *
**********************************************************************
*                                                                    *
* All rights reserved.                                               *
*                                                                    *
* Redistribution and use in source and binary forms, with or         *
* without modification, are permitted provided that the following    *
* conditions are met:                                                *
*                                                                    *
* - Redistributions of source code must retain the above copyright   *
*   notice, this list of conditions and the following disclaimer.    *
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
* DISCLAIMED.                                                        *
* IN NO EVENT SHALL SEGGER Microcontroller GmbH BE LIABLE FOR        *
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
;
;----------------------------------------------------------------------
;File    : HardFaultHandler.S
;Purpose : HardFault exception handler for IAR, Keil and GNU assembler.
;          Evaluates used stack (MSP, PSP) and passes appropiate stack
;          pointer to the HardFaultHandler "C"-routine.
;------------- END-OF-HEADER ------------------------------------------
;*/

#ifndef __IAR_SYSTEMS_ASM__
  #ifndef __CC_ARM
    #ifndef __clang__
      #ifndef __GNUC__
        #error "Unsupported assembler!"
      #endif
    #endif
  #endif
#endif

;/*********************************************************************
;*
;*     Forward declarations of segments used
;*
;**********************************************************************
;*/

#if   (defined(__IAR_SYSTEMS_ASM__))

        SECTION CODE:CODE:NOROOT(2)
        SECTION CSTACK:DATA:NOROOT(3)

#elif (defined(__CC_ARM))

        AREA    OSKERNEL, CODE, READONLY, ALIGN=2
        PRESERVE8

#endif

;/*********************************************************************
;*
;*     Publics
;*
;**********************************************************************
;*/

#if   (defined(__IAR_SYSTEMS_ASM__))

        SECTION .text:CODE:NOROOT(2)
        PUBLIC  HardFault_Handler

#elif (defined(__CC_ARM))

        EXPORT  HardFault_Handler

#elif (defined(__clang__) || defined(__GNUC__))

        .global HardFault_Handler
        .type   HardFault_Handler, function

#endif

;/*********************************************************************
;*
;*     Externals, code
;*
;**********************************************************************
;*/

#if   (defined(__IAR_SYSTEMS_ASM__))

        EXTERN  HardFaultHandler

#elif (defined(__CC_ARM))

        IMPORT  HardFaultHandler

#elif (defined(__clang__) || defined(__GNUC__))

        .extern HardFaultHandler

#endif

;/*********************************************************************
;*
;*     CODE segment
;*
;**********************************************************************
;*/

#if (defined(__clang__) || defined(__GNUC__))

        .syntax unified
        .thumb
        .balign 4
        .text

#else

        THUMB

#endif

;/*********************************************************************
;*
;*       Global functions
;*
;**********************************************************************
;*/

;/*********************************************************************
;*
;*      HardFault_Handler()
;*
;*  Function description
;*    Evaluates the used stack (MSP, PSP) and passes the appropiate
;*    stack pointer to the HardFaultHandler "C"-routine.
;*
;*  Notes
;*    (1) Ensure that HardFault_Handler is part of the exception table
;*/
#if (defined(__clang__) || defined(__GNUC__))
HardFault_Handler:
#else
HardFault_Handler
#endif
#if (defined(__IAR_SYSTEMS_ASM__) && defined(__ARM6M__) && (__CORE__ == __ARM6M__))     || \
    (defined(__CC_ARM) && defined(__TARGET_ARCH_6S_M))                                  || \
    (defined(__clang__) && defined(__ARM_ARCH) && (__ARM_ARCH == 6))                    || \
    (defined(__GNUC__) && (defined(__ARM_ARCH_6M__) || defined(__ARM_ARCH_8M_BASE__)))
        ;// This version is for Cortex M0
        movs   R0, #4
        mov    R1, LR
        tst    R0, R1            ;// Check EXC_RETURN in Link register bit 2.
        bne    Uses_PSP
        mrs    R0, MSP           ;// Stacking was using MSP.
        b      Pass_StackPtr
#if (defined(__clang__) || defined(__GNUC__))
Uses_PSP:
#else
Uses_PSP
#endif
        mrs    R0, PSP           ;// Stacking was using PSP.
#if (defined(__GNUC__) || defined(__clang__))
Pass_StackPtr:
#else
Pass_StackPtr
#endif
#else
        ;// This version is for Cortex M3, Cortex M4 and Cortex M4F
        tst    LR, #4            ;// Check EXC_RETURN in Link register bit 2.
        ite    EQ
        mrseq  R0, MSP           ;// Stacking was using MSP.
        mrsne  R0, PSP           ;// Stacking was using PSP.
#endif
#if (defined(__CC_ARM))
        ALIGN
#endif
        ldr    R1,=HardFaultHandler
        bx     R1                ;// Stack pointer passed through R0.

#if (defined(__clang__) || defined(__GNUC__))
        .end
#else
        END
#endif

;/****** End Of File *************************************************/
