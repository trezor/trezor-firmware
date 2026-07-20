
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2016-2022 STMicroelectronics, all rights reserved
  *
  * Unless required by applicable law or agreed to in writing, software
  * distributed under the License is distributed on an "AS IS" BASIS,
  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied,
  * AND SPECIFICALLY DISCLAIMING THE IMPLIED WARRANTIES OF MERCHANTABILITY,
  * FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
  * See the License for the specific language governing permissions and
  * limitations under the License.
  *
******************************************************************************/



/*
 *      PROJECT:   ST25R200 firmware
 *      Revision: 
 *      LANGUAGE:  ISO C99
 */

/*! \file st25r200_com.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief Implementation of ST25R200 communication
 *
 */

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/

#include "st25r200.h"
#include "st25r200_com.h"
#include "st25r200_irq.h"
#include "rfal_platform.h"
#include "rfal_utils.h"


/*
******************************************************************************
* LOCAL DEFINES
******************************************************************************
*/

#define ST25R200_OPTIMIZE              true                           /*!< Optimization switch: false always write value to register     */
#define ST25R200_MOSI_IDLE             (0x00)                         /*!< ST25R200 MOSI IDLE state                                      */
#define ST25R200_BUF_LEN               (ST25R200_CMD_LEN+ST25R200_FIFO_DEPTH) /*!< ST25R200 communication buffer: CMD + FIFO length      */

/*
******************************************************************************
* MACROS
******************************************************************************
*/

/*!
 ******************************************************************************
 * \brief ST25R200 communication Repeat Start
 * 
 * This method performs the required actions to repeat start a transmission
 * with ST25R200 
 ******************************************************************************
 */
#define st25r200comRepeatStart()   

#if defined(ST25R_COM_SINGLETXRX)
static uint8_t  comBuf[ST25R200_BUF_LEN];                             /*!< ST25R200 communication buffer                                 */
static uint16_t comBufIt;                                             /*!< ST25R200 communication buffer iterator                        */
#endif /* ST25R_COM_SINGLETXRX */
    
/*
 ******************************************************************************
 * LOCAL FUNCTION PROTOTYPES
 ******************************************************************************
 */

/*!
 ******************************************************************************
 * \brief ST25R200 communication Start
 * 
 * This method performs the required actions to start communications with 
 * ST25R200, either by SPI or I2C 
 ******************************************************************************
 */
static void st25r200comStart( void );

/*!
 ******************************************************************************
 * \brief ST25R200 communication Stop
 * 
 * This method performs the required actions to terminate communications with 
 * ST25R200, either by SPI or I2C 
 ******************************************************************************
 */
static void st25r200comStop( void );


/*!
 ******************************************************************************
 * \brief ST25R200 communication Tx
 * 
 * This method performs the required actions to transmit the given buffer
 * to ST25R200, either by SPI or I2C
 * 
 * \param[in]  txBuf : the buffer to transmit
 * \param[in]  txLen : the length of the buffer to transmit
 * \param[in]  last   : true if last data to be transmitted
 * \param[in]  txOnly : true no reception is to be performed
 *  
 ******************************************************************************
 */
static void st25r200comTx( const uint8_t* txBuf, uint16_t txLen, bool last, bool txOnly );


/*!
 ******************************************************************************
 * \brief ST25R200 communication Rx
 * 
 * This method performs the required actions to receive from ST25R200 the given 
 * amount of bytes, either by SPI or I2C
 * 
 * \param[out]  rxBuf : the buffer place the received bytes
 * \param[in]   rxLen : the length to receive
 *  
 ******************************************************************************
 */
static void st25r200comRx( uint8_t* rxBuf, uint16_t rxLen );

/*!
 ******************************************************************************
 * \brief ST25R200 communication Tx Byte
 * 
 * This helper method transmits a byte passed by value and not by reference
 * 
 * \param[in]   txByte : the value of the byte to be transmitted
 * \param[in]   last   : true if last byte to be transmitted
 * \param[in]   txOnly : true no reception is to be performed
 *  
 ******************************************************************************
 */
static void st25r200comTxByte( uint8_t txByte, bool last, bool txOnly );


/*
 ******************************************************************************
 * LOCAL FUNCTION
 ******************************************************************************
 */
static void st25r200comStart( void )
{
    /* Make this operation atomic, disabling ST25R200 interrupt during communications*/
    platformProtectST25RComm();
    
    /* Perform the chip select */
    platformSpiSelect();
    
    #if defined(ST25R_COM_SINGLETXRX)
        comBufIt = 0;                                  /* Reset local buffer position   */
    #endif /* ST25R_COM_SINGLETXRX */
}


/*******************************************************************************/
static void st25r200comStop( void )
{
    /* Release the chip select */
    platformSpiDeselect();
    
    /* reEnable the ST25R200 interrupt */
    platformUnprotectST25RComm();
}



/*******************************************************************************/
static void st25r200comTx( const uint8_t* txBuf, uint16_t txLen, bool last, bool txOnly )
{
    RFAL_NO_WARNING(last);
    RFAL_NO_WARNING(txOnly);
    
    if( txLen > 0U )
    {
        #ifdef ST25R_COM_SINGLETXRX
            
            RFAL_MEMCPY( &comBuf[comBufIt], txBuf, RFAL_MIN( txLen, (uint16_t)(ST25R200_BUF_LEN - comBufIt) ) );  /* Copy tx data to local buffer                      */
            comBufIt += RFAL_MIN( txLen, (ST25R200_BUF_LEN - comBufIt) );                                         /* Store position on local buffer                    */
                
            if( last && txOnly )                                                                                  /* Only perform SPI transaction if no Rx will follow */
            {
                platformSpiTxRx( comBuf, NULL, comBufIt );
            }
            
        #else
            platformSpiTxRx( txBuf, NULL, txLen );
        #endif /* ST25R_COM_SINGLETXRX */
    }
}


/*******************************************************************************/
static void st25r200comRx( uint8_t* rxBuf, uint16_t rxLen )
{
#ifndef ST25R_COM_SINGLETXRX
    uint8_t  dummyBuf;
    uint16_t rxIt;
#endif /* ST25R_COM_SINGLETXRX */
    
    if( rxLen > 0U )
    {
        
    #ifdef ST25R_COM_SINGLETXRX
        RFAL_MEMSET( &comBuf[comBufIt], ST25R200_MOSI_IDLE, RFAL_MIN( rxLen, (uint16_t)(ST25R200_BUF_LEN - comBufIt) ) ); /* Clear outgoing buffer                        */
        platformSpiTxRx( comBuf, comBuf, RFAL_MIN( (comBufIt + rxLen), ST25R200_BUF_LEN ) );                    /* Transceive as a single SPI call                        */
        if( rxBuf != NULL )
        {
            RFAL_MEMCPY( rxBuf, &comBuf[comBufIt], RFAL_MIN( rxLen, (uint16_t)(ST25R200_BUF_LEN - comBufIt) ) );/* Copy from local buf to output buffer and skip cmd byte */
        }
    #else
        
        /* In case rxBuf is not provided, ensure that SPI operation is executed. *
         * Depending on the HAL used, the SPI driver may not support             *
         * NULL as Rx buffer, do single byte SPI transactions to a dummy buffer  */
        if( rxBuf == NULL )
        {
            for( rxIt = 0; (rxIt < rxLen); rxIt++ )
            {
                dummyBuf = ST25R200_MOSI_IDLE;                                                                   /* Clear outgoing|incoming buffer                         */
                platformSpiTxRx( &dummyBuf, &dummyBuf, 1U );                                                     /* Re-use the buffer as SPI outputs data first then reads */
            }
        }
        else
        {
            RFAL_MEMSET( rxBuf, ST25R200_MOSI_IDLE, rxLen );                                                     /* Clear outgoing|incoming buffer                         */
            platformSpiTxRx( rxBuf, rxBuf, rxLen );                                                              /* Re-use the rxBuf as SPI outputs data first then reads  */
        }
        
    #endif /* ST25R_COM_SINGLETXRX */

    }
}


/*******************************************************************************/
static void st25r200comTxByte( uint8_t txByte, bool last, bool txOnly )
{
    uint8_t val = txByte;               /* MISRA 17.8: use intermediate variable */
    st25r200comTx( &val, ST25R200_REG_LEN, last, txOnly );
}

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/

/*******************************************************************************/
ReturnCode st25r200ReadRegister( uint8_t reg, uint8_t* val )
{
    return st25r200ReadMultipleRegisters( reg, val, ST25R200_REG_LEN );
}


/*******************************************************************************/
ReturnCode st25r200ReadMultipleRegisters( uint8_t reg, uint8_t* values, uint16_t length )
{
    if( length > 0U )
    {
        st25r200comStart();
        st25r200comTxByte( (reg | ST25R200_READ_MODE), true, false );
        st25r200comRepeatStart();
        st25r200comRx( values, length );
        st25r200comStop();
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200WriteRegister( uint8_t reg, uint8_t val )
{
    uint8_t value = val;               /* MISRA 17.8: use intermediate variable */
    return st25r200WriteMultipleRegisters( reg, &value, ST25R200_REG_LEN );
}


/*******************************************************************************/
ReturnCode st25r200WriteMultipleRegisters( uint8_t reg, const uint8_t* values, uint16_t length )
{
    if( length > 0U )
    {
        st25r200comStart();
        st25r200comTxByte( (reg | ST25R200_WRITE_MODE), false, true );
        st25r200comTx( values, length, true, true );
        st25r200comStop();
        
        /* Send a WriteMultiReg event to LED handling */
        st25r200ledEvtWrMultiReg( reg, values, (uint8_t)length );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200WriteFifo( const uint8_t* values, uint16_t length )
{
    if( length > ST25R200_FIFO_DEPTH )
    {
        return RFAL_ERR_PARAM;
    }
    
    st25r200WriteMultipleRegisters( ST25R200_FIFO_ACCESS, values, length );

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200ReadFifo( uint8_t* buf, uint16_t length )
{
    if( length > 0U )
    {
        if( length > ST25R200_FIFO_DEPTH )
        {
            return RFAL_ERR_PARAM;
        }
        
        st25r200ReadMultipleRegisters( ST25R200_FIFO_ACCESS, buf, length );
    }

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200ExecuteCommand( uint8_t cmd )
{
    st25r200comStart();
    st25r200comTxByte( (cmd | ST25R200_CMD_MODE ), true, true );
    st25r200comStop();
    
    /* Send a cmd event to LED handling */
    st25r200ledEvtCmd( cmd );
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200ExecuteCommands( const uint8_t *cmds, uint8_t length )
{
    st25r200comStart();
    st25r200comTx( cmds, length, true, true );
    st25r200comStop();
    
    /* Send cmd event to LED handling */
    st25r200ledEvtCmds( cmds, length );
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200ReadTestRegister( uint8_t reg, uint8_t* val )
{
    st25r200comStart();
    st25r200comTxByte( ST25R200_CMD_TEST_ACCESS, false, false );
    st25r200comTxByte( (reg | ST25R200_READ_MODE), true, false );
    st25r200comRepeatStart();
    st25r200comRx( val, ST25R200_REG_LEN );
    st25r200comStop();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200WriteTestRegister( uint8_t reg, uint8_t val )
{
    uint8_t value = val;               /* MISRA 17.8: use intermediate variable */

    st25r200comStart();
    st25r200comTxByte( ST25R200_CMD_TEST_ACCESS, false, true );
    st25r200comTxByte( (reg | ST25R200_WRITE_MODE), false, true );
    st25r200comTx( &value, ST25R200_REG_LEN, true, true );
    st25r200comStop();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200WriteMultipleTestRegister( uint8_t reg, const uint8_t* values, uint8_t length )
{
    st25r200comStart();
    st25r200comTxByte( ST25R200_CMD_TEST_ACCESS, false, true );
    st25r200comTxByte( (reg | ST25R200_WRITE_MODE), false, true );
    st25r200comTx( values, length, true, true );
    st25r200comStop();
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r200ClrRegisterBits( uint8_t reg, uint8_t clr_mask )
{
    ReturnCode ret;
    uint8_t    rdVal;
    
    /* Read current reg value */
    RFAL_EXIT_ON_ERR( ret, st25r200ReadRegister(reg, &rdVal) );
    
    /* Only perform a Write if value to be written is different */
    if( ST25R200_OPTIMIZE && (rdVal == (uint8_t)(rdVal & ~clr_mask)) )
    {
        return RFAL_ERR_NONE;
    }
    
    /* Write new reg value */
    return st25r200WriteRegister(reg, (uint8_t)(rdVal & ~clr_mask) );
}


/*******************************************************************************/
ReturnCode st25r200SetRegisterBits( uint8_t reg, uint8_t set_mask )
{
    ReturnCode ret;
    uint8_t    rdVal;
    
    /* Read current reg value */
    RFAL_EXIT_ON_ERR( ret, st25r200ReadRegister(reg, &rdVal) );
    
    /* Only perform a Write if the value to be written is different */
    if( ST25R200_OPTIMIZE && (rdVal == (rdVal | set_mask)) )
    {
        return RFAL_ERR_NONE;
    }
    
    /* Write new reg value */
    return st25r200WriteRegister(reg, (rdVal | set_mask) );
}


/*******************************************************************************/
ReturnCode st25r200ChangeRegisterBits( uint8_t reg, uint8_t valueMask, uint8_t value )
{
    return st25r200ModifyRegister(reg, valueMask, (valueMask & value) );
}


/*******************************************************************************/
ReturnCode st25r200ModifyRegister( uint8_t reg, uint8_t clr_mask, uint8_t set_mask )
{
    ReturnCode ret;
    uint8_t    rdVal;
    uint8_t    wrVal;
    
    /* Read current reg value */
    RFAL_EXIT_ON_ERR( ret, st25r200ReadRegister(reg, &rdVal) );
    
    /* Compute new value */
    wrVal  = (uint8_t)(rdVal & ~clr_mask);
    wrVal |= set_mask;
    
    /* Only perform a Write if the value to be written is different */
    if( ST25R200_OPTIMIZE && (rdVal == wrVal) )
    {
        return RFAL_ERR_NONE;
    }
    
    /* Write new reg value */
    return st25r200WriteRegister(reg, wrVal );
}


/*******************************************************************************/
ReturnCode st25r200ChangeTestRegisterBits( uint8_t reg, uint8_t valueMask, uint8_t value )
{
    ReturnCode ret;
    uint8_t    rdVal;
    uint8_t    wrVal;
    
    /* Read current reg value */
    RFAL_EXIT_ON_ERR( ret, st25r200ReadTestRegister(reg, &rdVal) );
    
    /* Compute new value */
    wrVal  = (uint8_t)(rdVal & ~valueMask);
    wrVal |= (uint8_t)(value & valueMask);
    
    /* Only perform a Write if the value to be written is different */
    if( ST25R200_OPTIMIZE && (rdVal == wrVal) )
    {
        return RFAL_ERR_NONE;
    }
    
    /* Write new reg value */
    return st25r200WriteTestRegister(reg, wrVal );
}


/*******************************************************************************/
bool st25r200CheckReg( uint8_t reg, uint8_t mask, uint8_t val )
{
    uint8_t regVal;
    
    regVal = 0;
    st25r200ReadRegister( reg, &regVal );
    
    return ( (regVal & mask) == val );
}


/*******************************************************************************/
bool st25r200IsRegValid( uint8_t reg )
{
    if( !( ((int16_t)reg >= (int16_t)ST25R200_REG_OPERATION) && (reg < ST25R200_FIFO_ACCESS) ) )
    {
        return false;
    }    
    return true;
}





/*
******************************************************************************
* MACROS
******************************************************************************
*/

#ifdef PLATFORM_LED_RX_PIN
    #define st25r200ledRxOn()            platformLedOn( PLATFORM_LED_RX_PORT, PLATFORM_LED_RX_PIN );           /*!< LED Rx Pin On from system HAL            */
    #define st25r200ledRxOff()           platformLedOff( PLATFORM_LED_RX_PORT, PLATFORM_LED_RX_PIN );          /*!< LED Rx Pin Off from system HAL           */
#else /* PLATFORM_LED_RX_PIN */
    #define st25r200ledRxOn()
    #define st25r200ledRxOff()
#endif /* PLATFORM_LED_RX_PIN */


#ifdef PLATFORM_LED_FIELD_PIN
    #define st25r200ledFieldOn()         platformLedOn( PLATFORM_LED_FIELD_PORT, PLATFORM_LED_FIELD_PIN );     /*!< LED Field Pin On from system HAL            */
    #define st25r200ledFieldOff()        platformLedOff( PLATFORM_LED_FIELD_PORT, PLATFORM_LED_FIELD_PIN );    /*!< LED Field Pin Off from system HAL           */
#else /* PLATFORM_LED_FIELD_PIN */
    #define st25r200ledFieldOn()
    #define st25r200ledFieldOff()
#endif /* PLATFORM_LED_FIELD_PIN */

#ifdef PLATFORM_LED_ERR_PIN
    #define st25r200ledErrOn()         platformLedOn( PLATFORM_LED_ERR_PORT, PLATFORM_LED_ERR_PIN );     /*!< LED Field Pin On from system HAL            */
    #define st25r200ledErrOff()        platformLedOff( PLATFORM_LED_ERR_PORT, PLATFORM_LED_ERR_PIN );    /*!< LED Field Pin Off from system HAL           */
#else /* PLATFORM_LED_ERR_PIN */
    #define st25r200ledErrOn()
    #define st25r200ledErrOff()
#endif /* PLATFORM_LED_ERR_PIN */

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/

void st25r200ledInit( void )
{
    /* Initialize LEDs if existing and defined */
    platformLedsInitialize();
    
    st25r200ledRxOff();
    st25r200ledFieldOff();
    st25r200ledErrOff();
}


/*******************************************************************************/
void st25r200ledEvtIrq( uint32_t irqs )
{
    if( (irqs & ST25R200_IRQ_MASK_TXE ) != 0U )
    {
        st25r200ledFieldOn();
        st25r200ledErrOff();
    }
    
    if( (irqs & (ST25R200_IRQ_MASK_RXS | ST25R200_IRQ_MASK_SUBC_START) ) != 0U )
    {
        st25r200ledRxOn();
    }
    
    if( ((irqs & (ST25R200_IRQ_MASK_RXE | ST25R200_IRQ_MASK_NRE | ST25R200_IRQ_MASK_RX_REST | ST25R200_IRQ_MASK_OSC )) != 0U ) ) 
    {
        st25r200ledRxOff();
    }
    
    if( ((irqs & (ST25R200_IRQ_MASK_CRC | ST25R200_IRQ_MASK_PAR | ST25R200_IRQ_MASK_HFE | ST25R200_IRQ_MASK_SFE)) != 0U) )
    {
        st25r200ledErrOn();
    }
}


/*******************************************************************************/
void st25r200ledEvtWrReg( uint8_t reg, uint8_t val )
{
    if( reg == ST25R200_REG_OPERATION )
    {
        if( (ST25R200_REG_OPERATION_tx_en & val) != 0U )
        {
            st25r200ledFieldOn();
        }
        else
        {
            st25r200ledFieldOff();
            st25r200ledRxOff();
        }
    }
}


/*******************************************************************************/
void st25r200ledEvtWrMultiReg( uint8_t reg, const uint8_t* vals, uint8_t len )
{
    uint8_t i;
    
    for(i=0; i<(len); i++)
    {
        st25r200ledEvtWrReg( (reg+i), vals[i] );
    }
}


/*******************************************************************************/
void st25r200ledEvtCmds( const uint8_t* cmds, uint8_t len )
{
    uint8_t i;
    
    for(i=0; i<(len); i++)
    {
        st25r200ledEvtCmd( cmds[i] );
    }
}


/*******************************************************************************/
void st25r200ledEvtCmd( uint8_t cmd )
{
    if( cmd == ST25R200_CMD_TRANSMIT )
    {
        st25r200ledFieldOff();
    }
    
    if( cmd == ST25R200_CMD_UNMASK_RECEIVE_DATA )
    {
        st25r200ledRxOff();
    }
    
    if( cmd == ST25R200_CMD_SET_DEFAULT )
    {
        st25r200ledFieldOff();
        st25r200ledRxOff();
        st25r200ledErrOff();
    }
}

