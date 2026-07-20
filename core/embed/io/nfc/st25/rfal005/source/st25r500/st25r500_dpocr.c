/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2024-2026 STMicroelectronics, all rights reserved
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
#define RFAL_DPO_ANALOGCONFIG_SHIFT       13U
#define RFAL_DPO_ANALOGCONFIG_MASK        0x6000U

#define ZLOAD_LOWLIM_COHM           100U        /*!< Limit for calculations: Don't go below 1 ohm: */
#define CURR_LOWLIM                 16U         /*!< Limit for calculated target current: Don't go below ~50mA/3.2 */
#define CURR_HIGHLIM                (3U*1024U)  /*!< Limit for target current, required by arithmetic. Here: Don't go beyond ~10A */
#define DRES_HIGHLIM                ((ST25R500_REG_DRIVER_d_res_mask >> ST25R500_REG_DRIVER_d_res_shift) - 1U) /*!< Do not allow dres = highZ */

/*
 ******************************************************************************
 * MACROS
 ******************************************************************************
 */

#ifndef st25R500DpoCrRampDelay
    /*! Macro to define a delay between register writes when ramping the power.
     * Default: no delay, as no additional time was needed during testing.
     * Macro can be externally overwritten as needed. */
    #define st25R500DpoCrRampDelay()                    do{}while(0)
#endif /* st25R500DpoCrRampDelay */

/*
 ******************************************************************************
 * LOCAL DATA TYPES
 ******************************************************************************
 */

/*! ST25R500 DPOCR Point struct */
typedef struct{
    uint8_t dres;  /*!< Driver resistance per DS */
    uint8_t rege;  /*!< Regulator setting per DS */
    uint8_t curr;  /*!< Current as measured by device, 3.2ms/step */
} st25r500DpoPoint;


/*! ST25R500 DPOCR instance */
typedef struct{
    bool                isInit;  /*!< Marker if module is initialized */
    st25r500DpocrConfig config;  /*!< Configuration to be used */
    st25r500DpocrInfo   info;    /*!< Provide information on current operation */
    rfalMode            curMode; /*!< Current technologoy/mode set by RFAL */
    rfalBitRate         curBR;   /*!< Current bitrate set by RFAL  */
    bool                forceAdj;/*!< Force adjustment due to take place irrespecive of I/Q values */
    uint16_t            last_i;  /*!< Stored I value taken after last adjustment */
    uint16_t            last_q;  /*!< Stored Q value taken after last adjustment */
} st25r500Dpocr;


/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

/*! ST25R500 DPOCR instance */
static st25r500Dpocr gSt25r500Dpocr;


/*! Multiplier per DS times 60 centi ohms */
static const uint16_t dres2cohm[16] =
{ /*  0   1   2   3    4    5    4    7    8    9    a    b    c     d     e      f : actually highZ, use high value for calculation, typically multiplied with 2 for differential antennas */
     61, 67, 74, 83 , 91, 100, 112, 133, 154, 183, 245, 371, 768, 1644, 3840, 32000
};


/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/
static uint16_t calcZload_cohm( uint8_t reg, uint8_t res, uint16_t curr );
static uint8_t calcRege( uint16_t curr, uint16_t zload_cohm, uint8_t dres );
static uint8_t calcCurrent( uint16_t rege, uint16_t zload_cohm, uint8_t dres );
static void st25r500BresenhamRamp( uint8_t smdres, uint8_t srege, uint8_t tmdres, uint8_t trege, uint8_t regr);
static ReturnCode st25r500DpocrRampPower( uint16_t zload_cohm, uint16_t curr, uint8_t tdres, uint8_t trege );


/*
 ******************************************************************************
 * GLOBAL FUNCTIONS
 ******************************************************************************
 */
ReturnCode st25r500DpocrInitialize( const st25r500DpocrConfig *config )
{
    ReturnCode ret;

    gSt25r500Dpocr.isInit = false;

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
        gSt25r500Dpocr.config.enabled    = false;
        gSt25r500Dpocr.config.target     = 125;       /*403mA*/
        gSt25r500Dpocr.config.minRege    =  35;       /*1.7V*/
        gSt25r500Dpocr.config.maxRege    = 110;       /*5.2V*/
        gSt25r500Dpocr.config.measRege   = 71;        /*3.3V*/
        gSt25r500Dpocr.config.measDres   = 12;        /*12*RRFO, even with shorted antenna: max 174mA @3V3*/
        gSt25r500Dpocr.config.threshold  = 2;
        gSt25r500Dpocr.config.numEntries = 4;

        gSt25r500Dpocr.config.levels[0].zloadLim   = 2050;
        gSt25r500Dpocr.config.levels[0].correction = -5;
        gSt25r500Dpocr.config.levels[1].zloadLim   = 1500;
        gSt25r500Dpocr.config.levels[1].correction = -10;
        gSt25r500Dpocr.config.levels[2].zloadLim   = 1200;
        gSt25r500Dpocr.config.levels[2].correction = -15;
        gSt25r500Dpocr.config.levels[3].zloadLim   = 1100;
        gSt25r500Dpocr.config.levels[3].correction = -20;
    }
    else
    {
        gSt25r500Dpocr.config = *config;
    }

    /* Set initialized to not block st25r500DpocrConfigWrite() */
    gSt25r500Dpocr.isInit = true;

    ret = st25r500DpocrConfigWrite( &gSt25r500Dpocr.config );

    /* Default back to not initialized */
    gSt25r500Dpocr.isInit = false;

    if( RFAL_ERR_NONE == ret )
    {
        gSt25r500Dpocr.isInit = true;

        /* By default DPO is disabled */
        st25r500DpocrSetEnabled( false );
    }

    return ret;
}


/*******************************************************************************/
static uint16_t calcZload_cohm( uint8_t reg, uint8_t res, uint16_t curr )
{
    uint32_t cohm;
    if( 0U==curr )
    {
        cohm = dres2cohm[15U]; /* Use the highZ value */
    }
    else
    {
        cohm = ( ((((uint32_t)reg+1U)*47U)*81U) / (((uint32_t)curr*32U)/10U) );   /* AN6092 eq4 reformulated part 1 */
    }
    if( cohm < ((2U*(uint32_t)dres2cohm[res]) + ZLOAD_LOWLIM_COHM) )
    {
        /* Inaccuracies may lead to too low cohm and too low or even negative zload. Saturate at 50 */
        cohm = (2U * (uint32_t)dres2cohm[res]) + ZLOAD_LOWLIM_COHM;
    }
    cohm -= (2U * (uint32_t)dres2cohm[res]);                         /* AN6092 eq4 reformulated part 2 */

    return (uint16_t)cohm;
}


/*******************************************************************************/
static uint8_t calcRege( uint16_t curr, uint16_t zload_cohm, uint8_t dres )
{
    uint32_t reg_mvolts;
    uint32_t rege;
    reg_mvolts = ( ((((uint32_t)curr*32U)/10U) * ((2U*(uint32_t)dres2cohm[dres])+(uint32_t)zload_cohm)) / 81U ); /* AN6092 eq4 solved for voltage */
    rege = ((reg_mvolts + 23U) / 47U); /* Divide and round */

    if(rege > 1U) {rege-=1U;}
    if(rege > (ST25R500_REG_REGULATOR_rege_mask >> ST25R500_REG_REGULATOR_rege_shift))
    {
    	rege = (ST25R500_REG_REGULATOR_rege_mask >> ST25R500_REG_REGULATOR_rege_shift);
    }

    return (uint8_t)rege;
}


/*******************************************************************************/
static uint8_t calcCurrent( uint16_t rege, uint16_t zload_cohm, uint8_t dres )
{
    uint32_t curr;

    curr = ( (((uint32_t)rege+1U)*47U*81U) / ( (2U * (uint32_t)dres2cohm[dres]) + zload_cohm)); /* AN6092 eq4 */

    curr = ((curr * 10U) / 32U); /* convert to ST25R500 units */
    curr = RFAL_MIN( curr, (uint8_t)UCHAR_MAX );

    return (uint8_t)curr;
}


/*******************************************************************************/
/* Bresenham's mid point algorithm from de.wikipedia adapted for writing rege and md_res */
/* smdres : Start value of md_res
 * tmdres : Target value of md_res
 * srege : Start value of rege
 * trege : Target value of rege
 * regr : remainder value of regulator register to be OR-ed in.
 */
static void st25r500BresenhamRamp( uint8_t smdres, uint8_t srege, uint8_t tmdres, uint8_t trege, uint8_t regr ) /*why sometimes 500 prefix, sometimes not*/
{
    int16_t x0 = (int16_t)smdres, y0 = (int16_t)srege, x1 = (int16_t)tmdres, y1 = (int16_t)trege;
    int16_t dx =  (int16_t)abs((int16_t)(x1 - x0)), sx = (x0 < x1) ? 1 : -1;
    int16_t dy = -(int16_t)abs((int16_t)(y1 - y0)), sy = (y0 < y1) ? 1 : -1;
    int16_t err = dx + dy, e2; /* error value e_xy */

    while(1) /* Loop is guaranteed to break due to below if..break - at some point the target values are reached by single-stepping. */
    {
        /* Originally: setPixel(x0, y0) here, optimized number of writes by putting register writes below */
        /* Possible optimization: Avoid writing previously written value. */
        if((x0 == x1) && (y0 == y1)) {break;}
        e2 = 2 * err;
        if (e2 > dy)
        {
            err += dy;
            x0 += sx;
            st25r500WriteRegister( ST25R500_REG_TX_MOD2, (uint8_t)x0 );
            st25R500DpoCrRampDelay();
        } /* e_xy+e_x > 0 */
        if (e2 < dx)
        {
            err += dx;
            y0 += sy;
            st25r500WriteRegister( ST25R500_REG_REGULATOR, (((uint8_t)y0)|regr) ); /* Write final target value */
            st25R500DpoCrRampDelay();
        } /* e_xy+e_y < 0 */
    }
}

/*******************************************************************************/
/* Advanced ramping of driver resistance and regulator voltage to avoid steep
 * and deep field artifacts.
 * This approach uses Bresenham's algorithm for drawing lines to single step
 * alternatingly d_res and md_res (instead of d_res for finer granularity.
 * after having stepped driver resistance.
 * It does tread (m)d_res linearly which is not truly the case as being in
 * the denominator of AN6092 eq4.
 * Thus small bulges are observed.
 */
static ReturnCode st25r500DpocrRampPower( uint16_t zload_cohm, uint16_t curr, uint8_t tdres, uint8_t trege )
{
    /*******************************************************************************/
    /* MISRA 8.9 An object should be defined at block scope if its identifier only appears in a single function */
    /*< Values:                              0    1    2    3    4    5                                       6    7    8   9     a    b    c    d    e    f */
    static const uint8_t dres2mdres[16] = {  0 , 10 , 18 , 26 , 31 , 35 /* no complete match, off by one */, 40 , 48 , 54 , 64 , 80 , 96 ,112 ,120 ,124 ,127 };
    uint8_t regr,regd; /* Variables to store the part of the register not to be touched */
    uint8_t r; /* Variables for signed arithmetic of step, regulator and dres */
    uint8_t txmod1, txmod2, ptx1; /* Registers which will be changed and need to be restored in the end */
    uint8_t md; /* Start and current md_res value */
    uint8_t tmdres = dres2mdres[tdres]; /* Target value for driver resistance, converted into md_res */

    RFAL_NO_WARNING( zload_cohm ); /* Alternative implemtations may use zload to more linearly shape the ramp */
    RFAL_NO_WARNING( curr );       /*           "                       curr                  "               */

    /* Prepare for using md_res by saving various used registers: */
    st25r500ReadRegister( ST25R500_REG_TX_MOD1, &txmod1 );   /* Read register to restore later on */
    st25r500ReadRegister( ST25R500_REG_TX_MOD2, &txmod2 );   /* Read register to restore later on */
    st25r500ReadRegister( ST25R500_REG_PROTOCOL_TX1, &ptx1); /* Read register to restore later on */
    /* Switch to resistor based modulation only. This way we can move from d_res to md_res for finer shaping */
    st25r500WriteRegister( ST25R500_REG_TX_MOD1, ((txmod1 & (~ST25R500_REG_TX_MOD1_rgs_am)) | ST25R500_REG_TX_MOD1_res_am) );
    /* Don't use OOK which would cause turning off the field */
    st25r500WriteRegister( ST25R500_REG_PROTOCOL_TX1, ptx1 | ST25R500_REG_PROTOCOL_TX1_tr_am);

    st25r500ReadRegister( ST25R500_REG_REGULATOR, &regr ); /* Read regulator register from chip */
    r = (regr & ST25R500_REG_REGULATOR_rege_mask); /* Start value for rege regulator setting */
    regr &= ~ST25R500_REG_REGULATOR_rege_mask; /* Remainder of register - to be kept*/

    st25r500ReadRegister( ST25R500_REG_DRIVER, &regd ); /* Read driver register from chip */
    md = dres2mdres[(regd & ST25R500_REG_DRIVER_d_res_mask)];
    regd &= ~ST25R500_REG_DRIVER_d_res_mask; /* Remainder of register - to be kept*/

    /* Switch from d_res to equivalent md_res so that we can step md_res only */
    st25r500WriteRegister( ST25R500_REG_TX_MOD2, (uint8_t) md ); /* Set md_res equivalent to current d_res*/
    st25r500WriteRegister( ST25R500_REG_TX_MOD1, ((txmod1 & (~ST25R500_REG_TX_MOD1_rgs_am))
                                                         | ST25R500_REG_TX_MOD1_mod_state
                                                         | ST25R500_REG_TX_MOD1_res_am)); /* Change to md_res */

    st25r500BresenhamRamp( md, r, tmdres, trege, regr);

    /* Regulator is already at final value, now also set d_res equivalent to current md_res */
    st25r500WriteRegister( ST25R500_REG_DRIVER, (tdres|regd) ); /* Write final target value */
    st25r500WriteRegister( ST25R500_REG_TX_MOD1, ((txmod1 & (~ST25R500_REG_TX_MOD1_rgs_am)
                                                          & (~ST25R500_REG_TX_MOD1_mod_state))
                                                          | ST25R500_REG_TX_MOD1_res_am)); /* Change to d_res */
    /* Restore registers used due to using md_res */
    st25r500WriteRegister( ST25R500_REG_TX_MOD1, txmod1 );
    st25r500WriteRegister( ST25R500_REG_TX_MOD2, txmod2 );
    st25r500WriteRegister( ST25R500_REG_PROTOCOL_TX1, ptx1);
    return RFAL_ERR_NONE;
}

/*******************************************************************************/
ReturnCode st25r500DpocrAdjust( void )
{
    uint16_t    refValue;
    uint16_t    modeID;
    rfalBitRate br;
    rfalMode    mode;
    uint8_t     tableEntry;
    uint16_t    target;
    uint8_t     currDres;
    uint8_t     reg;
    uint16_t    ichan;
    uint16_t    qchan;
    uint8_t     i;
    uint16_t    zload;

    /* Initialize local vars */
    refValue      = 0;
    mode          = RFAL_MODE_NONE;
    br            = RFAL_BR_KEEP;
    target        = gSt25r500Dpocr.config.target;
    tableEntry    = gSt25r500Dpocr.info.currentAcEntry;

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

    st25r500CalibrateWU( &ichan, &qchan );
    if( ( RFAL_DELTA( ichan, gSt25r500Dpocr.last_i) >= gSt25r500Dpocr.config.threshold ) ||
        ( RFAL_DELTA( qchan, gSt25r500Dpocr.last_q) >= gSt25r500Dpocr.config.threshold )    )
    { /* Only run dpo/current measurement if RFI signals have changed */

        /* Measure current always at same conditions to avoid changing measurement conditions
           at the expense of having more artifacts */
        reg = gSt25r500Dpocr.config.measRege; /* Move to regulator setting where current measurement is still accurate */

        st25r500ReadRegister( ST25R500_REG_DRIVER, &currDres ); /* Read Dres value from chip - configured by AC */
        currDres = (currDres & ST25R500_REG_DRIVER_d_res_mask);

        st25r500DiagMeasurePrefix(ST25R500_DIAG_MEAS_I_VDD_DR); /* Prepare current measurement */

        /* Use Zload and current from previous measurement for ramping */
        st25r500DpocrRampPower( gSt25r500Dpocr.info.currentZload, gSt25r500Dpocr.info.currentElecCurrent, gSt25r500Dpocr.config.measDres, gSt25r500Dpocr.config.measRege );

        /* Perform current measurement */
        st25r500DiagMeasureInfix( &refValue );

        /*Calculate current reduction by calculating antenna load */
        zload = calcZload_cohm( reg, gSt25r500Dpocr.config.measDres, refValue );

#ifdef sysZloadCorrection
        zload = sysZloadCorrection(zload);
#endif /* sysZloadCorrection */

        /* Now go through the target correction table to find the value for the calculated zload */
        tableEntry = 0; /* default to AC AWS level 0 */

        gSt25r500Dpocr.info.currentEntryIdx = 0xff; /* No entry found: 0xff value */
        i = gSt25r500Dpocr.config.numEntries;
        while( i > 0U )
        {
            i--;
            if( zload < gSt25r500Dpocr.config.levels[i].zloadLim )
            {
                int16_t starget = ((int16_t)target + (int16_t)gSt25r500Dpocr.config.levels[i].correction); /*  PRQA S 2152 # CERTCCM STR34 - correction is really a signed integer and not just a char. Promotion to wider signed type is required */
                if( starget < (int16_t)CURR_LOWLIM )
                {
                    target = CURR_LOWLIM;
                }
                else
                {
                    target = (uint16_t)starget;
                }
                tableEntry = gSt25r500Dpocr.config.levels[i].acEntry;
                gSt25r500Dpocr.info.currentEntryIdx = i; /* Assign found value */
                break;
            }
        }

        /* Now calculate out of measured zload and target current the required regulator */
        reg = calcRege(target, zload, currDres);
        reg = RFAL_MAX( reg, gSt25r500Dpocr.config.minRege ); /* Limit the regulator by min user limit (avoid test artifacts discused in #1490234) */
        reg = RFAL_MIN( reg, gSt25r500Dpocr.config.maxRege ); /* Limit the regulator by max user limit to e.g. guarantee sufficient drop */

        st25r500DpocrRampPower(zload, target, currDres, reg);

        /* Finish/clean up after current measuremnt */
        st25r500DiagMeasurePostfix();

        /* Store current I/Q measurement to avoid running the algorithm */
        st25r500CalibrateWU(&gSt25r500Dpocr.last_i, &gSt25r500Dpocr.last_q);

        gSt25r500Dpocr.info.currentRege        = reg;
        gSt25r500Dpocr.info.currentDres        = currDres;
        gSt25r500Dpocr.info.currentTarget      = target;
        gSt25r500Dpocr.info.currentElecCurrent = calcCurrent( reg, zload, currDres);
        gSt25r500Dpocr.info.currentZload       = zload;
        platformDelay(rfalConv1fcToMs(RFAL_GT_NFCA));

    }

    /* Apply new configs if there was a change on DPO level or RFAL mode|bitrate  */
    if( (mode != gSt25r500Dpocr.curMode) || (br != gSt25r500Dpocr.curBR) || (tableEntry != gSt25r500Dpocr.info.currentAcEntry) || ((mode == RFAL_MODE_NONE) && (tableEntry != gSt25r500Dpocr.info.currentAcEntry)) || (gSt25r500Dpocr.forceAdj) )
    {
        /* Update local context */
        gSt25r500Dpocr.curMode    = mode;
        gSt25r500Dpocr.curBR      = br;
        gSt25r500Dpocr.forceAdj   = false;
        gSt25r500Dpocr.info.currentAcEntry = tableEntry;


        /* Apply the DPO Analog Config according to this threshold */
        /* Technology field is being extended for DPO: 2msb are used for threshold step (only 4 allowed) */
        modeID  = rfalAnalogConfigGenModeID( gSt25r500Dpocr.curMode, gSt25r500Dpocr.curBR, RFAL_ANALOG_CONFIG_DPO );               /* Generate Analog Config mode ID  */
        modeID |= (((uint16_t)gSt25r500Dpocr.info.currentAcEntry << RFAL_DPO_ANALOGCONFIG_SHIFT) & RFAL_DPO_ANALOGCONFIG_MASK);   /* Add DPO threshold step|level    */
        rfalSetAnalogConfig( modeID );                                                                                             /* Apply DPO Analog Config         */

        /* TODO: RFAL Analog Config called directly from Low level Driver HAL. To be improved|revisited */
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
    uint32_t i;
    uint8_t reg;
    uint8_t res;

    if( NULL == config )
    {
        return RFAL_ERR_PARAM;
    }

    if( (!gSt25r500Dpocr.isInit) )
    {
        return RFAL_ERR_WRONG_STATE;
    }

    /* Check if the table size parameter is too big */
    if( config->numEntries > ST25R500_DPOCR_MAX_ENTRIES )
    {
        return RFAL_ERR_NOMEM;
    }

    if( (config->measDres > DRES_HIGHLIM)   || (config->minRege > ST25R500_REG_REGULATOR_rege_mask)  || (config->maxRege > ST25R500_REG_REGULATOR_rege_mask)  ||
        (config->minRege > config->maxRege) || (config->measRege > ST25R500_REG_REGULATOR_rege_mask) ||
        (config->target < CURR_LOWLIM)      || (config->target > CURR_HIGHLIM)                                                                                  )
    {
        return RFAL_ERR_PARAM;
    }

    /* ZLoad order should be strictly decreasing */
    /* Start from 1 to handle numEntries = 0 */
    for( i = 1U; i < config->numEntries; i++ )
    {
        if( config->levels[i].zloadLim >= config->levels[i - 1U].zloadLim )
        {
            return RFAL_ERR_PARAM;
        }
    }
    for( i = 0; i < config->numEntries; i++ )
    {
        if( config->levels[i].acEntry > 3U)
        {
            return RFAL_ERR_PARAM;
        }
    }

    /* Copy config passed as parameter */
    gSt25r500Dpocr.config = *config;

    /* Clear complete struct to have a fresh start and mark that values are
     * not the result of adjustment with current config */
    RFAL_MEMSET( &gSt25r500Dpocr.info, 0x00, sizeof(st25r500DpocrInfo) );

    gSt25r500Dpocr.last_i = 0;
    gSt25r500Dpocr.last_q = 0;

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
