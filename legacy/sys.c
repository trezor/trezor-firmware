
#include <libopencm3/stm32/gpio.h>
#include "sys.h"

uint8_t g_ucWorkMode;
uint8_t s_usPower_Button_Status;


/*
* delay time
*/
void delay_time(uint32_t uiDelay_Ms)
{
   uint32_t uiTimeout= uiDelay_Ms*30000;
   while(uiTimeout--)
   {
      __asm__("nop");
   }
}
void vPower_Control(uint8_t ucMode)
{
    uint32_t uiCount = 0;
    
    if(BUTTON_POWER_ON == ucMode)
    {
	    while(1)
        {
            if(GET_BUTTON_CANCEL())
            {
                delay_time(10);
                uiCount++;
                if(uiCount > 200)
                {
                    while(GET_BUTTON_CANCEL());
                    POWER_ON();
                    g_ucWorkMode = WORK_MODE_BLE;
                    break;
                }
                     
            }
            else
            {
                delay_time(2);
                if(0x00 == GET_BUTTON_CANCEL())
                {
                    POWER_OFF();
                    while(1);
                }
            }
        }
            
  }
  else
  {
       if(GET_BUTTON_CANCEL())
	    {
            while(GET_BUTTON_CANCEL())
	        {
		        delay_time(10);
                uiCount++;
                if(uiCount > 200)
                {
                     POWER_OFF();
                     while(1);
                }
            } 
	    }
    }
  
	
}

/*
* check usb/nfc/ble
*/
void vCheckMode(void)
{
    
    g_ucWorkMode = 0;
    
    //nfc mode 
    if(0x00 == GET_NFC_INSERT())
    {
        delay_time(2);
        if(0x00 == GET_NFC_INSERT())
        {
            g_ucWorkMode = WORK_MODE_NFC;
	        POWER_ON();
	        return;
        }
    }
    else
    {
        //usb mode 
        if(GET_USB_INSERT())
        {
            delay_time(2);
            if(GET_USB_INSERT())
            {
                g_ucWorkMode = WORK_MODE_USB;
	    	    POWER_OFF_BLE();
		        return;
            }
        }
        else
        {
            //2s power on
	        vPower_Control(BUTTON_POWER_ON);
            
        }
    }
    
}

