#ifndef _usart_H_
#define _usart_H_

#define _SUPPORT_DEBUG_UART_ 0

#if (_SUPPORT_DEBUG_UART_)
extern void usart_setup(void);
extern void vUART_DebugInfo(char *pcMsg, uint8_t *pucSendData,
                            uint16_t usStrLen);
#endif
#endif
