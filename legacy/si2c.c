#include <errno.h>
#include <stdio.h>
#include <string.h>	
#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/gpio.h>
#include "si2c.h" 
#include "sys.h"
#include "usart.h"
#if(_SUPPORT_SOFTI2C_ == 0)
#include <libopencm3/stm32/i2c.h>
#endif


uint8_t g_ucI2cRevBuf[SI2C_BUF_MAX_LEN];
uint16_t g_usI2cRevLen;
static uint8_t s_ucSendDataBak[SI2C_BUF_MAX_LEN];
static uint16_t s_usSendLenBak;
static uint8_t s_usTagbak;

#if (_SUPPORT_SOFTI2C_ > 0)

static void vSI2CDRV_Send_Ack(void)
{
	while(1)
	{
		if ( 0 == GET_SCL_DAT )
			break;
	}
	SET_I2C_SDA_OUT();		
	SET_SDA_LOW;	
	while(1)
	{
		if ( GET_SCL_DAT  )
			break;
	}		
}

static uint8_t ucSI2CDRV_Get_Addr(void)
{
	uint8_t bitcount,iic_slv_addr=0;
	uint32_t i2c_usTimeout;
	
	i2c_usTimeout = 0;
	while(1)
	{
		if ( GET_SCL_DAT )
			break;
		i2c_usTimeout++;
		if(i2c_usTimeout > I2C_TIMEOUT)
		{
		    i2c_usTimeout= 0;
		    return 0xFF;
		}
	}
	i2c_usTimeout = 0;
	while(1)
	{
		if(0==GET_SDA_DAT)
			break;
	
		i2c_usTimeout++;
		if(i2c_usTimeout > I2C_TIMEOUT)
		{
		    i2c_usTimeout= 0;
		    return 0xFF;
		}
	}		
	for(bitcount = 0; bitcount < 8; bitcount++)
	{
		while(1)
		{
			if ( 0==GET_SCL_DAT )
				break;
		}
		SET_I2C_SDA_IN();
		while(1)
		{
			if( GET_SCL_DAT )
				break;
		}
		iic_slv_addr <<= 1;  
		if(GET_SDA_DAT)
				iic_slv_addr |= 0x01;
		else
				iic_slv_addr |= 0x00;
	}
	return iic_slv_addr;
}
static uint8_t bSI2CDRV_ReadBytes(uint8_t *buf, uint16_t n)
{
    uint16_t i = 0;
		
	uint8_t	recFinish=0,bitcount,rxbyte = 0;
	uint16_t r0 = 0,r1= 0;
	//wati addr
	while(SI2C_ADDR != ucSI2CDRV_Get_Addr())
	{
	    if(i > 3)
	    {
	        return false;
	    }
	    i++;
	}
	vSI2CDRV_Send_Ack();

	while(!recFinish)
	{
		for(bitcount=0; bitcount<8; bitcount++)
		{
			while(1)
			{
				if ( 0==GET_SCL_DAT )
					break;
			}
			SET_I2C_SDA_IN();
			while(1)
			{
				if( GET_SCL_DAT )
					break;
			}
			//check STOP,clk:high;dat:low->high
			r0 = GET_SDA_DAT;
			while(1)
			{
				if( GET_SCL_DAT )
				{
					r1 = GET_SDA_DAT;
					if((r0 == 0) && (r1 > 0))
					{
						recFinish = 1;
						i = n;
						return true;
					}
				}
				else
					break;						
			}
			rxbyte <<= 1;
			if(r1)
					rxbyte |= 0x01;
			else
					rxbyte |= 0x00; 
		}
		vSI2CDRV_Send_Ack();
		buf[i] = rxbyte;
		i++;
    }
    return false;
}

static void vSI2CDRV_WriteBytes(uint8_t *buf, uint16_t buf_len)
{
    uint16_t i = 0;
	
	uint8_t txbyte,bitcount ;
	while((SI2C_ADDR+1) != ucSI2CDRV_Get_Addr())
	{
	    if(i > 3)
	    {
	        memset(buf,0x00,3);
	        return;
	    }
	    i++;
	}
	vSI2CDRV_Send_Ack();
	for(i = 0; i < buf_len; i ++)
	{        
		txbyte = buf[i];
		for(bitcount = 0; bitcount < 8; bitcount ++)
		{
				while(1)
				{
					if ( 0==GET_SCL_DAT )
						break;
				}
				SET_I2C_SDA_OUT();						
				if ( txbyte & 0x80 )
						SET_SDA_HIGH;   
				else    
						SET_SDA_LOW;  
				
				txbyte <<= 1;
				while(1)
				{
					if ( GET_SCL_DAT )
						break;
				}

		}	
			 
		while(1)
		{
			if ( 0==GET_SCL_DAT )
				break;
		}					
		SET_I2C_SDA_IN();
		while(1)
		{
			if ( GET_SCL_DAT )
				break;
		}
		if((buf_len - 1) == i)
		{
			if(GET_SDA_DAT)
			{
				//wait stop
				while(1)
				{
					if ( 0==GET_SCL_DAT )
						break;
				}					
				while(1)
				{
					if ( GET_SCL_DAT )
						break;
				}
				while(1)
				{
					if ( GET_SDA_DAT )
						break;
				}
				
			}
		}
		else
		{
			if(GET_SDA_DAT)
			{
				break;
			}
		}
	}	
}


#else
static uint8_t bSI2CDRV_ReadBytes(uint8_t *res, uint16_t n)
{
	
	uint32_t i2c_usTimeout = 0;
	
	/* Waiting for address is transferred. */
	while (!((I2C_SR1(I2C2) & I2C_SR1_ADDR)))
	{
		i2c_usTimeout++;
		if(i2c_usTimeout > I2C_TIMEOUT)
		{
		    i2c_usTimeout= 0;
		    return false;
		}
	}
	i2c_enable_ack(I2C2);
	/* Clearing ADDR condition sequence. */
	(void)I2C_SR2(I2C2);

	for (uint16_t i = 0; i < n; ++i) {
		if (i == n - 1) {
			i2c_disable_ack(I2C2);
		}
		while (!(I2C_SR1(I2C2) & I2C_SR1_RxNE));
		res[i] = i2c_get_data(I2C2);
		i2c_enable_ack(I2C2);
	}
	while (!(I2C_SR1(I2C2) & I2C_SR1_STOPF));
	
	return true;
}
static void vSI2CDRV_WriteBytes(uint8_t *data, uint16_t n)
{
	uint32_t i2c_usTimeout = 0;
	
	/* Waiting for address is transferred. */
	while (!(I2C_SR1(I2C2) & I2C_SR1_ADDR))
	{
	    i2c_usTimeout++;
		if(i2c_usTimeout > I2C_TIMEOUT)
		{
		    i2c_usTimeout= 0;
		    return;
		}
	}

	/* Clearing ADDR condition sequence. */
	(void)I2C_SR2(I2C2);

	for (uint16_t i = 0; i < n; i++) {
		i2c_send_data(I2C2, data[i]);
		while (!(I2C_SR1(I2C2) & (I2C_SR1_BTF)));
	}
	while (!(I2C_SR1(I2C2) & I2C_SR1_STOPF));
}
#endif



#if (_SUPPORT_SOFTI2C_ > 0)

void vSI2CDRV_Init(void)
{
	rcc_periph_clock_enable(RCC_GPIOB);
	rcc_periph_clock_enable(RCC_GPIOC);
    gpio_mode_setup(GPIO_SI2C_PORT,GPIO_MODE_INPUT,GPIO_PUPD_PULLUP,GPIO_SI2C_SDA);
    gpio_mode_setup(GPIO_SI2C_PORT,GPIO_MODE_INPUT,GPIO_PUPD_PULLUP,GPIO_SI2C_SCL);
	memset(s_ucSendDataBak,0x00,SI2C_BUF_MAX_LEN);
	s_usSendLenBak = 0;
}


#else
void vSI2CDRV_Init(void)
{
	rcc_periph_clock_enable(RCC_I2C2);
	rcc_periph_clock_enable(RCC_GPIOB);
	rcc_periph_clock_enable(RCC_GPIOC);

	//i2c_reset(I2C2);
	gpio_mode_setup(GPIO_SI2C_PORT, GPIO_MODE_AF, GPIO_PUPD_PULLUP, GPIO_SI2C_SCL | GPIO_SI2C_SDA);
	gpio_set_af(GPIO_SI2C_PORT, GPIO_AF4,GPIO_SI2C_SCL | GPIO_SI2C_SDA);
	//i2c_peripheral_disable(I2C2);
	//I2C_CR1(I2C2) &= ~I2C_CR1_NOSTRETCH;
	//I2C_CR1(I2C2) |= I2C_CR1_NOSTRETCH;
	/* HSI is at 2Mhz */
	//i2c_set_speed(I2C2, i2c_speed_sm_100k, 8);
	//addressing mode
	i2c_set_own_7bit_slave_address(I2C2,SI2C_ADDR);
	//(void)I2C_SR2(I2C2);
	i2c_peripheral_enable(I2C2);
	memset(s_ucSendDataBak,0x00,SI2C_BUF_MAX_LEN);
	s_usSendLenBak = 0;
}
#endif

static void UpdateConnectLessCrc( uint8_t input, uint16_t *crc )
{
	input = ( input ^ ( uint8_t )( ( *crc ) & 0x00FF ) );
	input = ( input ^ ( input << 4 ) );

	*crc = ( *crc >> 8 ) ^ ( ( uint16_t )input << 8 ) ^ ( ( uint16_t )input << 3 ) ^ ( ( uint16_t )input >> 4 );
}

static uint16_t ConnectLessCrc( uint16_t icv, uint8_t *input, uint16_t length )
{
	uint8_t p;
	uint16_t crc;

	crc = icv;

	while( length )
	{
		p = *((uint8_t  *) input++ );
		UpdateConnectLessCrc( p, &crc );
		length--;
	}

	if( 0xffff == icv || 0x00 == icv )
	{
		crc = ~crc;
	}

	return crc;
}

/*
*i2c rev
*/
uint8_t bSI2CDRV_ReceiveData(uint8_t *pucStr)
{	
    uint8_t i,ucBuf[3];
    uint16_t usLen,usCrc,usRevCrc;

    i = 0;
   
    while(i < 3)
    {
        if(false == bSI2CDRV_ReadBytes(pucStr,3))
        {
            return false;
        }
        //tlv tag + len + v
        usLen =  (pucStr[1]<<8) + (pucStr[2]&0xFF);
        if(usLen > (SI2C_BUF_MAX_LEN - DATA_HEAD_LEN))
        {
           usLen =  SI2C_BUF_MAX_LEN - DATA_HEAD_LEN;
        }
        if(usLen > 0)
        {
            //rev Data Remaining
            if(false == bSI2CDRV_ReadBytes(pucStr+3,usLen))
            {
                return false;
            }   
            SET_COMBUS_HIGH();
            //Compare checksums
            usCrc = ConnectLessCrc(0,pucStr+3,usLen-CRC_LEN);
            usRevCrc = (pucStr[3+ usLen - CRC_LEN]<<8)+(pucStr[3 + usLen - CRC_LEN + 1] & 0xFF);
            if(usCrc != usRevCrc)
            {
                SET_COMBUS_LOW();
                i++;
                ucBuf[0]= REPEAT_TAG;
                ucBuf[1]= 0x00;
                ucBuf[2]= 0x00;
                vSI2CDRV_WriteBytes(ucBuf,3);
                continue;
            }
            else
            {
                s_usTagbak = pucStr[0];
                return true;
            }
            
        }
        else
        {
            if((REPEAT_TAG == pucStr[0])&&(0x00 == pucStr[1])&&(0x00 == pucStr[2]))
            {
                SET_COMBUS_LOW();
		        vSI2CDRV_WriteBytes(s_ucSendDataBak,DATA_HEAD_LEN);  
                vSI2CDRV_WriteBytes(s_ucSendDataBak+DATA_HEAD_LEN,s_usSendLenBak);  
                continue;
            }
        }
    }
    
    return false;
    
}
/*
*i2c send 
*/
void vSI2CDRV_SendResponse(uint8_t *pucStr,uint16_t usStrLen)
{
    uint16_t usCrc;	
    uint8_t  ucHead[DATA_HEAD_LEN];
    
    SET_COMBUS_LOW();
    
    if(usStrLen > (SI2C_BUF_MAX_LEN - DATA_HEAD_LEN ))
    {
        usStrLen =  SI2C_BUF_MAX_LEN - DATA_HEAD_LEN;
    }

    //send head
    ucHead[0] = s_usTagbak;
    ucHead[1] = ((usStrLen+CRC_LEN)>>8)&0xFF;
    ucHead[2] = (usStrLen+CRC_LEN)&0xFF;
    memcpy(s_ucSendDataBak,ucHead, DATA_HEAD_LEN);
    vSI2CDRV_WriteBytes(ucHead,DATA_HEAD_LEN);
    //send data
    usCrc = ConnectLessCrc(0,pucStr,usStrLen);
    pucStr[usStrLen] = (usCrc>>8)&0xFF;
    pucStr[usStrLen+1] = usCrc&0xFF;
    usStrLen +=CRC_LEN;
    memcpy(s_ucSendDataBak+DATA_HEAD_LEN,pucStr, usStrLen);
    s_usSendLenBak = usStrLen; 
    vSI2CDRV_WriteBytes(pucStr,usStrLen);
     
}



