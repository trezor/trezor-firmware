/*
 * This file is part of the libopencm3 project.
 *
 * Copyright (C) 2009 Uwe Hermann <uwe@hermann-uwe.de>,
 * Copyright (C) 2011 Piotr Esden-Tempski <piotr@esden.net>
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

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/usart.h>
#include <libopencm3/cm3/nvic.h>
#include <libopencm3/stm32/rcc.h>
#include "usart.h"
#if(_SUPPORT_DEBUG_UART_)
/************************************************************************
函数名称:vUART_HtoA
参数:
	pucSrc:		要格式化的源数据
	usLen:		要格式化的源数据长度
	pucDes:		格式化后的数据
返回:
	NULL
功能:
	该函数用于UART数据格式化数据。
************************************************************************/
static void vUART_HtoA(uint8_t *pucSrc, uint16_t usLen, uint8_t *pucDes)
{
	uint16_t i,j;
	uint8_t mod=1;	//,sign;

	for(i=0,j=0; i<2*usLen; i+=2,j++)
	{
		mod = (pucSrc[j]>>4)&0x0F;
		if(mod<=9)
			pucDes[i] = mod + 48;
		else
			pucDes[i] = mod + 55;

		mod = pucSrc[j]&0x0F;
		if(mod<=9)
			pucDes[i+1] = mod + 48;
		else
			pucDes[i+1] = mod + 55;
	}
}
/************************************************************************
函数名称:vUART_DebugInfo
参数:
	pucSendData:		要发送的数据
	usStrLen:			要发送的数据长度
返回:
	NULL
功能:
	该函数用于UART数据发送。
************************************************************************/
static void vUART_SendData(uint8_t * pucSendData, uint16_t  usStrLen)
{
	uint16_t i;
	for(i = 0;i < usStrLen;i++)
	{
		usart_send_blocking(USART1, pucSendData[i]);
	}
}

/************************************************************************
函数名称:vUART_DebugInfo
参数:
	pcMsgTag:		提示消息
	pucSendData:	需要格式化发送的数据
	usStrLen:		数据长度
返回:
	NULL
功能:
	该函数用于格式化发送数据。
************************************************************************/
 void vUART_DebugInfo(char * pcMsg, uint8_t *pucSendData, uint16_t usStrLen)
{
	uint8_t ucBuff[600];

	vUART_SendData((uint8_t *)pcMsg, strlen(pcMsg));

	vUART_HtoA(pucSendData,usStrLen,ucBuff);
	vUART_SendData(ucBuff,usStrLen*2);
	vUART_SendData((uint8_t *)"\n",1);
}



void usart_setup(void)
{
	rcc_periph_clock_enable(RCC_USART1);
	//rcc_periph_clock_enable(RCC_GPIOA);
	//gpio_mode_setup(GPIOA, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO9);
	//gpio_set_af(GPIOA, GPIO_AF7, GPIO9 | GPIO10);
	rcc_periph_clock_enable(RCC_GPIOB);
	gpio_mode_setup(GPIOB, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO6);
	gpio_set_af(GPIOB, GPIO_AF7, GPIO6 | GPIO7);

	/* Setup UART parameters. */
	usart_set_baudrate(USART1, 115200);
	usart_set_databits(USART1, 8);
	usart_set_stopbits(USART1, USART_STOPBITS_1);
	usart_set_parity(USART1, USART_PARITY_NONE);
	usart_set_flow_control(USART1, USART_FLOWCONTROL_NONE);
	usart_set_mode(USART1, USART_MODE_TX);

	/* Finally enable the USART. */
	usart_enable(USART1);
}
#endif

