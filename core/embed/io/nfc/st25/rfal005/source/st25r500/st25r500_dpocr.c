/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2024 STMicroelectronics, all rights reserved
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
 *      PROJECT:   ST25R firmware
 *      $Revision: $
 *      LANGUAGE:  ISO C99
 */

/*! \file st25r500_dpocr.c
 *
 *  \author Ulrich Herrmann
 *
 *  \brief Functions to manage and set dynamic power settings for electric current based approach on R500
 *
 */

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "st25r500_dpocr.h"
#include "st25r500.h"
#include "rfal_platform.h"
#include "rfal_analogConfig.h"
#include "rfal_utils.h"

/*
 ******************************************************************************
 * ENABLE SWITCH
 ******************************************************************************
 */
 
/* Feature switch may be enabled or disabled by user at rfal_platform.h 
 * Default configuration (ST25R dependant) also provided at rfal_defConfig.h
 *  
 *    RFAL_FEATURE_DPO_CR
 */

#if RFAL_FEATURE_DPO_CR


#if RFAL_FEATURE_DPO
#error " Single DPO mechanism supported "
#endif /* RFAL_FEATURE_DPO */

/*
 ******************************************************************************
 * DEFINES
 ******************************************************************************
 */
#define RFAL_DPO_ANALOGCONFIG_SHIFT       13U          /* FIXME: Redifiniation of DPO macros, exclude? */
#define RFAL_DPO_ANALOGCONFIG_MASK        0x6000U   


/*
 ******************************************************************************
 * MACROS
 ******************************************************************************
 */
#define DELTA(A,B) (((A)>(B))?((A)-(B)):((B)-(A)))

/*
 ******************************************************************************
 * LOCAL DATA TYPES
 ******************************************************************************
 */

/*! ST25R500 DPOCR Point struct */
typedef struct{
    uint8_t dres;
    uint8_t rege;
    uint8_t curr;
} st25r500DpoPoint;


/*! ST25R500 DPOCR instance */
typedef struct{
    bool                isInit;
    st25r500DpocrConfig config;
    st25r500DpocrInfo   info;
    rfalMode            curMode;
    rfalBitRate         curBR;
    bool                forceAdj;
    st25r500DpoPoint    currBest;
} st25r500Dpocr;


/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

static st25r500Dpocr gSt25r500Dpocr;

/*
 ******************************************************************************
 * GLOBAL FUNCTIONS
 ******************************************************************************
 */
ReturnCode st25r500DpocrInitialize( const st25r500DpocrConfig *config )
{
    gSt25r500Dpocr.isInit  = false;
    
    /* Check for valid configuration                            *
     * Regulator must be set to manual setting for DPO CR usage */
    if( (!st25r500CheckReg( ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_reg_s, ST25R500_REG_REGULATOR_reg_s )) )
    {
        return RFAL_ERR_DISABLED;
    }
    
    /* Initialize DPO CR struct */
    RFAL_MEMSET( &gSt25r500Dpocr, 0x00, sizeof(st25r500Dpocr) );
    
    if( NULL == config )
    {
        gSt25r500Dpocr.config.enabled              = false;
        gSt25r500Dpocr.config.target               = 60;        /*193mA*/
        gSt25r500Dpocr.config.maxRege              = 96;        /*4.5V*/
        gSt25r500Dpocr.config.minRege              = 71;        /*3.3V*/
        gSt25r500Dpocr.config.maxDres              = 10;        /*4.09*RRFO*/
        gSt25r500Dpocr.config.minDres              = 5;         /*1.67*RRFO*/
        gSt25r500Dpocr.config.currThreshold        = 2;
        gSt25r500Dpocr.config.numEntries           = 0;
        gSt25r500Dpocr.config.tableUpThresholds[0] = 75;
        gSt25r500Dpocr.config.tableUpThresholds[1] = 85;
        gSt25r500Dpocr.config.tableUpThresholds[2] = 95;
        gSt25r500Dpocr.config.tableUpThresholds[3] = 200;
    }
    else
    {
        gSt25r500Dpocr.config = *config;
    }
    

    gSt25r500Dpocr.isInit  = true;

    /* By default DPO is disabled */
    st25r500DpocrSetEnabled( false );
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500DpocrAdjust( void )
{
    uint8_t     refValue;
    uint16_t    modeID;
    rfalBitRate br;
    rfalMode    mode;
    uint8_t     tableEntry;
    uint16_t    target;
    uint8_t     maxRege;
    uint8_t     minRege;
    uint8_t     maxDres;
    uint8_t     minDres;
    uint8_t     reg;
    uint8_t     res;
    uint16_t    currThreshold;
    bool        increasing;
    uint8_t     stage;
    
    
    /* Initialize local vars */
    refValue      = 0;
    mode          = RFAL_MODE_NONE;
    br            = RFAL_BR_KEEP;
    target        = gSt25r500Dpocr.config.target;
    maxRege       = gSt25r500Dpocr.config.maxRege;
    minRege       = gSt25r500Dpocr.config.minRege;
    maxDres       = gSt25r500Dpocr.config.maxDres;
    minDres       = gSt25r500Dpocr.config.minDres;
    currThreshold = gSt25r500Dpocr.config.currThreshold;
    
    
    /*  Algoithm has three stages:
     *  1: Move rege until we are on the other side of target, if within boundaries stop
     *  2: Move d_res until we are on the other side of target
     *  3: Move again rege until again on the other side of target
     */
    stage = 0;

    /* Obtain RFAL's current mode and bit rate */
    mode = rfalGetMode();
    rfalGetBitRate( &br, NULL );
    
    /* Check if initialized */
    if( (!gSt25r500Dpocr.isInit) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check if the Power Adjustment is disabled */
    if( (!gSt25r500Dpocr.config.enabled) )
    {
        return RFAL_ERR_PARAM;
    }

    /* Ensure that the current mode is Passive Poller and table is initialized */  /* TODO: RFAL Analog Config called directly from Low level Driver HAL. To be improved|revisited */
    if( (!rfalIsModePassivePoll( mode )) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check for valid configuration                            *
     * Regulator must be set to manual setting for DPO CR usage */
    if( (!st25r500CheckReg( ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_reg_s, ST25R500_REG_REGULATOR_reg_s )) )
    {
        return RFAL_ERR_DISABLED;
    }

    
    if( gSt25r500Dpocr.info.currentRege > maxRege )
    {
        gSt25r500Dpocr.info.currentRege = maxRege;
        st25r500ChangeRegisterBits(ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_rege_mask, gSt25r500Dpocr.info.currentRege);
    }
    
    if( gSt25r500Dpocr.info.currentRege < minRege )
    {
        gSt25r500Dpocr.info.currentRege = minRege;
        st25r500ChangeRegisterBits(ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_rege_mask, gSt25r500Dpocr.info.currentRege);
    }

    if( gSt25r500Dpocr.info.currentDres > maxDres )
    {
        gSt25r500Dpocr.info.currentDres = maxDres;
        st25r500ChangeRegisterBits(ST25R500_REG_DRIVER, ST25R500_REG_DRIVER_d_res_mask, gSt25r500Dpocr.info.currentDres);
    }
    
    if( gSt25r500Dpocr.info.currentDres < minDres )
    {
        gSt25r500Dpocr.info.currentDres = minDres;
        st25r500ChangeRegisterBits(ST25R500_REG_DRIVER, ST25R500_REG_DRIVER_d_res_mask, gSt25r500Dpocr.info.currentDres);
    }

    st25r500MeasureCurrent( &refValue );

    if( DELTA( (uint16_t)refValue, gSt25r500Dpocr.currBest.curr) > currThreshold )
    { 
        /* Value changed compared to last call -> move regulator  */
        reg = gSt25r500Dpocr.info.currentRege;
        res = gSt25r500Dpocr.info.currentDres;
        gSt25r500Dpocr.currBest.dres = gSt25r500Dpocr.info.currentDres;
        gSt25r500Dpocr.currBest.rege = gSt25r500Dpocr.info.currentRege;
        gSt25r500Dpocr.currBest.curr = refValue;

        if( refValue < target )
        { 
            /* If we are overall trying to increase, give precedence to reducing d_res */
            stage = 1; /* Skip stage 1, start with minimal regulator */
            reg = minRege;
            st25r500ChangeRegisterBits(ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_rege_mask, reg); /* Write rege */

            st25r500MeasureCurrent( &refValue );
            if( DELTA(refValue, target) < DELTA(gSt25r500Dpocr.currBest.curr, target) )
            {
                gSt25r500Dpocr.currBest.dres = res;
                gSt25r500Dpocr.currBest.rege = reg;
                gSt25r500Dpocr.currBest.curr = refValue;
            }
        }

        while( (stage++) < 3U )
        {
            increasing = (refValue < target);
            
            if( (1U == stage) || (3U == stage) )
            {
                /* Try with changing regulator */
                do{
                    if( increasing && (reg < maxRege) )
                    {
                        reg++;
                    }
                    else if( (!increasing) && (reg > minRege) )
                    {
                        reg--;
                    }
                    else
                    {
                        if( (reg != maxRege) && (reg != minRege) )
                        { /* If the fine rege allowed to stay within boundaries: stop here */
                            stage = 3;
                        }
                        break;
                    }

                    st25r500ChangeRegisterBits(ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_rege_mask, reg); /* Write rege */

                    st25r500MeasureCurrent( &refValue );
                    if( DELTA(refValue, target) < DELTA(gSt25r500Dpocr.currBest.curr, target) )
                    {
                        gSt25r500Dpocr.currBest.dres = res;
                        gSt25r500Dpocr.currBest.rege = reg;
                        gSt25r500Dpocr.currBest.curr = refValue;
                    }
                }
                while( increasing == (refValue < target) );
            }
            else if( 2U == stage )
            {
                /* Try with changing resistor */
                do{                                                   /*  PRQA S 0771 # MISRA 15.4 - Multiple break used to simplify logic  */
                    if( increasing && (res > minDres) )
                    {
                        res--;
                    }
                    else if( (!increasing) && (res < maxDres) )
                    {
                        res++;
                    }
                    else
                    {
                        break;
                    }

                    st25r500ChangeRegisterBits(ST25R500_REG_DRIVER, ST25R500_REG_DRIVER_d_res_mask, res); /* Write d_res */

                    st25r500MeasureCurrent( &refValue );
                    if( DELTA(refValue, target) < DELTA(gSt25r500Dpocr.currBest.curr, target) )
                    {
                        gSt25r500Dpocr.currBest.dres = res;
                        gSt25r500Dpocr.currBest.rege = reg;
                        gSt25r500Dpocr.currBest.curr = refValue;
                    }
                    if( increasing && (refValue >= target) )
                    { /* rege should at this step already at minRege, cannot further decrease: increase d_res */
                        res++;
                        st25r500ChangeRegisterBits(ST25R500_REG_DRIVER, ST25R500_REG_DRIVER_d_res_mask, res); /* Write d_res */

                        st25r500MeasureCurrent( &refValue );
                        if( DELTA(refValue, target) < DELTA(gSt25r500Dpocr.currBest.curr, target) )
                        {
                            gSt25r500Dpocr.currBest.dres = res;
                            gSt25r500Dpocr.currBest.rege = reg;
                            gSt25r500Dpocr.currBest.curr = refValue;
                        }
                        break;
                    }
                }
                while( increasing == (refValue < target) );
            }
            else
            {
                /* MISRA 15.7 - Empty else */
            }
        }
        
        /* Apply the best found point */
        st25r500ChangeRegisterBits(ST25R500_REG_REGULATOR, ST25R500_REG_REGULATOR_rege_mask, gSt25r500Dpocr.currBest.rege); /* Write rege */
        st25r500ChangeRegisterBits(ST25R500_REG_DRIVER, ST25R500_REG_DRIVER_d_res_mask, gSt25r500Dpocr.currBest.dres); /* Write d_res */
        gSt25r500Dpocr.info.currentRege = gSt25r500Dpocr.currBest.rege;
        gSt25r500Dpocr.info.currentDres = gSt25r500Dpocr.currBest.dres;
        st25r500MeasureCurrent( &refValue );

    }

    /* Store last measurement */
    gSt25r500Dpocr.info.currentElecCurrent = refValue;

    if( gSt25r500Dpocr.config.numEntries >= 1U )
    {
        for( tableEntry=0; tableEntry < (gSt25r500Dpocr.config.numEntries - 1U); tableEntry++ )
        {
            if( gSt25r500Dpocr.currBest.rege <= gSt25r500Dpocr.config.tableUpThresholds[tableEntry] )
            {
                break;
            }
        }

        /* Apply new configs if there was a change on DPO level or RFAL mode|bitrate  */
        if( (mode != gSt25r500Dpocr.curMode) || (br != gSt25r500Dpocr.curBR) || (tableEntry != gSt25r500Dpocr.info.currentEntryIdx) || ((mode == RFAL_MODE_NONE) && (tableEntry != gSt25r500Dpocr.info.currentEntryIdx)) || (gSt25r500Dpocr.forceAdj) )
        {
            /* Update local context */
            gSt25r500Dpocr.curMode    = mode;
            gSt25r500Dpocr.curBR      = br;
            gSt25r500Dpocr.forceAdj   = false;
            gSt25r500Dpocr.info.currentEntryIdx = tableEntry;
            

            /* Apply the DPO Analog Config according to this threshold */
            /* Technology field is being extended for DPO: 2msb are used for threshold step (only 4 allowed) */
            modeID  = rfalAnalogConfigGenModeID( gSt25r500Dpocr.curMode, gSt25r500Dpocr.curBR, RFAL_ANALOG_CONFIG_DPO );               /* Generate Analog Config mode ID  */
            modeID |= (((uint16_t)gSt25r500Dpocr.info.currentEntryIdx << RFAL_DPO_ANALOGCONFIG_SHIFT) & RFAL_DPO_ANALOGCONFIG_MASK);   /* Add DPO threshold step|level    */
            rfalSetAnalogConfig( modeID );                                                                                             /* Apply DPO Analog Config         */
            
            /* TODO: RFAL Analog Config called directly from Low level Driver HAL. To be improved|revisited */
        }
    }

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
void st25r500DpocrSetEnabled( bool enable )
{
    if( gSt25r500Dpocr.isInit )
    {
        gSt25r500Dpocr.config.enabled = enable;
        gSt25r500Dpocr.forceAdj       = enable;
        gSt25r500Dpocr.curMode        = RFAL_MODE_NONE;
        gSt25r500Dpocr.curBR          = RFAL_BR_KEEP;
    }
}


/*******************************************************************************/
void st25r500DpocrReqAdj( void )
{
    gSt25r500Dpocr.forceAdj = true;
}


/*******************************************************************************/
ReturnCode st25r500DpocrConfigWrite( const st25r500DpocrConfig* config )
{
    uint8_t reg;
    uint8_t res;

    if( NULL == config )
    {
        return RFAL_ERR_PARAM;
    }

    /* Check if the table size parameter is too big */
    if( config->numEntries > ST25R500_DPOCR_MAX_ENTRIES )
    {
        return RFAL_ERR_PARAM;
    }
    
    if( (!gSt25r500Dpocr.isInit) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* TODO: more checks might help */

    /* Copy config passed as parameter */
    gSt25r500Dpocr.config = *config;

    /* Initialize info structure */
    RFAL_MEMSET( &gSt25r500Dpocr.info, 0x00, sizeof(st25r500DpocrInfo) );

    /* Initialize currBest structure */
    RFAL_MEMSET( &gSt25r500Dpocr.currBest, 0x00, sizeof(st25r500DpoPoint) );

    /* Read current values from chip - note that it is ok to read
     * values outside limits of the config struct. First adjustment will
     * correct this. */
    st25r500ReadRegister( ST25R500_REG_REGULATOR, &reg );
    gSt25r500Dpocr.info.currentRege = (reg & ST25R500_REG_REGULATOR_rege_mask); /* Keep only rege */

    st25r500ReadRegister( ST25R500_REG_DRIVER, &res );
    gSt25r500Dpocr.info.currentDres = (res & ST25R500_REG_DRIVER_d_res_mask);

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500DpocrConfigRead( st25r500DpocrConfig* config )
{
    /* Check for valid parameters */
    if( config == NULL )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Check if initialized */
    if( (!gSt25r500Dpocr.isInit) )
    {
        return RFAL_ERR_WRONG_STATE;
    }

    *config = gSt25r500Dpocr.config;

    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode st25r500DpocrGetInfo( st25r500DpocrInfo* info )
{
    /* Check for valid parameters */
    if( info == NULL )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Check if initialized */
    if( (!gSt25r500Dpocr.isInit) )
    {
        return RFAL_ERR_WRONG_STATE;
    }

    *info = gSt25r500Dpocr.info;

    return RFAL_ERR_NONE;
}


#endif /* RFAL_FEATURE_DPO_CR */
