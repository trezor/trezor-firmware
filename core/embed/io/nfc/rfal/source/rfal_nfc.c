
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2020 STMicroelectronics, all rights reserved
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

/*! \file rfal_nfc.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief RFAL NFC device  
 *  
 *  This module provides the required features to behave as an NFC Poller 
 *  or Listener device. It grants an easy to use interface for the following
 *  activities: Technology Detection, Collision Resolution, Activation,
 *  Data Exchange, and Deactivation
 *  
 *  This layer is influenced by (but not fully aligned with) the NFC Forum 
 *  specifications, in particular: Activity 2.0 and NCI 2.0
 *
 */
 
/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_nfc.h"
#include "rfal_utils.h"
#include "rfal_analogConfig.h"


/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/
#define RFAL_NFC_MAX_DEVICES          5U    /*!< Max number of devices supported */
#define RFAL_NFC_T_FIELD_OFF          5U    /*!< tFIELD_OFF minimal duration  Activity 2.2  Table 26 */


/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/

#define rfalNfcNfcNotify( st )                         if( gNfcDev.disc.notifyCb != NULL )  gNfcDev.disc.notifyCb( (st) )
    
#define rfalNfcpCbPollerInitialize()                   ((gNfcDev.disc.propNfc.rfalNfcpPollerInitialize != NULL) ? gNfcDev.disc.propNfc.rfalNfcpPollerInitialize() : RFAL_ERR_NOTSUPP )
#define rfalNfcpCbPollerTechnologyDetection()          ((gNfcDev.disc.propNfc.rfalNfcpPollerTechnologyDetection != NULL) ? gNfcDev.disc.propNfc.rfalNfcpPollerTechnologyDetection() : RFAL_ERR_TIMEOUT )
#define rfalNfcpCbPollerStartCollisionResolution()     ((gNfcDev.disc.propNfc.rfalNfcpPollerStartCollisionResolution != NULL) ? gNfcDev.disc.propNfc.rfalNfcpPollerStartCollisionResolution() : RFAL_ERR_NOTSUPP )
#define rfalNfcpCbPollerGetCollisionResolutionStatus() ((gNfcDev.disc.propNfc.rfalNfcpPollerGetCollisionResolutionStatus != NULL) ? gNfcDev.disc.propNfc.rfalNfcpPollerGetCollisionResolutionStatus() : RFAL_ERR_NOTSUPP )
#define rfalNfcpCbStartActivation()                    ((gNfcDev.disc.propNfc.rfalNfcpStartActivation != NULL) ? gNfcDev.disc.propNfc.rfalNfcpStartActivation() : RFAL_ERR_NOTSUPP )
#define rfalNfcpCbGetActivationStatus()                ((gNfcDev.disc.propNfc.rfalNfcpGetActivationStatus != NULL) ? gNfcDev.disc.propNfc.rfalNfcpGetActivationStatus() : RFAL_ERR_NOTSUPP )

#define rfalNfcHasPollerTechs()                        ((gNfcDev.disc.techs2Find & (RFAL_NFC_POLL_TECH_A | RFAL_NFC_POLL_TECH_B | RFAL_NFC_POLL_TECH_F | RFAL_NFC_POLL_TECH_V |  \
                                                                                   RFAL_NFC_POLL_TECH_AP2P | RFAL_NFC_POLL_TECH_ST25TB | RFAL_NFC_POLL_TECH_PROP)) != 0U)
    
/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! Buffer union, only one interface is used at a time                                                        */
typedef union{  /*PRQA S 0750 # MISRA 19.2 - Members of the union will not be used concurrently, only one interface at a time */
    rfalIsoDepBufFormat   isoDepBuf;                  /*!< ISO-DEP buffer format (with header/prologue)       */
    rfalNfcDepBufFormat   nfcDepBuf;                  /*!< NFC-DEP buffer format (with header/prologue)       */
}rfalNfcTmpBuffer;


/*! RFAL NFC instance                                                                                */
typedef struct{
    rfalNfcState            state;              /*!< Main state                                      */
    uint16_t                techsFound;         /*!< Technologies found bitmask                      */
    uint16_t                techs2do;           /*!< Technologies still to be performed              */
    uint16_t                techDctCnt;         /*!< Technologies detection counter (before WU)      */
    rfalBitRate             ap2pBR;             /*!< Bit rate to poll for AP2P                       */
    uint8_t                 selDevIdx;          /*!< Selected device index                           */
    rfalNfcDevice           *activeDev;         /*!< Active device pointer                           */
    rfalNfcDiscoverParam    disc;               /*!< Discovery parameters                            */
    rfalNfcDevice           devList[RFAL_NFC_MAX_DEVICES];   /*!< Location of device list            */
    uint8_t                 devCnt;             /*!< Decices found counter                           */
    uint32_t                discTmr;            /*!< Discovery Total duration timer                  */
    ReturnCode              dataExErr;          /*!< Last Data Exchange error                        */
    rfalNfcDeactivateType   deactType;          /*!< Deactivation type                               */
    bool                    isRxChaining;       /*!< Flag indicating Other device is chaining        */
    uint32_t                lmMask;             /*!< Listen Mode mask                                */
    bool                    isFieldOn;          /*!< Flag indicating Fieldon for Passive Poll        */
    bool                    isTechInit;         /*!< Flag indicating technology has been set         */
    bool                    isOperOngoing;      /*!< Flag indicating operation is ongoing            */
    bool                    isDeactivating;     /*!< Flag indicating deactivation is ongoing         */

    rfalNfcaSensRes         sensRes;            /*!< SENS_RES during card detection and activation   */
    rfalNfcbSensbRes        sensbRes;           /*!< SENSB_RES during card detection and activation  */
    uint8_t                 sensbResLen;        /*!< SENSB_RES length                                */

    rfalNfcBuffer           txBuf;              /*!< Tx buffer for Data Exchange                     */
    rfalNfcBuffer           rxBuf;              /*!< Rx buffer for Data Exchange                     */
    uint16_t                rxLen;              /*!< Length of received data on Data Exchange        */
    
#if RFAL_FEATURE_NFC_DEP || RFAL_FEATURE_ISO_DEP
    rfalNfcTmpBuffer        tmpBuf;             /*!< Tmp buffer for Data Exchange                    */
#endif /* RFAL_FEATURE_NFC_DEP || RFAL_FEATURE_ISO_DEP */

}rfalNfc;

  
/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */
#ifdef RFAL_TEST_MODE
    rfalNfc gNfcDev;
#else /* RFAL_TEST_MODE */
    static rfalNfc gNfcDev;
#endif /* RFAL_TEST_MODE */

/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/
static ReturnCode rfalNfcPollTechDetection( void );
static ReturnCode rfalNfcPollCollResolution( void );
static ReturnCode rfalNfcPollActivation( uint8_t devIt );
static ReturnCode rfalNfcDeactivation( void );

#if RFAL_FEATURE_NFC_DEP
static ReturnCode rfalNfcNfcDepActivate( rfalNfcDevice *device, rfalNfcDepCommMode commMode, const uint8_t *atrReq, uint16_t atrReqLen );
#endif /* RFAL_FEATURE_NFC_DEP */

#if RFAL_FEATURE_LISTEN_MODE
static ReturnCode rfalNfcListenActivation( void );
#endif /* RFAL_FEATURE_LISTEN_MODE*/


/*******************************************************************************/
ReturnCode rfalNfcInitialize( void )
{
    ReturnCode err;
    
    gNfcDev.state = RFAL_NFC_STATE_NOTINIT;
    
    
#ifdef RFAL_FEATURE_DYNAMIC_ANALOG_CONFIG
    /* Initialize the AC if not already done                                   */
    /* Prevents reseting to default AC table in case another has been loaded   */
    /* meanwhile - For use cases where a dynamic AC is loaded at run time      */
    if( (!rfalAnalogConfigIsReady()) )
#endif /* RFAL_FEATURE_DYNAMIC_ANALOG_CONFIG */
    {
        rfalAnalogConfigInitialize();          /* Initialize RFAL's Analog Configs */
    }
    
    RFAL_EXIT_ON_ERR( err, rfalInitialize() ); /* Initialize RFAL */
    
    RFAL_MEMSET( &gNfcDev, 0x00, sizeof(gNfcDev) );
    
    gNfcDev.state = RFAL_NFC_STATE_IDLE;       /* Go to initialized */
    return RFAL_ERR_NONE;
}

/*******************************************************************************/
ReturnCode rfalNfcDiscover( const rfalNfcDiscoverParam *disParams )
{
    /* Check if initialization has been performed */
    if( gNfcDev.state != RFAL_NFC_STATE_IDLE )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check valid parameters */
    if( (disParams == NULL) || (disParams->devLimit > RFAL_NFC_MAX_DEVICES) || (disParams->devLimit == 0U)                                                 || 
        ( (disParams->maxBR > RFAL_BR_1695) && (disParams->maxBR != RFAL_BR_KEEP) )                                                                        ||
        ( ((disParams->techs2Find & RFAL_NFC_POLL_TECH_F) != 0U)     && (disParams->nfcfBR != RFAL_BR_212) && (disParams->nfcfBR != RFAL_BR_424) )         ||
        ( (((disParams->techs2Find & RFAL_NFC_POLL_TECH_AP2P) != 0U) && (disParams->ap2pBR > RFAL_BR_424)) || (disParams->GBLen > RFAL_NFCDEP_GB_MAX_LEN) )  )
    {
        return RFAL_ERR_PARAM;
    }
    
    if( (((disParams->techs2Find & RFAL_NFC_POLL_TECH_A) != 0U)      && (!((bool)RFAL_FEATURE_NFCA)))    ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_B) != 0U)      && (!((bool)RFAL_FEATURE_NFCB)))    ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_F) != 0U)      && (!((bool)RFAL_FEATURE_NFCF)))    ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_V) != 0U)      && (!((bool)RFAL_FEATURE_NFCV)))    ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_ST25TB) != 0U) && (!((bool)RFAL_FEATURE_ST25TB)))  ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_AP2P) != 0U)   && (!((bool)RFAL_FEATURE_NFC_DEP))) ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_A) != 0U)    && (!((bool)RFAL_FEATURE_NFCA)))    ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_B) != 0U)    && (!((bool)RFAL_FEATURE_NFCB)))    ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_F) != 0U)    && (!((bool)RFAL_FEATURE_NFCF)))    ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_AP2P) != 0U) && (!((bool)RFAL_FEATURE_NFC_DEP)))    )
    {
        return RFAL_ERR_DISABLED;   /*  PRQA S  2880 # MISRA 2.1 - Unreachable code due to configuration option being set/unset  */ 
    }

    if( (((disParams->techs2Find & RFAL_NFC_POLL_TECH_A) != 0U)      && (!((bool)RFAL_SUPPORT_MODE_POLL_NFCA)))         ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_B) != 0U)      && (!((bool)RFAL_SUPPORT_MODE_POLL_NFCB)))         ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_F) != 0U)      && (!((bool)RFAL_SUPPORT_MODE_POLL_NFCF)))         ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_V) != 0U)      && (!((bool)RFAL_SUPPORT_MODE_POLL_NFCV)))         ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_ST25TB) != 0U) && (!((bool)RFAL_SUPPORT_MODE_POLL_NFCB)))         ||
        (((disParams->techs2Find & RFAL_NFC_POLL_TECH_AP2P) != 0U)   && (!((bool)RFAL_SUPPORT_MODE_POLL_ACTIVE_P2P)))   ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_A) != 0U)    && (!((bool)RFAL_SUPPORT_MODE_LISTEN_NFCA)))       ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_B) != 0U)    && (!((bool)RFAL_SUPPORT_MODE_LISTEN_NFCB)))       ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_F) != 0U)    && (!((bool)RFAL_SUPPORT_MODE_LISTEN_NFCF)))       ||
        (((disParams->techs2Find & RFAL_NFC_LISTEN_TECH_AP2P) != 0U) && (!((bool)RFAL_SUPPORT_MODE_LISTEN_ACTIVE_P2P)))    )
    {
        return RFAL_ERR_NOTSUPP;   /*  PRQA S  2880 # MISRA 2.1 - Unreachable code due to configuration option being set/unset  */ 
    }
    
    /* Initialize context for discovery */
    gNfcDev.activeDev       = NULL;
    gNfcDev.techsFound      = RFAL_NFC_TECH_NONE;
    gNfcDev.techDctCnt      = 0;
    gNfcDev.devCnt          = 0;
    gNfcDev.deactType       = RFAL_NFC_DEACTIVATE_DISCOVERY;
    gNfcDev.isTechInit      = false;
    gNfcDev.isFieldOn       = false;
    gNfcDev.isDeactivating  = false;
    gNfcDev.disc            = *disParams;
    
    
    /* Calculate Listen Mask */
    gNfcDev.lmMask  = 0U;
    gNfcDev.lmMask |= (((gNfcDev.disc.techs2Find & RFAL_NFC_LISTEN_TECH_A) != 0U) ? RFAL_LM_MASK_NFCA : 0U);
    gNfcDev.lmMask |= (((gNfcDev.disc.techs2Find & RFAL_NFC_LISTEN_TECH_B) != 0U) ? RFAL_LM_MASK_NFCB : 0U);
    gNfcDev.lmMask |= (((gNfcDev.disc.techs2Find & RFAL_NFC_LISTEN_TECH_F) != 0U) ? RFAL_LM_MASK_NFCF : 0U);
    gNfcDev.lmMask |= (((gNfcDev.disc.techs2Find & RFAL_NFC_LISTEN_TECH_AP2P) != 0U) ? RFAL_LM_MASK_ACTIVE_P2P : 0U);
    
#if !RFAL_FEATURE_LISTEN_MODE
    /* Check if Listen Mode is supported/Enabled */
    if( gNfcDev.lmMask != 0U )
    {
        return RFAL_ERR_DISABLED;
    }
#endif
    
    gNfcDev.state = RFAL_NFC_STATE_START_DISCOVERY;
    
    return RFAL_ERR_NONE;
}

/*******************************************************************************/
ReturnCode rfalNfcDeactivate( rfalNfcDeactivateType deactType )
{
    ReturnCode ret;

    /* Check for valid state */
    if( (gNfcDev.state <= RFAL_NFC_STATE_IDLE) || ((deactType == RFAL_NFC_DEACTIVATE_SLEEP) && ((gNfcDev.state < RFAL_NFC_STATE_ACTIVATED) || (gNfcDev.activeDev == NULL))) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check valid paramters for the deactivation types */
    if( ( (deactType == RFAL_NFC_DEACTIVATE_SLEEP) && rfalNfcIsRemDevPoller(gNfcDev.activeDev->type) )       || 
        ( (deactType == RFAL_NFC_DEACTIVATE_DISCOVERY)  && (gNfcDev.disc.techs2Find == RFAL_NFC_TECH_NONE) )    )
    {
        return RFAL_ERR_PARAM;
    }

    gNfcDev.deactType = deactType;
    
    /* Check if Discovery is to continue afterwards or back to Select */
    if( (deactType == RFAL_NFC_DEACTIVATE_DISCOVERY) || (deactType == RFAL_NFC_DEACTIVATE_SLEEP) )
    {
        /* If so let the state machine continue*/
        gNfcDev.state     = RFAL_NFC_STATE_DEACTIVATION;
    }
    else
    {
        /* Otherwise deactivate immediately and go to IDLE */
        rfalRunBlocking( ret, rfalNfcDeactivation() );
        gNfcDev.state = RFAL_NFC_STATE_IDLE;
    }
    
    return RFAL_ERR_NONE;
}

/*******************************************************************************/
ReturnCode rfalNfcSelect( uint8_t devIdx )
{
    /* Check for valid state */
    if( gNfcDev.state != RFAL_NFC_STATE_POLL_SELECT )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    gNfcDev.isTechInit = false;
    gNfcDev.selDevIdx  = devIdx;
    gNfcDev.state      = RFAL_NFC_STATE_POLL_ACTIVATION;
    
    return RFAL_ERR_NONE;
}

/*******************************************************************************/
rfalNfcState rfalNfcGetState( void )
{
    return gNfcDev.state;
}

/*******************************************************************************/
ReturnCode rfalNfcGetDevicesFound( rfalNfcDevice **devList, uint8_t *devCnt )
{
    /* Check for valid state */
    if( gNfcDev.state < RFAL_NFC_STATE_POLL_SELECT )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check valid parameters */
    if( (devList == NULL) || (devCnt == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    *devCnt  = gNfcDev.devCnt;
    *devList = gNfcDev.devList;
    
    return RFAL_ERR_NONE;
}

/*******************************************************************************/
ReturnCode rfalNfcGetActiveDevice( rfalNfcDevice **dev )
{
    /* Check for valid state */
    if( gNfcDev.state < RFAL_NFC_STATE_ACTIVATED )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check valid parameter */
    if( dev == NULL )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Check for valid state */
    if( (gNfcDev.devCnt == 0U) || (gNfcDev.activeDev == NULL)  )
    {
        return RFAL_ERR_REQUEST;
    }
    
    *dev = gNfcDev.activeDev;
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
void rfalNfcWorker( void )
{
    ReturnCode err;
   
    rfalWorker();                                                                     /* Execute RFAL process  */
    
    switch( gNfcDev.state )
    {   
        /*******************************************************************************/
        case RFAL_NFC_STATE_NOTINIT:                            
        case RFAL_NFC_STATE_IDLE:                               
            break;
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_START_DISCOVERY:
        
            /* Initialize context for discovery cycle */
            gNfcDev.devCnt         = 0;
            gNfcDev.selDevIdx      = 0;
            RFAL_MEMSET( gNfcDev.devList, 0x00, sizeof(gNfcDev.devList) );
            gNfcDev.techsFound     = RFAL_NFC_TECH_NONE;
            gNfcDev.techs2do       = gNfcDev.disc.techs2Find;
            gNfcDev.state          = RFAL_NFC_STATE_POLL_TECHDETECT;
            gNfcDev.isDeactivating = false;
        
            /* Start total duration timer */
            platformTimerDestroy( gNfcDev.discTmr );
            gNfcDev.discTmr = (uint32_t)platformTimerCreate( gNfcDev.disc.totalDuration );
        
        #if RFAL_FEATURE_WAKEUP_MODE    
            /* Check if Low power Wake-Up is to be performed */
            if( (gNfcDev.disc.wakeupEnabled) && ( ((gNfcDev.techDctCnt == 0U) && (gNfcDev.disc.wakeupPollBefore == false)) || (gNfcDev.techDctCnt >= gNfcDev.disc.wakeupNPolls)) )
            {
                /* Initialize Low power Wake-up mode and wait */
                err = rfalWakeUpModeStart( (gNfcDev.disc.wakeupConfigDefault ? NULL : &gNfcDev.disc.wakeupConfig) );
                if( err == RFAL_ERR_NONE )
                {
                    gNfcDev.state = RFAL_NFC_STATE_WAKEUP_MODE;
                }
            }
            gNfcDev.techDctCnt++;
            
        #endif /* RFAL_FEATURE_WAKEUP_MODE */
            
            rfalNfcNfcNotify( gNfcDev.state );                                /* Notify caller that WU or Technology Detection has started  */
            break;
        
        /*******************************************************************************/
        case RFAL_NFC_STATE_WAKEUP_MODE:
            
    #if RFAL_FEATURE_WAKEUP_MODE
            /* Check if the Wake-up mode has woke */
            if( rfalWakeUpModeHasWoke() )
            {
                rfalWakeUpModeStop();                                                 /* Disable Wake-up mode           */
                gNfcDev.state      = RFAL_NFC_STATE_POLL_TECHDETECT;                  /* Go to Technology detection     */
                gNfcDev.techDctCnt = 1;                                               /* Tech Detect counter (1 woke)   */
                
                /* (Re)Start total duration timer upon waking up */
                platformTimerDestroy( gNfcDev.discTmr );
                gNfcDev.discTmr = (uint32_t)platformTimerCreate( gNfcDev.disc.totalDuration );
                
                rfalNfcNfcNotify( gNfcDev.state );                                    /* Notify caller that WU has woke */
            }
    #endif /* RFAL_FEATURE_WAKEUP_MODE */

            break;
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_POLL_TECHDETECT:
        
            err = rfalNfcPollTechDetection();                                       /* Perform Technology Detection                         */
            if( err != RFAL_ERR_BUSY )                                                /* Wait until all technologies are performed            */
            {
                if( ( err != RFAL_ERR_NONE) || (gNfcDev.techsFound == RFAL_NFC_TECH_NONE) )/* Check if any error occurred or no techs were found   */
                {
                    rfalFieldOff();
                    gNfcDev.isFieldOn = false;
                    gNfcDev.state     = RFAL_NFC_STATE_LISTEN_TECHDETECT;             /* Nothing found as poller, go to listener */
                    break;
                }
                
                gNfcDev.techs2do = gNfcDev.techsFound;                                /* Store the found technologies for collision resolution */
                gNfcDev.state    = RFAL_NFC_STATE_POLL_COLAVOIDANCE;                  /* One or more devices found, go to Collision Avoidance  */
            }
            break;
            
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_POLL_COLAVOIDANCE:
        
            err = rfalNfcPollCollResolution();                                        /* Resolve any eventual collision                       */
            if( err != RFAL_ERR_BUSY )                                                /* Wait until all technologies are performed            */
            {
                if( (err != RFAL_ERR_NONE) || (gNfcDev.devCnt == 0U) )                /* Check if any error occurred or no devices were found */
                {
                    gNfcDev.deactType = RFAL_NFC_DEACTIVATE_DISCOVERY;
                    gNfcDev.state     = RFAL_NFC_STATE_DEACTIVATION;
                    break;                                                            /* Unable to retrieve any device, restart loop          */
                }
                
                /* Check if more than one device has been found */
                if( gNfcDev.devCnt > 1U )
                {
                    /* If more than one device was found inform upper layer to choose which one to activate */
                    if( gNfcDev.disc.notifyCb != NULL )
                    {
                        gNfcDev.state = RFAL_NFC_STATE_POLL_SELECT;
                        gNfcDev.disc.notifyCb( gNfcDev.state );
                        break;
                    }
                }
                
                /* If only one device or no callback has been set, activate the first device found */
                gNfcDev.selDevIdx = 0U;
                gNfcDev.state = RFAL_NFC_STATE_POLL_ACTIVATION;
            }
            break;
        
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_POLL_ACTIVATION:
            
            err = rfalNfcPollActivation( gNfcDev.selDevIdx );
            if( err != RFAL_ERR_BUSY )                                                     /* Wait until all Activation is complete */
            {
                if( err != RFAL_ERR_NONE )                                                 /* Check if activation has failed        */
                {
                    /* Check if more than one device has been found */
                    if( (gNfcDev.devCnt > 1U) && (gNfcDev.disc.notifyCb != NULL) )
                    {
                        gNfcDev.state = RFAL_NFC_STATE_POLL_SELECT;
                        rfalNfcNfcNotify( gNfcDev.state );
                        break;
                    }
                    
                    gNfcDev.deactType = RFAL_NFC_DEACTIVATE_DISCOVERY;                /* Ensure deactivation, not Sleep        */
                    gNfcDev.state     = RFAL_NFC_STATE_DEACTIVATION;                  /* If Activation failed, restart loop    */
                    break;
                }
                
                gNfcDev.state = RFAL_NFC_STATE_ACTIVATED;                             /* Device has been properly activated    */
                rfalNfcNfcNotify( gNfcDev.state );                                    /* Inform upper layer that a device has been activated */
            }
            break;
            
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_DATAEXCHANGE:

            rfalNfcDataExchangeGetStatus();                                           /* Run the internal state machine */
            
            if( gNfcDev.dataExErr != RFAL_ERR_BUSY )                                  /* If Dataexchange has terminated */
            {
                gNfcDev.state = RFAL_NFC_STATE_DATAEXCHANGE_DONE;                     /* Go to done state               */
                rfalNfcNfcNotify( gNfcDev.state );                                    /* And notify caller              */
            }
            if( gNfcDev.dataExErr == RFAL_ERR_SLEEP_REQ )                             /* Check if Listen mode has to go to Sleep */
            {
                gNfcDev.state = RFAL_NFC_STATE_LISTEN_SLEEP;                          /* Go to Listen Sleep state       */
                rfalNfcNfcNotify( gNfcDev.state );                                    /* And notify caller              */
            }
            break;
            
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_DEACTIVATION:
            
            err = rfalNfcDeactivation();                                              /* Deactivate current device */
            if( err != RFAL_ERR_BUSY )
            {
                if( gNfcDev.deactType == RFAL_NFC_DEACTIVATE_SLEEP )
                {
                    gNfcDev.state = RFAL_NFC_STATE_POLL_SELECT;
                }
                else
                {
                    gNfcDev.state = ( (gNfcDev.deactType == RFAL_NFC_DEACTIVATE_DISCOVERY) ? RFAL_NFC_STATE_START_DISCOVERY : RFAL_NFC_STATE_IDLE );
                }
                
                rfalNfcNfcNotify( gNfcDev.state );                                        /* Notify caller             */
            }
            break;
        
        /*******************************************************************************/
        case RFAL_NFC_STATE_LISTEN_TECHDETECT:
            
            if( platformTimerIsExpired( gNfcDev.discTmr ) )
            {
                #if RFAL_FEATURE_LISTEN_MODE
                    rfalListenStop();
                #else
                    rfalFieldOff();
                #endif /* RFAL_FEATURE_LISTEN_MODE */
                gNfcDev.isFieldOn = false;
                
                gNfcDev.state = RFAL_NFC_STATE_START_DISCOVERY;                       /* Restart the discovery loop */
                rfalNfcNfcNotify( gNfcDev.state );                                    /* Notify caller             */
                break;
            }

    #if RFAL_FEATURE_LISTEN_MODE
            
            if( gNfcDev.lmMask != 0U )                                                /* Check if configured to perform Listen mode */
            {
                err = rfalListenStart( gNfcDev.lmMask, &gNfcDev.disc.lmConfigPA, NULL, &gNfcDev.disc.lmConfigPF, (uint8_t*)&gNfcDev.rxBuf.rfBuf, (uint16_t)rfalConvBytesToBits(sizeof(gNfcDev.rxBuf.rfBuf)), &gNfcDev.rxLen );
                if( err == RFAL_ERR_NONE )
                {
                    gNfcDev.state = RFAL_NFC_STATE_LISTEN_COLAVOIDANCE;               /* Wait for listen mode to be activated */
                }
            }
            break;
        
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_LISTEN_COLAVOIDANCE:
            
            if( platformTimerIsExpired( gNfcDev.discTmr ) )                           /* Check if the total duration has been reached */
            {
                rfalListenStop();
                gNfcDev.state = RFAL_NFC_STATE_START_DISCOVERY;                       /* Restart the discovery loop */
                rfalNfcNfcNotify( gNfcDev.state );                                    /* Notify caller             */
                break;
            }
            
            /* Check for external field */
            if( rfalListenGetState( NULL, NULL ) >= RFAL_LM_STATE_IDLE )
            {
                gNfcDev.state = RFAL_NFC_STATE_LISTEN_ACTIVATION;                     /* Wait for listen mode to be activated */
            }
            break;
            
        
        /*******************************************************************************/    
        case RFAL_NFC_STATE_LISTEN_ACTIVATION:
        case RFAL_NFC_STATE_LISTEN_SLEEP:
            
            err = rfalNfcListenActivation();
            if( err != RFAL_ERR_BUSY )
            {
                if( err == RFAL_ERR_NONE )
                {
                    gNfcDev.activeDev = gNfcDev.devList;                              /* Assign the active device to be used further on */
                    gNfcDev.devCnt++;
                    
                    gNfcDev.state = RFAL_NFC_STATE_ACTIVATED;                         /* Device has been properly activated */
                    rfalNfcNfcNotify( gNfcDev.state );                                /* Inform upper layer that a device has been activated */
                }
                else if( (!platformTimerIsExpired( gNfcDev.discTmr )) && (err == RFAL_ERR_LINK_LOSS) && (gNfcDev.state == RFAL_NFC_STATE_LISTEN_ACTIVATION) )
                {
                    break;                                                            /* Field|Link broken during activation, keep in Listen the remaining total duration */
                }
                else
                {
                    rfalListenStop();
                    gNfcDev.state = RFAL_NFC_STATE_START_DISCOVERY;                   /* Restart the discovery loop */
                    rfalNfcNfcNotify( gNfcDev.state );                                /* Notify caller             */
                }
            }
    #endif /* RFAL_FEATURE_LISTEN_MODE */
            break;
            
        /*******************************************************************************/
        case RFAL_NFC_STATE_ACTIVATED:
        case RFAL_NFC_STATE_POLL_SELECT:
        case RFAL_NFC_STATE_DATAEXCHANGE_DONE:
        default:
            return;
    }
}


/*******************************************************************************/
ReturnCode rfalNfcDataExchangeStart( uint8_t *txData, uint16_t txDataLen, uint8_t **rxData, uint16_t **rvdLen, uint32_t fwt )
{
    ReturnCode            err;
    rfalTransceiveContext ctx;
    
    /*******************************************************************************/
    /* The Data Exchange is divided in two different moments, the trigger/Start of *
     *  the transfer followed by the check until its completion                    */
    if( (gNfcDev.state >= RFAL_NFC_STATE_ACTIVATED) && (gNfcDev.activeDev != NULL) )
    {
        
        /*******************************************************************************/
        /* In Listen mode is the Poller that initiates the communicatation             */
        /* Assign output parameters and rfalNfcDataExchangeGetStatus will return       */
        /* incoming data from Poller/Initiator                                         */
        if( (gNfcDev.state == RFAL_NFC_STATE_ACTIVATED) && rfalNfcIsRemDevPoller( gNfcDev.activeDev->type ) )
        {
            if( txDataLen > 0U )
            {
                return RFAL_ERR_WRONG_STATE;
            }
            
            *rvdLen = (uint16_t*)&gNfcDev.rxLen;
            *rxData = (uint8_t*)(  (gNfcDev.activeDev->rfInterface == RFAL_NFC_INTERFACE_ISODEP) ? gNfcDev.rxBuf.isoDepBuf.apdu : 
                                  ((gNfcDev.activeDev->rfInterface == RFAL_NFC_INTERFACE_NFCDEP) ? gNfcDev.rxBuf.nfcDepBuf.pdu  : gNfcDev.rxBuf.rfBuf));
            return RFAL_ERR_NONE;
        }
        
        
        /*******************************************************************************/
        switch( gNfcDev.activeDev->rfInterface )                                      /* Check which RF interface shall be used/has been activated */
        {
            /*******************************************************************************/
            case RFAL_NFC_INTERFACE_RF:
    
                rfalCreateByteFlagsTxRxContext( ctx, (uint8_t*)txData, txDataLen, gNfcDev.rxBuf.rfBuf, sizeof(gNfcDev.rxBuf.rfBuf), &gNfcDev.rxLen, RFAL_TXRX_FLAGS_DEFAULT, fwt );
                ctx.txBufLen = txDataLen;    /* RF interface uses number of bits */
            
                *rxData = (uint8_t*)gNfcDev.rxBuf.rfBuf;
                *rvdLen = (uint16_t*)&gNfcDev.rxLen;
                err = rfalStartTransceive( &ctx );
                break;
                
        #if RFAL_FEATURE_ISO_DEP
            /*******************************************************************************/
            case RFAL_NFC_INTERFACE_ISODEP:
            {
                rfalIsoDepApduTxRxParam rfalIsoDepTxRx;
                
                if( txDataLen > sizeof(gNfcDev.txBuf.isoDepBuf.apdu) )
                {
                    return RFAL_ERR_NOMEM;
                }
                
                if( txDataLen > 0U )
                {
                    RFAL_MEMCPY( (uint8_t*)gNfcDev.txBuf.isoDepBuf.apdu, txData, txDataLen );
                }
                
                rfalIsoDepTxRx.DID       = RFAL_ISODEP_NO_DID;
                rfalIsoDepTxRx.ourFSx    = RFAL_ISODEP_FSX_KEEP;
                rfalIsoDepTxRx.FSx       = gNfcDev.activeDev->proto.isoDep.info.FSx;
                rfalIsoDepTxRx.dFWT      = gNfcDev.activeDev->proto.isoDep.info.dFWT;
                rfalIsoDepTxRx.FWT       = gNfcDev.activeDev->proto.isoDep.info.FWT;
                rfalIsoDepTxRx.txBuf     = &gNfcDev.txBuf.isoDepBuf;
                rfalIsoDepTxRx.txBufLen  = txDataLen;
                rfalIsoDepTxRx.rxBuf     = &gNfcDev.rxBuf.isoDepBuf;
                rfalIsoDepTxRx.rxLen     = &gNfcDev.rxLen;
                rfalIsoDepTxRx.tmpBuf    = &gNfcDev.tmpBuf.isoDepBuf;
                *rxData                  = (uint8_t*)gNfcDev.rxBuf.isoDepBuf.apdu;
                *rvdLen                  = (uint16_t*)&gNfcDev.rxLen;
                
                /*******************************************************************************/
                /* Trigger a RFAL ISO-DEP Transceive                                           */
                err = rfalIsoDepStartApduTransceive( rfalIsoDepTxRx );
                break;
            }
        #endif /* RFAL_FEATURE_ISO_DEP */
                
        #if RFAL_FEATURE_NFC_DEP
            /*******************************************************************************/
            case RFAL_NFC_INTERFACE_NFCDEP:
            {
                rfalNfcDepPduTxRxParam rfalNfcDepTxRx;
                
                if( txDataLen > sizeof(gNfcDev.txBuf.nfcDepBuf.pdu) )
                {
                    return RFAL_ERR_NOMEM;
                }
                
                if( txDataLen > 0U)
                {
                    RFAL_MEMCPY( (uint8_t*)gNfcDev.txBuf.nfcDepBuf.pdu, txData, txDataLen );
                }
                
                rfalNfcDepTxRx.DID       = RFAL_NFCDEP_DID_KEEP;
                rfalNfcDepTxRx.FSx       = rfalNfcIsRemDevListener(gNfcDev.activeDev->type) ?
                                           rfalNfcDepLR2FS( (uint8_t)rfalNfcDepPP2LR( gNfcDev.activeDev->proto.nfcDep.activation.Target.ATR_RES.PPt ) ) :
                                           rfalNfcDepLR2FS( (uint8_t)rfalNfcDepPP2LR( gNfcDev.activeDev->proto.nfcDep.activation.Initiator.ATR_REQ.PPi ) );
                rfalNfcDepTxRx.dFWT      = gNfcDev.activeDev->proto.nfcDep.info.dFWT;
                rfalNfcDepTxRx.FWT       = gNfcDev.activeDev->proto.nfcDep.info.FWT;
                rfalNfcDepTxRx.txBuf     = &gNfcDev.txBuf.nfcDepBuf;
                rfalNfcDepTxRx.txBufLen  = txDataLen;
                rfalNfcDepTxRx.rxBuf     = &gNfcDev.rxBuf.nfcDepBuf;
                rfalNfcDepTxRx.rxLen     = &gNfcDev.rxLen;
                rfalNfcDepTxRx.tmpBuf    = &gNfcDev.tmpBuf.nfcDepBuf;
                *rxData                  = (uint8_t*)gNfcDev.rxBuf.nfcDepBuf.pdu;
                *rvdLen                  = (uint16_t*)&gNfcDev.rxLen;
                
                /*******************************************************************************/
                /* Trigger a RFAL NFC-DEP Transceive                                           */
                err = rfalNfcDepStartPduTransceive( rfalNfcDepTxRx );                          
                break;
            }
        #endif /* RFAL_FEATURE_NFC_DEP */

            /*******************************************************************************/
            default:
                err = RFAL_ERR_PARAM;
                break;
        }
        
        /* If a transceive has succesfully started flag Data Exchange as ongoing */
        if( err == RFAL_ERR_NONE )
        {
            gNfcDev.dataExErr = RFAL_ERR_BUSY;
            gNfcDev.state     = RFAL_NFC_STATE_DATAEXCHANGE;
        }
        
        return err;
    }
    
    return RFAL_ERR_WRONG_STATE;
}


/*******************************************************************************/
ReturnCode rfalNfcDataExchangeGetStatus( void )
{
    /*******************************************************************************/
    /* Check if it's the first frame received in Listen mode */
    if( gNfcDev.state == RFAL_NFC_STATE_ACTIVATED )
    {
        /* Continue data exchange as normal */
        gNfcDev.dataExErr = RFAL_ERR_BUSY;
        gNfcDev.state     = RFAL_NFC_STATE_DATAEXCHANGE;
        
        /* Check if we performing in T3T CE */
        if( (gNfcDev.activeDev->type == RFAL_NFC_POLL_TYPE_NFCF) && (gNfcDev.activeDev->rfInterface == RFAL_NFC_INTERFACE_RF) )
        {
            /* The first frame has been retrieved by rfalListenMode, flag data immediately                  */
            /* Can only call rfalGetTransceiveStatus() after starting a transceive with rfalStartTransceive */
            gNfcDev.dataExErr = RFAL_ERR_NONE;
        }
    }
    
    
    /*******************************************************************************/
    /* Check if we are in we have been placed to sleep, and return last error     */
    if( gNfcDev.state == RFAL_NFC_STATE_LISTEN_SLEEP )
    {
        return gNfcDev.dataExErr;                                /* RFAL_ERR_SLEEP_REQ */
    }

    
    /*******************************************************************************/    
    /* Check if Data exchange has been started */
    if( (gNfcDev.state != RFAL_NFC_STATE_DATAEXCHANGE) && (gNfcDev.state != RFAL_NFC_STATE_DATAEXCHANGE_DONE) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Check if Data exchange is still ongoing */
    if( gNfcDev.dataExErr == RFAL_ERR_BUSY )
    {
        switch( gNfcDev.activeDev->rfInterface )
        {
            /*******************************************************************************/
            case RFAL_NFC_INTERFACE_RF:
                gNfcDev.dataExErr = rfalGetTransceiveStatus();
                break;
        
        #if RFAL_FEATURE_ISO_DEP
            /*******************************************************************************/
            case RFAL_NFC_INTERFACE_ISODEP:
                gNfcDev.dataExErr = rfalIsoDepGetApduTransceiveStatus();
                break;
        #endif /* RFAL_FEATURE_ISO_DEP */
                
            /*******************************************************************************/
        #if RFAL_FEATURE_NFC_DEP
            case RFAL_NFC_INTERFACE_NFCDEP:
                gNfcDev.dataExErr = rfalNfcDepGetPduTransceiveStatus();
                break;
        #endif /* RFAL_FEATURE_NFC_DEP */
                
            /*******************************************************************************/
            default:
                gNfcDev.dataExErr = RFAL_ERR_PARAM;
                break;
        }
        
    #if  RFAL_FEATURE_LISTEN_MODE
        /*******************************************************************************/
        /* If a Sleep request has been received (Listen Mode) go to sleep immediately  */
        if( gNfcDev.dataExErr == RFAL_ERR_SLEEP_REQ )
        {
            RFAL_EXIT_ON_ERR( gNfcDev.dataExErr, rfalListenSleepStart( RFAL_LM_STATE_SLEEP_A, gNfcDev.rxBuf.rfBuf, sizeof(gNfcDev.rxBuf.rfBuf), &gNfcDev.rxLen ) );
            
            /* If set Sleep was succesfull keep restore the Sleep request signal */
            gNfcDev.dataExErr = RFAL_ERR_SLEEP_REQ;
        }
    #endif /* RFAL_FEATURE_LISTEN_MODE */
        
    }
    
    return gNfcDev.dataExErr;
}

/*!
 ******************************************************************************
 * \brief Poller Technology Detection
 * 
 * This method implements the Technology Detection / Poll for different 
 * device technologies.
 * 
 * \return  RFAL_ERR_NONE         : Operation completed with no error
 * \return  RFAL_ERR_BUSY         : Operation ongoing
 * \return  RFAL_ERR_XXXX         : Error occurred
 * 
 ******************************************************************************
 */
static ReturnCode rfalNfcPollTechDetection( void )
{
    ReturnCode err;
    
    err = RFAL_ERR_NONE;
    
    /* Suppress warning when specific RFAL features have been disabled */
    RFAL_NO_WARNING(err);   
    
    
    /*******************************************************************************/
    /* AP2P Technology Detection                                                   */
    /*******************************************************************************/
    if( ((gNfcDev.disc.techs2Find & RFAL_NFC_POLL_TECH_AP2P) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_AP2P) != 0U) )
    {
        
    #if RFAL_FEATURE_NFC_DEP
    
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalSetMode( RFAL_MODE_POLL_ACTIVE_P2P, gNfcDev.disc.ap2pBR, gNfcDev.disc.ap2pBR ) );
            rfalSetErrorHandling( RFAL_ERRORHANDLING_NONE );
            rfalSetFDTListen( RFAL_FDT_LISTEN_AP2P_POLLER );
            rfalSetFDTPoll( RFAL_FDT_POLL_AP2P_POLLER );
            rfalSetGT( RFAL_GT_AP2P_ADJUSTED );
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                                /* Turns the Field On and starts GT timer */
            gNfcDev.isTechInit = true;
        }
        
        if( rfalIsGTExpired() )                                                              /* Wait until Guard Time is fulfilled */
        {
            gNfcDev.techs2do &= ~RFAL_NFC_POLL_TECH_AP2P;
            
            err = rfalNfcNfcDepActivate( gNfcDev.devList, RFAL_NFCDEP_COMM_ACTIVE, NULL, 0 );/* Poll for AP2P devices */
            if( err == RFAL_ERR_NONE )
            {
                gNfcDev.techsFound |= RFAL_NFC_POLL_TECH_AP2P;
                
                gNfcDev.devList->type        = RFAL_NFC_LISTEN_TYPE_AP2P;
                gNfcDev.devList->rfInterface = RFAL_NFC_INTERFACE_NFCDEP;
                gNfcDev.devCnt++;
                
                return RFAL_ERR_NONE;
            }
            
            gNfcDev.isTechInit = false;
            rfalFieldOff();
        }
        return RFAL_ERR_BUSY;
        
    #endif /* RFAL_FEATURE_NFC_DEP */
    }
    
    
    /*******************************************************************************/
    /* Turn Field On if Passive Poll technologies are enabled                      */
    /*******************************************************************************/
    if( (!gNfcDev.isFieldOn) && ( (gNfcDev.disc.techs2Find & (RFAL_NFC_POLL_TECH_A | RFAL_NFC_POLL_TECH_B | RFAL_NFC_POLL_TECH_F | RFAL_NFC_POLL_TECH_V | RFAL_NFC_POLL_TECH_ST25TB | RFAL_NFC_POLL_TECH_PROP)) != 0U) )
    {
        RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                              /* Turns the Field On  */
        gNfcDev.isFieldOn = true;
        return RFAL_ERR_BUSY;
    }

    
    /*******************************************************************************/
    /* Passive NFC-A Technology Detection                                          */
    /*******************************************************************************/
    if( ((gNfcDev.disc.techs2Find & RFAL_NFC_POLL_TECH_A) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_A) != 0U) )
    {
        
    #if RFAL_FEATURE_NFCA
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcaPollerInitialize() );                       /* Initialize RFAL for NFC-A */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                          /* As field is already On only starts GT timer */
            gNfcDev.isTechInit    = true;
            gNfcDev.isOperOngoing = false;                                             /* No operation currently ongoing  */
        }
        
        if( rfalIsGTExpired() )                                                        /* Wait until Guard Time is fulfilled */
        {
            if( !gNfcDev.isOperOngoing )
            {
                rfalNfcaPollerStartTechnologyDetection( gNfcDev.disc.compMode, &gNfcDev.sensRes );/* Poll for NFC-A devices */
             
                gNfcDev.isOperOngoing = true;
                return RFAL_ERR_BUSY;
            }
            
            err = rfalNfcaPollerGetTechnologyDetectionStatus();
            if( err != RFAL_ERR_BUSY )
            {
                if( err == RFAL_ERR_NONE )
                {
                    gNfcDev.techsFound |= RFAL_NFC_POLL_TECH_A;
                }
                
                gNfcDev.isTechInit = false;
                gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_A;
            }
            
            /* Check if bail-out after NFC-A     Activity 2.1  9.2.3.21 */
            if( ((gNfcDev.disc.techs2Bail & RFAL_NFC_POLL_TECH_A) != 0U) && (gNfcDev.techsFound != 0U) )
            {
                return RFAL_ERR_NONE;
            }
        }
    
        return RFAL_ERR_BUSY;

    #endif /* RFAL_FEATURE_NFCA */
    }
    
    
    /*******************************************************************************/
    /* Passive NFC-B Technology Detection                                          */
    /*******************************************************************************/
    if( ((gNfcDev.disc.techs2Find & RFAL_NFC_POLL_TECH_B) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_B) != 0U) )
    {
    #if RFAL_FEATURE_NFCB
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcbPollerInitialize() );                      /* Initialize RFAL for NFC-B */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                         /* As field is already On only starts GT timer */
            gNfcDev.isTechInit    = true;
            gNfcDev.isOperOngoing = false;                                            /* No operation currently ongoing  */
        }
        
        if( rfalIsGTExpired() )                                                       /* Wait until Guard Time is fulfilled */
        {
            
            if( !gNfcDev.isOperOngoing )
            {
                rfalNfcbPollerStartTechnologyDetection( gNfcDev.disc.compMode, &gNfcDev.sensbRes, &gNfcDev.sensbResLen );/* Poll for NFC-B devices */
             
                gNfcDev.isOperOngoing = true;
                return RFAL_ERR_BUSY;
            }
            
            err = rfalNfcbPollerGetTechnologyDetectionStatus();
            if( err != RFAL_ERR_BUSY )
            {
                if( err == RFAL_ERR_NONE )
                {
                    gNfcDev.techsFound |= RFAL_NFC_POLL_TECH_B;
                }
                
                gNfcDev.isTechInit = false;
                gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_B;
            }
            
            /* Check if bail-out after NFC-B     Activity 2.1  9.2.3.26 */
            if( ((gNfcDev.disc.techs2Bail & RFAL_NFC_POLL_TECH_B) != 0U) && (gNfcDev.techsFound != 0U) )
            {
                return RFAL_ERR_NONE;
            }
        }        
        
        return RFAL_ERR_BUSY;
    
    #endif /* RFAL_FEATURE_NFCB */
    }
    
    /*******************************************************************************/
    /* Passive NFC-F Technology Detection                                          */
    /*******************************************************************************/
    if( ((gNfcDev.disc.techs2Find & RFAL_NFC_POLL_TECH_F) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_F) != 0U) )
    {
    #if RFAL_FEATURE_NFCF
     
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcfPollerInitialize( gNfcDev.disc.nfcfBR ) );/* Initialize RFAL for NFC-F */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                        /* As field is already On only starts GT timer */
            
            gNfcDev.isTechInit    = true;
            gNfcDev.isOperOngoing = false;                                           /* No operation currently ongoing  */
        }

        if( rfalIsGTExpired() )                                                      /* Wait until Guard Time is fulfilled */
        {
            
            if( !gNfcDev.isOperOngoing )
            {
                rfalNfcfPollerStartCheckPresence();
             
                gNfcDev.isOperOngoing = true;
                return RFAL_ERR_BUSY;
            }
            
            err = rfalNfcfPollerGetCheckPresenceStatus();                            /* Poll for NFC-F devices */
            if( err != RFAL_ERR_BUSY )
            {
                if( err == RFAL_ERR_NONE )
                {
                    gNfcDev.techsFound |= RFAL_NFC_POLL_TECH_F;
                }
                
                gNfcDev.isTechInit = false;
                gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_F;
            }
            
            /* Check if bail-out after NFC-F     Activity 2.1  9.2.3.31 */
            if( ((gNfcDev.disc.techs2Bail & RFAL_NFC_POLL_TECH_F) != 0U) && (gNfcDev.techsFound != 0U) )
            {
                return RFAL_ERR_NONE;
            }
        }
        
        return RFAL_ERR_BUSY;
    
    #endif /* RFAL_FEATURE_NFCF */
    }
    
    
    /*******************************************************************************/
    /* Passive NFC-V Technology Detection                                          */
    /*******************************************************************************/
    if( ((gNfcDev.disc.techs2Find & RFAL_NFC_POLL_TECH_V) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_V) != 0U) )
    {
    #if RFAL_FEATURE_NFCV
        
        rfalNfcvInventoryRes invRes;
 
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcvPollerInitialize() );                      /* Initialize RFAL for NFC-V */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                         /* As field is already On only starts GT timer */
            gNfcDev.isTechInit = true;
        }
                
        if( rfalIsGTExpired() )                                                       /* Wait until Guard Time is fulfilled */
        {
            err = rfalNfcvPollerCheckPresence( &invRes );                             /* Poll for NFC-V devices */
            if( err == RFAL_ERR_NONE )
            {
                gNfcDev.techsFound |= RFAL_NFC_POLL_TECH_V;
            }
            
            gNfcDev.isTechInit = false;
            gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_V;
        }
        
        return RFAL_ERR_BUSY;
    
    #endif /* RFAL_FEATURE_NFCV */
    }
    
    
    /*******************************************************************************/
    /* Passive Proprietary Technology ST25TB                                       */
    /*******************************************************************************/  
    if( ((gNfcDev.disc.techs2Find & RFAL_NFC_POLL_TECH_ST25TB) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_ST25TB) != 0U) )
    {
    #if RFAL_FEATURE_ST25TB
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalSt25tbPollerInitialize() );                    /* Initialize RFAL for NFC-V */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                         /* As field is already On only starts GT timer */
            gNfcDev.isTechInit = true;
        }
     
        if( rfalIsGTExpired() )                                                       /* Wait until Guard Time is fulfilled */
        {
            err = rfalSt25tbPollerCheckPresence( NULL );                              /* Poll for ST25TB devices */
            if( err == RFAL_ERR_NONE )
            {
                gNfcDev.techsFound |= RFAL_NFC_POLL_TECH_ST25TB;
            }
            
            gNfcDev.isTechInit = false;
            gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_ST25TB;
        }
        
        return RFAL_ERR_BUSY;
        
    #endif /* RFAL_FEATURE_ST25TB */
    }
    
    /*******************************************************************************/
    /* Passive Proprietary Technology                                              */
    /*******************************************************************************/  
    if( ((gNfcDev.disc.techs2Find & RFAL_NFC_POLL_TECH_PROP) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_PROP) != 0U) )
    {
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcpCbPollerInitialize() );                    /* Initialize RFAL for Proprietary NFC */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                         /* As field may already be On only starts GT timer */
            gNfcDev.isTechInit = true;
        }
     
        if( rfalIsGTExpired() )                                                       /* Wait until Guard Time is fulfilled */
        {
            err = rfalNfcpCbPollerTechnologyDetection();                              /* Poll for devices */
            if( err == RFAL_ERR_NONE )
            {
                gNfcDev.techsFound |= RFAL_NFC_POLL_TECH_PROP;
            }
            
            gNfcDev.isTechInit = false;
            gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_PROP;
        }
        
        return RFAL_ERR_BUSY;
    }
    
    return RFAL_ERR_NONE;
}

/*!
 ******************************************************************************
 * \brief Poller Collision Resolution
 * 
 * This method implements the Collision Resolution on all technologies that
 * have been detected before.
 * 
 * \return  RFAL_ERR_NONE         : Operation completed with no error
 * \return  RFAL_ERR_BUSY         : Operation ongoing
 * \return  RFAL_ERR_XXXX         : Error occurred
 * 
 ******************************************************************************
 */
static ReturnCode rfalNfcPollCollResolution( void )
{
    uint8_t    i;
    static uint8_t    devCnt;
    ReturnCode err;
    
    err    = RFAL_ERR_NONE;
    i      = 0;
    
    /* Suppress warning when specific RFAL features have been disabled */
    RFAL_NO_WARNING(err);
    RFAL_NO_WARNING(devCnt);
    RFAL_NO_WARNING(i);
    
    /* Check if device limit has been reached */
    if( gNfcDev.devCnt >= gNfcDev.disc.devLimit )
    {
        return RFAL_ERR_NONE;
    }
    
    /*******************************************************************************/
    /* NFC-A Collision Resolution                                                  */
    /*******************************************************************************/
#if RFAL_FEATURE_NFCA
    if( ((gNfcDev.techsFound & RFAL_NFC_POLL_TECH_A) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_A) != 0U) )   /* If a NFC-A device was found/detected, perform Collision Resolution */
    {
        static rfalNfcaListenDevice nfcaDevList[RFAL_NFC_MAX_DEVICES];
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcaPollerInitialize() );                       /* Initialize RFAL for NFC-A */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                          /* Turns the Field On and starts GT timer */
            
            gNfcDev.isTechInit    = true;                                              /* Technology has been initialized */
            gNfcDev.isOperOngoing = false;                                             /* No operation currently ongoing  */
        }
        
        if( !rfalIsGTExpired() )
        {
            return RFAL_ERR_BUSY;
        }
        
        if( !gNfcDev.isOperOngoing )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcaPollerStartFullCollisionResolution( gNfcDev.disc.compMode, (gNfcDev.disc.devLimit - gNfcDev.devCnt), nfcaDevList, &devCnt ) );
         
            gNfcDev.isOperOngoing = true;
            return RFAL_ERR_BUSY;
        }
        
        err = rfalNfcaPollerGetFullCollisionResolutionStatus();
        if( err != RFAL_ERR_BUSY )
        {
            gNfcDev.isTechInit = false;
            gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_A;
            
            if( (err == RFAL_ERR_NONE) && (devCnt != 0U) )
            {
                for( i=0; i<devCnt; i++ )                                                 /* Copy devices found form local Nfca list into global device list */
                {
                    gNfcDev.devList[gNfcDev.devCnt].type     = RFAL_NFC_LISTEN_TYPE_NFCA;
                    gNfcDev.devList[gNfcDev.devCnt].dev.nfca = nfcaDevList[i];
                    gNfcDev.devCnt++;
                }
            }
        }
        
        return RFAL_ERR_BUSY;
    }
#endif /* RFAL_FEATURE_NFCA */
    
    /*******************************************************************************/
    /* NFC-B Collision Resolution                                                  */
    /*******************************************************************************/
#if RFAL_FEATURE_NFCB
    if( ((gNfcDev.techsFound & RFAL_NFC_POLL_TECH_B) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_B) != 0U) )   /* If a NFC-B device was found/detected, perform Collision Resolution */
    {
        static rfalNfcbListenDevice nfcbDevList[RFAL_NFC_MAX_DEVICES];
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcbPollerInitialize());                        /* Initialize RFAL for NFC-B */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                          /* Ensure GT again as other technologies have also been polled */
            
            gNfcDev.isTechInit    = true;
            gNfcDev.isOperOngoing = false;                                             /* No operation currently ongoing  */
        }
        
        if( !rfalIsGTExpired() )
        {
            return RFAL_ERR_BUSY;
        }
        
        if( !gNfcDev.isOperOngoing )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcbPollerStartCollisionResolution( gNfcDev.disc.compMode, (gNfcDev.disc.devLimit - gNfcDev.devCnt), nfcbDevList, &devCnt ) );
         
            gNfcDev.isOperOngoing = true;
            return RFAL_ERR_BUSY;
        }
        
        err = rfalNfcbPollerGetCollisionResolutionStatus();
        if( err != RFAL_ERR_BUSY )
        {
            gNfcDev.isTechInit = false;
            gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_B;
            
            if( (err == RFAL_ERR_NONE) && (devCnt != 0U) )
            {
                for( i=0; i<devCnt; i++ )                                                 /* Copy devices found form local Nfcb list into global device list */
                {
                    gNfcDev.devList[gNfcDev.devCnt].type     = RFAL_NFC_LISTEN_TYPE_NFCB;
                    gNfcDev.devList[gNfcDev.devCnt].dev.nfcb = nfcbDevList[i];
                    gNfcDev.devCnt++;
                }
            }
        }
        
        return RFAL_ERR_BUSY;
    }
#endif /* RFAL_FEATURE_NFCB*/
    
    /*******************************************************************************/
    /* NFC-F Collision Resolution                                                  */
    /*******************************************************************************/
#if RFAL_FEATURE_NFCF
    if( ((gNfcDev.techsFound & RFAL_NFC_POLL_TECH_F) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_F) != 0U) )  /* If a NFC-F device was found/detected, perform Collision Resolution */
    {
        static rfalNfcfListenDevice nfcfDevList[RFAL_NFC_MAX_DEVICES];
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcfPollerInitialize( gNfcDev.disc.nfcfBR ));   /* Initialize RFAL for NFC-F */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                          /* Ensure GT again as other technologies have also been polled */
            
            gNfcDev.isTechInit    = true;
            gNfcDev.isOperOngoing = false;                                             /* No operation currently ongoing  */
        }
        
        if( !rfalIsGTExpired() )
        {
            return RFAL_ERR_BUSY;
        }
        
        if( !gNfcDev.isOperOngoing )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcfPollerStartCollisionResolution( gNfcDev.disc.compMode, (gNfcDev.disc.devLimit - gNfcDev.devCnt), nfcfDevList, &devCnt ) );
         
            gNfcDev.isOperOngoing = true;
            return RFAL_ERR_BUSY;
        }
        
        err = rfalNfcfPollerGetCollisionResolutionStatus();
        if( err != RFAL_ERR_BUSY )
        {
            gNfcDev.isTechInit = false;
            gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_F;
            
            if( (err == RFAL_ERR_NONE) && (devCnt != 0U) )
            {
                for( i=0; i<devCnt; i++ )                                              /* Copy devices found form local Nfcf list into global device list */
                {
                    gNfcDev.devList[gNfcDev.devCnt].type     = RFAL_NFC_LISTEN_TYPE_NFCF;
                    gNfcDev.devList[gNfcDev.devCnt].dev.nfcf = nfcfDevList[i];
                    gNfcDev.devCnt++;
                }
            }
        }
        
        return RFAL_ERR_BUSY;
    }
#endif /* RFAL_FEATURE_NFCF */
    
    /*******************************************************************************/
    /* NFC-V Collision Resolution                                                  */
    /*******************************************************************************/
#if RFAL_FEATURE_NFCV
    if( ((gNfcDev.techsFound & RFAL_NFC_POLL_TECH_V) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_V) != 0U) )  /* If a NFC-V device was found/detected, perform Collision Resolution */
    {
        rfalNfcvListenDevice nfcvDevList[RFAL_NFC_MAX_DEVICES];
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcvPollerInitialize());                       /* Initialize RFAL for NFC-V */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                         /* Ensure GT again as other technologies have also been polled */
            gNfcDev.isTechInit = true;
        }
        
        if( !rfalIsGTExpired() )
        {
            return RFAL_ERR_BUSY;
        }
        
        devCnt             = 0;
        gNfcDev.isTechInit = false;
        gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_V;
        
        
        err = rfalNfcvPollerCollisionResolution( RFAL_COMPLIANCE_MODE_NFC, (gNfcDev.disc.devLimit - gNfcDev.devCnt), nfcvDevList, &devCnt );
        if( (err == RFAL_ERR_NONE) && (devCnt != 0U) )
        {
            for( i=0; i<devCnt; i++ )                                                 /* Copy devices found form local Nfcf list into global device list */
            {
                gNfcDev.devList[gNfcDev.devCnt].type     = RFAL_NFC_LISTEN_TYPE_NFCV;
                gNfcDev.devList[gNfcDev.devCnt].dev.nfcv = nfcvDevList[i];
                gNfcDev.devCnt++;
            }
        }
        
        return RFAL_ERR_BUSY;
    }
#endif /* RFAL_FEATURE_NFCV */
    
    /*******************************************************************************/
    /* ST25TB Collision Resolution                                                 */
    /*******************************************************************************/
#if RFAL_FEATURE_ST25TB
    if( ((gNfcDev.techsFound & RFAL_NFC_POLL_TECH_ST25TB) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_ST25TB) != 0U) ) /* If a ST25TB device was found/detected, perform Collision Resolution */
    {
        rfalSt25tbListenDevice st25tbDevList[RFAL_NFC_MAX_DEVICES];
        
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalSt25tbPollerInitialize() );                    /* Initialize RFAL for ST25TB */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                         /* Ensure GT again as other technologies have also been polled */
            gNfcDev.isTechInit = true;
        }
        
        if( !rfalIsGTExpired() )
        {
            return RFAL_ERR_BUSY;
        }
        
        devCnt             = 0;
        gNfcDev.isTechInit = false;
        gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_ST25TB;
        
        
        err = rfalSt25tbPollerCollisionResolution( (gNfcDev.disc.devLimit - gNfcDev.devCnt), st25tbDevList, &devCnt );
        if( (err == RFAL_ERR_NONE) && (devCnt != 0U) )
        {
            for( i=0; i<devCnt; i++ )                                                 /* Copy devices found form local Nfcf list into global device list */
            {
                gNfcDev.devList[gNfcDev.devCnt].type       = RFAL_NFC_LISTEN_TYPE_ST25TB;
                gNfcDev.devList[gNfcDev.devCnt].dev.st25tb = st25tbDevList[i];
                gNfcDev.devCnt++;
            }
        }
        
        return RFAL_ERR_BUSY;
    }
#endif /* RFAL_FEATURE_ST25TB */
    
    
    /*******************************************************************************/
    /* Proprietary NFC Collision Resolution                                        */
    /*******************************************************************************/
    if( ((gNfcDev.techsFound & RFAL_NFC_POLL_TECH_PROP) != 0U) && ((gNfcDev.techs2do & RFAL_NFC_POLL_TECH_PROP) != 0U) )   /* If a device was found/detected, perform Collision Resolution */
    {
        if( !gNfcDev.isTechInit )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcpCbPollerInitialize() );                     /* Initialize RFAL for Proprietary NFC */
            RFAL_EXIT_ON_ERR( err, rfalFieldOnAndStartGT() );                          /* Turns the Field On and starts GT timer */
            
            gNfcDev.isTechInit    = true;                                              /* Technology has been initialized */
            gNfcDev.isOperOngoing = false;                                             /* No operation currently ongoing  */
        }
        
        if( !rfalIsGTExpired() )
        {
            return RFAL_ERR_BUSY;
        }
        
        if( !gNfcDev.isOperOngoing )
        {
            RFAL_EXIT_ON_ERR( err, rfalNfcpCbPollerStartCollisionResolution() );
         
            gNfcDev.isOperOngoing = true;
            return RFAL_ERR_BUSY;
        }
        
        err = rfalNfcpCbPollerGetCollisionResolutionStatus();
        if( err != RFAL_ERR_BUSY )
        {
            gNfcDev.isTechInit = false;
            gNfcDev.techs2do  &= ~RFAL_NFC_POLL_TECH_PROP;
            
            if( err == RFAL_ERR_NONE )
            {
                gNfcDev.devCnt = 1;                                                   /* Device list held by caller */
                gNfcDev.devList[0].type = RFAL_NFC_LISTEN_TYPE_PROP;
            }
        }
        return RFAL_ERR_BUSY;
    }

    
    return RFAL_ERR_NONE;                                                             /* All technologies have been performed */
}


/*!
 ******************************************************************************
 * \brief Poller Activation
 * 
 * This method Activates a given device according to it's type and 
 * protocols supported
 *  
 * \param[in]  devIt : device's position on the list to be activated 
 * 
 * \return  RFAL_ERR_NONE         : Operation completed with no error
 * \return  RFAL_ERR_BUSY         : Operation ongoing
 * \return  RFAL_ERR_XXXX         : Error occurred
 * 
 ******************************************************************************
 */
static ReturnCode rfalNfcPollActivation( uint8_t devIt )
{
    ReturnCode                  err;
    uint8_t                     devIdx;
    rfalNfcaListenDeviceType    nfcaType;
    
    err      = RFAL_ERR_NONE;
    devIdx   = 0;
    nfcaType = RFAL_NFCA_T1T;
    
    /* Suppress warning when specific RFAL features have been disabled */
    RFAL_NO_WARNING(err);
    RFAL_NO_WARNING(devIdx);
    RFAL_NO_WARNING(nfcaType);
    
    if( devIt > gNfcDev.devCnt )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    switch( gNfcDev.devList[devIt].type )
    {
        /*******************************************************************************/
        /* AP2P Activation                                                             */
        /*******************************************************************************/
    #if RFAL_FEATURE_NFC_DEP
        case RFAL_NFC_LISTEN_TYPE_AP2P:
            /* Activation has already been  (ATR_REQ) */
        
            gNfcDev.devList[devIt].nfcid     = gNfcDev.devList[devIt].proto.nfcDep.activation.Target.ATR_RES.NFCID3;
            gNfcDev.devList[devIt].nfcidLen  = RFAL_NFCDEP_NFCID3_LEN;
            break;
    #endif /* RFAL_FEATURE_NFC_DEP */
        
        
        /*******************************************************************************/
        /* Passive NFC-A Activation                                                    */
        /*******************************************************************************/
    #if RFAL_FEATURE_NFCA
        case RFAL_NFC_LISTEN_TYPE_NFCA:
            
            if( !gNfcDev.isTechInit )
            {
                rfalNfcaPollerInitialize();
                gNfcDev.isTechInit    = true;
                gNfcDev.isOperOngoing = false;
                return RFAL_ERR_BUSY;
            }
            
            if( gNfcDev.devList[devIt].dev.nfca.isSleep )                             /* Check if desired device is in Sleep */
            {
                if( !gNfcDev.isOperOngoing )
                {
                    /* Wake up all cards  */
                    RFAL_EXIT_ON_ERR( err, rfalNfcaPollerCheckPresence( RFAL_14443A_SHORTFRAME_CMD_WUPA, &gNfcDev.sensRes ) );
                    
                    /* Select specific device */
                    RFAL_EXIT_ON_ERR( err, rfalNfcaPollerStartSelect( gNfcDev.devList[devIt].dev.nfca.nfcId1, gNfcDev.devList[devIt].dev.nfca.nfcId1Len, &gNfcDev.devList[devIt].dev.nfca.selRes ) ); 
                    
                    gNfcDev.isOperOngoing = true;
                }
                else
                {
                    RFAL_EXIT_ON_ERR( err, rfalNfcaPollerGetSelectStatus() ); 


                    /* In case multiple NFC-A devices are present, when activating/waking a device that 
                       is sleeping (not the last one) will make the active one to go back to IDLE.
                       Marking it as in sleep (Activity 2.2  9.4.4 Optional Symbol 2) will ensure that 
                       gets correctly activated afterwards                                              */
                    for( devIdx = 0; devIdx < gNfcDev.devCnt; devIdx++ )
                    {
                        if( gNfcDev.devList[devIdx].type == RFAL_NFC_LISTEN_TYPE_NFCA )
                        {
                            gNfcDev.devList[devIdx].dev.nfca.isSleep = true;
                        }
                    }
                    
                    gNfcDev.devList[devIt].dev.nfca.isSleep = false;
                    gNfcDev.isOperOngoing = false;
                }
                return RFAL_ERR_BUSY;
            }
            
            
            /* Set NFCID */
            gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].dev.nfca.nfcId1;
            gNfcDev.devList[devIt].nfcidLen = gNfcDev.devList[devIt].dev.nfca.nfcId1Len;
            
            /* If device supports multiple technologies assign protocol requested */
            nfcaType = gNfcDev.devList[devIt].dev.nfca.type;
            if( nfcaType == RFAL_NFCA_T4T_NFCDEP )
            {
                nfcaType = ( (gNfcDev.disc.p2pNfcaPrio) ? RFAL_NFCA_NFCDEP : RFAL_NFCA_T4T);
            }
            
            /*******************************************************************************/
            /* Perform protocol specific activation                                        */
            switch( nfcaType )
            {
                /*******************************************************************************/
                case RFAL_NFCA_T1T:
                
                    /* No further activation needed for T1T (RID already performed) */
                
                    gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].dev.nfca.ridRes.uid;
                    gNfcDev.devList[devIt].nfcidLen = RFAL_T1T_UID_LEN;
                
                    gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_RF;
                    break;
                
                case RFAL_NFCA_T2T:
                    
                    /* No further activation needed for a T2T */

                    gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_RF;
                    break;
                
                
                /*******************************************************************************/
                case RFAL_NFCA_T4T:                                                   /* Device supports ISO-DEP */
                
                #if RFAL_FEATURE_ISO_DEP && RFAL_FEATURE_ISO_DEP_POLL
                    if( !gNfcDev.isOperOngoing )
                    {
                        /* Perform ISO-DEP (ISO14443-4) activation: RATS and PPS if supported */
                        rfalIsoDepInitializeWithParams( gNfcDev.disc.compMode, RFAL_ISODEP_MAX_R_RETRYS, RFAL_ISODEP_MAX_WTX_NACK_RETRYS, RFAL_ISODEP_MAX_WTX_RETRYS, RFAL_ISODEP_MAX_DSL_RETRYS, RFAL_ISODEP_MAX_I_RETRYS, RFAL_ISODEP_RATS_RETRIES);
                        RFAL_EXIT_ON_ERR( err, rfalIsoDepPollAStartActivation( gNfcDev.disc.isoDepFS, RFAL_ISODEP_NO_DID, gNfcDev.disc.maxBR, &gNfcDev.devList[devIt].proto.isoDep ) );
                        
                        gNfcDev.isOperOngoing = true;
                        return RFAL_ERR_BUSY;
                    }

                    err = rfalIsoDepPollAGetActivationStatus();
                    if( err != RFAL_ERR_NONE )
                    {
                        return err;
                    }
                    
                    gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_ISODEP;   /* NFC-A T4T device activated */
                #else
                    gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_RF;       /* No ISO-DEP supported activate using RF interface */
                #endif /* RFAL_FEATURE_ISO_DEP_POLL */
                    break;
                    
                /*******************************************************************************/
                case RFAL_NFCA_NFCDEP:                                                /* Device supports NFC-DEP */
                
                #if RFAL_FEATURE_NFC_DEP
                    /* Perform NFC-DEP (P2P) activation: ATR and PSL if supported */
                    RFAL_EXIT_ON_ERR( err, rfalNfcNfcDepActivate( &gNfcDev.devList[devIt], RFAL_NFCDEP_COMM_PASSIVE, NULL, 0 ) );
                
                    gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].proto.nfcDep.activation.Target.ATR_RES.NFCID3;
                    gNfcDev.devList[devIt].nfcidLen = RFAL_NFCDEP_NFCID3_LEN;
                
                    gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_NFCDEP;   /* NFC-A P2P device activated */
                #else
                    gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_RF;       /* No NFC-DEP supported activate using RF interface */
                #endif /* RFAL_FEATURE_NFC_DEP */
                    break;
                
                /*******************************************************************************/
                case RFAL_NFCA_T4T_NFCDEP:                                            /* Multiple proto resolved based on NFCA P2P Prio config */
                default:
                    return RFAL_ERR_WRONG_STATE;
            }
            break;
    #endif /* RFAL_FEATURE_NFCA */
        
        
        /*******************************************************************************/
        /* Passive NFC-B Activation                                                    */
        /*******************************************************************************/
    #if RFAL_FEATURE_NFCB
        case RFAL_NFC_LISTEN_TYPE_NFCB:
            
            if( !gNfcDev.isTechInit )
            {
                rfalNfcbPollerInitialize();
                gNfcDev.isTechInit    = true;
                gNfcDev.isOperOngoing = false;
            
                if( gNfcDev.devList[devIt].dev.nfcb.isSleep )                         /* Check if desired device is in Sleep */
                {
                    /* Wake up all cards. SENSB_RES may return collision but the NFCID0 is available to explicitly select NFC-B card via ATTRIB; so error will be ignored here */
                    rfalNfcbPollerStartCheckPresence( RFAL_NFCB_SENS_CMD_ALLB_REQ, RFAL_NFCB_SLOT_NUM_1, &gNfcDev.sensbRes, &gNfcDev.sensbResLen );
                }
                
                return RFAL_ERR_BUSY;
            }
            
            if( gNfcDev.devList[devIt].dev.nfcb.isSleep )                             /* Check if desired device is still in Sleep */
            {
                /* Wake up all cards. SENSB_RES may return collision but the NFCID0 is available to explicitly select NFC-B card via ATTRIB; so error will be ignored here */
                RFAL_EXIT_ON_BUSY( err, rfalNfcbPollerGetCheckPresenceStatus() );
                
                gNfcDev.devList[devIt].dev.nfcb.isSleep = false;
            }
            
            /* Set NFCID */
            gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].dev.nfcb.sensbRes.nfcid0;
            gNfcDev.devList[devIt].nfcidLen = RFAL_NFCB_NFCID0_LEN;
            
        #if RFAL_FEATURE_ISO_DEP && RFAL_FEATURE_ISO_DEP_POLL
            /* Check if device supports  ISO-DEP (ISO14443-4) */
            if( (gNfcDev.devList[devIt].dev.nfcb.sensbRes.protInfo.FsciProType & RFAL_NFCB_SENSB_RES_PROTO_ISO_MASK) != 0U )
            {
                if( !gNfcDev.isOperOngoing )
                {
                    rfalIsoDepInitializeWithParams( gNfcDev.disc.compMode, RFAL_ISODEP_MAX_R_RETRYS, RFAL_ISODEP_MAX_WTX_NACK_RETRYS, RFAL_ISODEP_MAX_WTX_RETRYS, RFAL_ISODEP_MAX_DSL_RETRYS, RFAL_ISODEP_MAX_I_RETRYS, RFAL_ISODEP_RATS_RETRIES);
                    /* Perform ISO-DEP (ISO14443-4) activation: ATTRIB    */
                    RFAL_EXIT_ON_ERR( err, rfalIsoDepPollBStartActivation( gNfcDev.disc.isoDepFS, RFAL_ISODEP_NO_DID, gNfcDev.disc.maxBR, 0x00, &gNfcDev.devList[devIt].dev.nfcb, NULL, 0, &gNfcDev.devList[devIt].proto.isoDep ) );
                    
                    gNfcDev.isOperOngoing = true;
                    return RFAL_ERR_BUSY;
                }
                
                err = rfalIsoDepPollBGetActivationStatus();
                if( err != RFAL_ERR_NONE )
                {
                    return err;
                }
                
                gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_ISODEP;       /* NFC-B T4T device activated */
                break;
            }
                    
        #endif /* RFAL_FEATURE_ISO_DEP_POLL */
            
            gNfcDev.devList[devIt].rfInterface =  RFAL_NFC_INTERFACE_RF;              /* NFC-B device activated     */
            break;
            
    #endif /* RFAL_FEATURE_NFCB */
        
        
        /*******************************************************************************/
        /* Passive NFC-F Activation                                                    */
        /*******************************************************************************/
    #if RFAL_FEATURE_NFCF
        case RFAL_NFC_LISTEN_TYPE_NFCF:
            
            rfalNfcfPollerInitialize( gNfcDev.disc.nfcfBR );
        
        #if RFAL_FEATURE_NFC_DEP
            if( rfalNfcfIsNfcDepSupported( &gNfcDev.devList[devIt].dev.nfcf ) )
            {
                /* Perform NFC-DEP (P2P) activation: ATR and PSL if supported */
                RFAL_EXIT_ON_ERR( err, rfalNfcNfcDepActivate( &gNfcDev.devList[devIt], RFAL_NFCDEP_COMM_PASSIVE, NULL, 0 ) );
                
                /* Set NFCID */
                gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].proto.nfcDep.activation.Target.ATR_RES.NFCID3;
                gNfcDev.devList[devIt].nfcidLen = RFAL_NFCDEP_NFCID3_LEN;
                
                gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_NFCDEP;       /* NFC-F P2P device activated */
                break;
            }
        #endif /* RFAL_FEATURE_NFC_DEP */
            
            /* Set NFCID */
            gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].dev.nfcf.sensfRes.NFCID2;
            gNfcDev.devList[devIt].nfcidLen = RFAL_NFCF_NFCID2_LEN;
            
            gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_RF;               /* NFC-F T3T device activated */
            break;
    #endif /* RFAL_FEATURE_NFCF */
        
        
        /*******************************************************************************/
        /* Passive NFC-V Activation                                                    */
        /*******************************************************************************/
    #if RFAL_FEATURE_NFCV
        case RFAL_NFC_LISTEN_TYPE_NFCV:
            
            rfalNfcvPollerInitialize();
            
            /* No specific activation needed for a T5T */
            
            /* Set NFCID */
            gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].dev.nfcv.InvRes.UID;
            gNfcDev.devList[devIt].nfcidLen = RFAL_NFCV_UID_LEN;
        
            gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_RF;               /* NFC-V T5T device activated */
            break;
    #endif /* RFAL_FEATURE_NFCV */
        
        
        /*******************************************************************************/
        /* Passive ST25TB Activation                                                   */
        /*******************************************************************************/
    #if RFAL_FEATURE_ST25TB
        case RFAL_NFC_LISTEN_TYPE_ST25TB:
            
            rfalSt25tbPollerInitialize();
            
            /* No specific activation needed for a ST25TB */
        
            /* Set NFCID */
            gNfcDev.devList[devIt].nfcid    = gNfcDev.devList[devIt].dev.st25tb.UID;
            gNfcDev.devList[devIt].nfcidLen = RFAL_ST25TB_UID_LEN;
        
            gNfcDev.devList[devIt].rfInterface = RFAL_NFC_INTERFACE_RF;               /* ST25TB device activated */
            break;
    #endif /* RFAL_FEATURE_ST25TB */
        
        
        /*******************************************************************************/
        /* Passive Proprietary NFC Activation                                          */
        /*******************************************************************************/
        case RFAL_NFC_LISTEN_TYPE_PROP:
            
            if( !gNfcDev.isTechInit )
            {
                RFAL_EXIT_ON_ERR( err, rfalNfcpCbPollerInitialize() );
                gNfcDev.isTechInit    = true;
                gNfcDev.isOperOngoing = false;
                return RFAL_ERR_BUSY;
            }
            

            if( !gNfcDev.isOperOngoing )
            {
                /* Start activation  */
                RFAL_EXIT_ON_ERR( err, rfalNfcpCbStartActivation() );
                
                gNfcDev.isOperOngoing = true;
                return RFAL_ERR_BUSY;
            }
            
            err = rfalNfcpCbGetActivationStatus();
            if( err != RFAL_ERR_NONE )
            {
                return err;
            }

            /* Clear NFCID */
            gNfcDev.devList[devIt].nfcid = NULL;
            gNfcDev.devList[devIt].nfcidLen = 0;
            
            gNfcDev.devList[devIt].rfInterface =  RFAL_NFC_INTERFACE_RF;
            break;
         
         
        /*******************************************************************************/
        default:
            return RFAL_ERR_WRONG_STATE;
    }
    
    gNfcDev.activeDev     = &gNfcDev.devList[devIt];                                  /* Assign active device to be used further on */
    gNfcDev.isOperOngoing = false;
    return RFAL_ERR_NONE;
}


/*!
 ******************************************************************************
 * \brief Listener Activation
 * 
 * This method handles the listen mode Activation according to the different 
 * protocols the Reader/Initiator performs
 * 
 * \return  RFAL_ERR_NONE   : Operation completed with no error
 * \return  RFAL_ERR_BUSY   : Operation ongoing
 * \return  RFAL_ERR_PROTO  : Unexpected frame received
 * \return  RFAL_ERR_XXXX   : Error occurred
 * 
 ******************************************************************************
 */
#if RFAL_FEATURE_LISTEN_MODE
static ReturnCode rfalNfcListenActivation( void )
{
    bool                      isDataRcvd;
    ReturnCode                ret;
    rfalLmState               lmSt;
    rfalBitRate               bitRate;
#if RFAL_FEATURE_NFC_DEP    
    uint8_t                   hdrLen;
    
    /* Set the header length in NFC-A */
    hdrLen = (RFAL_NFCDEP_SB_LEN + RFAL_NFCDEP_LEN_LEN);
#endif /* RFAL_FEATURE_NFC_DEP */

    
    lmSt = rfalListenGetState( &isDataRcvd, &bitRate );
    switch(lmSt)
    {

    #if RFAL_FEATURE_NFCA
        /*******************************************************************************/
        case RFAL_LM_STATE_ACTIVE_A:                                                  /* NFC-A CE activation */
        case RFAL_LM_STATE_ACTIVE_Ax:
            
            if( isDataRcvd )                                                          /* Check if Reader/Initator has sent some data */
            {
                /* Check if received data is a Sleep request */
                if( rfalNfcaListenerIsSleepReq( gNfcDev.rxBuf.rfBuf, rfalConvBitsToBytes(gNfcDev.rxLen)) )     /* Check if received data is a SLP_REQ */
                {
                    /* Set the Listen Mode in Sleep state */
                    RFAL_EXIT_ON_ERR( ret, rfalListenSleepStart( RFAL_LM_STATE_SLEEP_A, gNfcDev.rxBuf.rfBuf, sizeof(gNfcDev.rxBuf.rfBuf), &gNfcDev.rxLen ) );
                }
                
            #if RFAL_FEATURE_ISO_DEP && RFAL_FEATURE_ISO_DEP_LISTEN
                /* Check if received data is a valid RATS */
                else if( rfalIsoDepIsRats( gNfcDev.rxBuf.rfBuf, (uint8_t)rfalConvBitsToBytes(gNfcDev.rxLen) ) )
                {
                    rfalIsoDepAtsParam        atsParam;
                    rfalIsoDepListenActvParam rxParam;
                    
                    /* Set ATS parameters */
                    atsParam.fsci       = (uint8_t)RFAL_ISODEP_DEFAULT_FSCI;
                    atsParam.fwi        = RFAL_ISODEP_DEFAULT_FWI;
                    atsParam.sfgi       = RFAL_ISODEP_DEFAULT_SFGI;
                    atsParam.didSupport = false;
                    atsParam.ta         = RFAL_ISODEP_ATS_TA_SAME_D;
                    atsParam.hb         = NULL;
                    atsParam.hbLen      = 0;

                    /* Set Rx parameters */
                    rxParam.rxBuf        = (rfalIsoDepBufFormat*) &gNfcDev.rxBuf.isoDepBuf;   /*  PRQA S 0310 # MISRA 11.3 - Intentional safe cast to avoiding large buffer duplication */
                    rxParam.rxLen        = &gNfcDev.rxLen;
                    rxParam.isoDepDev    = &gNfcDev.devList->proto.isoDep;
                    rxParam.isRxChaining = &gNfcDev.isRxChaining;

                    rfalListenSetState( RFAL_LM_STATE_CARDEMU_4A );                   /* Set next state CE T4T */
                    rfalIsoDepInitialize();                                           /* Initialize ISO-DEP layer to handle ISO14443-a activation / RATS */
                    
                    /* Set ISO-DEP layer to digest RATS and handle activation */
                    RFAL_EXIT_ON_ERR( ret, rfalIsoDepListenStartActivation( &atsParam, NULL, gNfcDev.rxBuf.rfBuf, gNfcDev.rxLen, rxParam ) );
                }
            #endif /* RFAL_FEATURE_ISO_DEP_LISTEN */
            
            #if RFAL_FEATURE_NFC_DEP

                /* Check if received data is a valid ATR_REQ */
                else if( rfalNfcDepIsAtrReq( &gNfcDev.rxBuf.rfBuf[hdrLen], (rfalConvBitsToBytes(gNfcDev.rxLen) - hdrLen), gNfcDev.devList->nfcid ) )
                {
                    gNfcDev.devList->type = RFAL_NFC_POLL_TYPE_NFCA;
                    RFAL_EXIT_ON_ERR( ret, rfalNfcNfcDepActivate( gNfcDev.devList, RFAL_NFCDEP_COMM_PASSIVE, &gNfcDev.rxBuf.rfBuf[hdrLen], (rfalConvBitsToBytes(gNfcDev.rxLen) - hdrLen) ) );
                }
            #endif /* RFAL_FEATURE_NFC_DEP */
                
                else
                {
                    return RFAL_ERR_PROTO;
                }
            }
            return RFAL_ERR_BUSY;

    #endif /* RFAL_FEATURE_NFCA */
            
    #if RFAL_FEATURE_ISO_DEP && RFAL_FEATURE_ISO_DEP_LISTEN
        /*******************************************************************************/
        case RFAL_LM_STATE_CARDEMU_4A:                                                /* T4T ISO-DEP activation */
            
            ret = rfalIsoDepListenGetActivationStatus();
            if( ret == RFAL_ERR_NONE )
            {
                gNfcDev.devList->type        = RFAL_NFC_POLL_TYPE_NFCA;
                gNfcDev.devList->rfInterface = RFAL_NFC_INTERFACE_ISODEP;
                gNfcDev.devList->nfcid       = NULL;
                gNfcDev.devList->nfcidLen    = 0;
            }
            return ( (ret == RFAL_ERR_LINK_LOSS) ? RFAL_ERR_PROTO : ret);             /* Link loss during protocol activation, reMap error */
            
    #endif /* RFAL_FEATURE_ISO_DEP_LISTEN */
        
        /*******************************************************************************/
        case RFAL_LM_STATE_READY_F:                                                   /* NFC-F CE activation */
            
            if( isDataRcvd )                                                          /* Wait for the first received data */
            {
            #if RFAL_FEATURE_NFC_DEP
                /* Set the header length in NFC-F */
                hdrLen = RFAL_NFCDEP_LEN_LEN;
                
                if( rfalNfcDepIsAtrReq( &gNfcDev.rxBuf.rfBuf[hdrLen], (rfalConvBitsToBytes(gNfcDev.rxLen) - hdrLen), gNfcDev.devList->nfcid ) )
                {
                    gNfcDev.devList->type = RFAL_NFC_POLL_TYPE_NFCF;
                    RFAL_EXIT_ON_ERR( ret, rfalNfcNfcDepActivate( gNfcDev.devList, RFAL_NFCDEP_COMM_PASSIVE, &gNfcDev.rxBuf.rfBuf[hdrLen], (rfalConvBitsToBytes(gNfcDev.rxLen) - hdrLen) ) );
                }
                else
            #endif /* RFAL_FEATURE_NFC_DEP */
                {
                    rfalListenSetState( RFAL_LM_STATE_CARDEMU_3 );                    /* First data already received - set T3T CE */
                }
            }
            return RFAL_ERR_BUSY;
            
        /*******************************************************************************/
        case RFAL_LM_STATE_CARDEMU_3:                                                 /* T3T activated */
            
            gNfcDev.devList->type        = RFAL_NFC_POLL_TYPE_NFCF;
            gNfcDev.devList->rfInterface = RFAL_NFC_INTERFACE_RF;
            gNfcDev.devList->nfcid       = NULL;
            gNfcDev.devList->nfcidLen    = 0;
            
            return RFAL_ERR_NONE;
        
    #if RFAL_FEATURE_NFC_DEP
        /*******************************************************************************/
        case RFAL_LM_STATE_TARGET_A:                                                  /* NFC-DEP activation */
        case RFAL_LM_STATE_TARGET_F:
            
            ret = rfalNfcDepListenGetActivationStatus();
            if( ret == RFAL_ERR_NONE )
            {
                gNfcDev.devList->rfInterface = RFAL_NFC_INTERFACE_NFCDEP;
                gNfcDev.devList->nfcid       = gNfcDev.devList->proto.nfcDep.activation.Initiator.ATR_REQ.NFCID3;
                gNfcDev.devList->nfcidLen    = RFAL_NFCDEP_NFCID3_LEN;
            }
            return ret;
    #endif /* RFAL_FEATURE_NFC_DEP */
        
        /*******************************************************************************/
        case RFAL_LM_STATE_IDLE:                                                      /* AP2P activation */
            if( isDataRcvd )                                                          /* Check if Reader/Initator has sent some data */
            {
                if( (gNfcDev.lmMask & RFAL_LM_MASK_ACTIVE_P2P) != 0U )                /* Check if AP2P is enabled */
                {
                    
                #if RFAL_FEATURE_NFC_DEP
                    /* Calculate the header length in NFC-A or NFC-F mode*/
                    hdrLen = ( (bitRate == RFAL_BR_106) ? (RFAL_NFCDEP_SB_LEN + RFAL_NFCDEP_LEN_LEN) : RFAL_NFCDEP_LEN_LEN );
                    
                    if( rfalNfcDepIsAtrReq( &gNfcDev.rxBuf.rfBuf[hdrLen], (rfalConvBitsToBytes(gNfcDev.rxLen) - hdrLen), NULL) )
                    {
                        gNfcDev.devList->type = RFAL_NFC_POLL_TYPE_AP2P;
                        rfalSetMode( (RFAL_MODE_LISTEN_ACTIVE_P2P), bitRate, bitRate );
                        rfalSetFDTListen( RFAL_FDT_LISTEN_AP2P_LISTENER );
                        RFAL_EXIT_ON_ERR( ret, rfalNfcNfcDepActivate( gNfcDev.devList, RFAL_NFCDEP_COMM_ACTIVE, &gNfcDev.rxBuf.rfBuf[hdrLen], (rfalConvBitsToBytes(gNfcDev.rxLen) - hdrLen) ) );
                    }
                    else
                #endif /* RFAL_FEATURE_NFC_DEP */
                    {
                        return RFAL_ERR_PROTO;
                    }
                }
            }
            return RFAL_ERR_BUSY;
            
        /*******************************************************************************/
        case RFAL_LM_STATE_READY_A:
        case RFAL_LM_STATE_READY_Ax:
        case RFAL_LM_STATE_SLEEP_A:
        case RFAL_LM_STATE_SLEEP_AF:
            return RFAL_ERR_BUSY;
        
        /*******************************************************************************/
        case RFAL_LM_STATE_POWER_OFF:
            return RFAL_ERR_LINK_LOSS;
        
        default:                                                                      /* Wait for activation */
            break;
    }

    return RFAL_ERR_INTERNAL;
}
#endif /* RFAL_FEATURE_LISTEN_MODE */


/*!
 ******************************************************************************
 * \brief Poller NFC DEP Activate
 * 
 * This method performs NFC-DEP Activation 
 *  
 * \param[in]  device    : device info
 * \param[in]  commMode  : communication mode (Passive/Active)
 * \param[in]  atrReq    : received ATR_REQ
 * \param[in]  atrReqLen : received ATR_REQ size
 * 
 * \return  RFAL_ERR_NONE     : Operation completed with no error
 * \return  RFAL_ERR_BUSY     : Operation ongoing
 * \return  RFAL_ERR_XXXX     : Error occurred
 * 
 ******************************************************************************
 */
#if RFAL_FEATURE_NFC_DEP
static ReturnCode rfalNfcNfcDepActivate( rfalNfcDevice *device, rfalNfcDepCommMode commMode, const uint8_t *atrReq, uint16_t atrReqLen )
{
    rfalNfcDepAtrParam          initParam;
    
    /* Suppress warnings if Listen mode is disabled */
    RFAL_NO_WARNING(atrReq);
    RFAL_NO_WARNING(atrReqLen);
    
    /* If we are in Poll mode */
    if( gNfcDev.state < RFAL_NFC_STATE_LISTEN_TECHDETECT )
    {
        /*******************************************************************************/
        /* If Passive F use the NFCID2 retrieved from SENSF                            */
        if( device->type == RFAL_NFC_LISTEN_TYPE_NFCF )
        {
            initParam.nfcid    = device->dev.nfcf.sensfRes.NFCID2;
            initParam.nfcidLen = RFAL_NFCF_NFCID2_LEN;
        }
        else
        {
            initParam.nfcid    = gNfcDev.disc.nfcid3; 
            initParam.nfcidLen = RFAL_NFCDEP_NFCID3_LEN;
        }    
        
        initParam.BS        = RFAL_NFCDEP_Bx_NO_HIGH_BR;
        initParam.BR        = RFAL_NFCDEP_Bx_NO_HIGH_BR;
        initParam.DID       = RFAL_NFCDEP_DID_NO;
        initParam.NAD       = RFAL_NFCDEP_NAD_NO;
        initParam.LR        = gNfcDev.disc.nfcDepLR;
        initParam.GB        = gNfcDev.disc.GB;
        initParam.GBLen     = gNfcDev.disc.GBLen;
        initParam.commMode  = commMode;
        initParam.operParam = (RFAL_NFCDEP_OPER_FULL_MI_EN | RFAL_NFCDEP_OPER_EMPTY_DEP_DIS | RFAL_NFCDEP_OPER_ATN_EN | RFAL_NFCDEP_OPER_RTOX_REQ_EN);
        
        rfalNfcDepInitialize();
        /* Perform NFC-DEP (P2P) activation: ATR and PSL if supported */
        return rfalNfcDepInitiatorHandleActivation( &initParam, gNfcDev.disc.maxBR, &device->proto.nfcDep );
    }
    
    /* If we are in Listen mode */
#if RFAL_FEATURE_LISTEN_MODE
    else if( rfalNfcIsRemDevPoller( device->type ) && ( gNfcDev.state >= RFAL_NFC_STATE_LISTEN_TECHDETECT ) )
    {
        rfalNfcDepListenActvParam   actvParams;
        rfalNfcDepTargetParam       targetParam;
        
        RFAL_MEMCPY(targetParam.nfcid3, (uint8_t*)gNfcDev.disc.nfcid3, RFAL_NFCDEP_NFCID3_LEN);
        targetParam.bst       = RFAL_NFCDEP_Bx_NO_HIGH_BR;
        targetParam.brt       = RFAL_NFCDEP_Bx_NO_HIGH_BR;
        targetParam.to        = RFAL_NFCDEP_WT_TRG_MAX_L13; /* [LLCP] 1.3 6.2.1 */ 
        targetParam.ppt       = rfalNfcDepLR2PP(gNfcDev.disc.nfcDepLR);
        if( gNfcDev.disc.GBLen >= RFAL_NFCDEP_GB_MAX_LEN )
        {
            return RFAL_ERR_PARAM;
        }
        targetParam.GBtLen    = gNfcDev.disc.GBLen;
        if( gNfcDev.disc.GBLen > 0U )
        {
            RFAL_MEMCPY(targetParam.GBt, gNfcDev.disc.GB, gNfcDev.disc.GBLen);
        }
        targetParam.operParam = (RFAL_NFCDEP_OPER_FULL_MI_EN | RFAL_NFCDEP_OPER_EMPTY_DEP_DIS | RFAL_NFCDEP_OPER_ATN_EN | RFAL_NFCDEP_OPER_RTOX_REQ_EN);
        targetParam.commMode  = commMode;
            
        
        /* Set activation buffer (including header) for NFC-DEP */
        actvParams.rxBuf        = (rfalNfcDepBufFormat*) &gNfcDev.rxBuf.nfcDepBuf;   /*  PRQA S 0310 # MISRA 11.3 - Intentional safe cast to avoiding large buffer duplication */
        actvParams.rxLen        = &gNfcDev.rxLen;
        actvParams.isRxChaining = &gNfcDev.isRxChaining;
        actvParams.nfcDepDev    = &gNfcDev.devList->proto.nfcDep;

        rfalListenSetState( ((device->type == RFAL_NFC_POLL_TYPE_NFCA) ? RFAL_LM_STATE_TARGET_A : RFAL_LM_STATE_TARGET_F) );
        
        rfalNfcDepInitialize();
        /* Perform NFC-DEP (P2P) activation: send ATR_RES and handle activation */
        return rfalNfcDepListenStartActivation( &targetParam, atrReq, atrReqLen, actvParams );
    }
#endif  /* RFAL_FEATURE_LISTEN_MODE */
    
    else
    {
        return RFAL_ERR_INTERNAL;
    }
}
#endif /* RFAL_FEATURE_NFC_DEP */


/*!
 ******************************************************************************
 * \brief Poller NFC Deactivate
 * 
 * This method Deactivates the device if a deactivation procedure exists 
 * 
 * \return  RFAL_ERR_NONE  : Operation completed with no error
 * \return  RFAL_ERR_BUSY  : Operation ongoing
 * \return  RFAL_ERR_XXXX  : Error occurred
 * 
 ******************************************************************************
 */
static ReturnCode rfalNfcDeactivation( void )
{
    bool       aux;
    ReturnCode ret;
    
    ret = RFAL_ERR_NONE;
    aux = false;
    
    /* Suppress warning when specific RFAL features have been disabled */
    RFAL_NO_WARNING( ret );
    
    
    /* Check if a device has been activated */
    if( gNfcDev.activeDev != NULL )
    {
        if( rfalNfcIsRemDevListener( gNfcDev.activeDev->type ) )                          /* Listen mode no additional deactivation to be performed*/
        {
            switch( gNfcDev.activeDev->rfInterface )
            {
                /*******************************************************************************/
                case RFAL_NFC_INTERFACE_RF:
                    break;                                                                /* No specific deactivation to be performed */
                
                /*******************************************************************************/
            #if RFAL_FEATURE_ISO_DEP && RFAL_FEATURE_ISO_DEP_POLL
                case RFAL_NFC_INTERFACE_ISODEP:
                    
                    if( !gNfcDev.isOperOngoing )
                    {
                        ret = rfalIsoDepStartDeselect();
                        if( ret == RFAL_ERR_NONE )                                        /* Send a Deselect to device */
                        {
                            gNfcDev.isOperOngoing = true;
                            return RFAL_ERR_BUSY;
                        }
                    }
                    else
                    {
                        RFAL_EXIT_ON_BUSY( ret, rfalIsoDepGetDeselectStatus() );          /* Check if deselection has finished */
                        
                        aux                   = true;                                     /* Mark device as deselected */
                        gNfcDev.isOperOngoing = false;
                    }
                    break;
            #endif /* RFAL_FEATURE_ISO_DEP_POLL */
                    
                /*******************************************************************************/
            #if RFAL_FEATURE_NFC_DEP
                case RFAL_NFC_INTERFACE_NFCDEP:
                    switch ( gNfcDev.activeDev->type )
                    {
                        case RFAL_NFC_LISTEN_TYPE_AP2P:
                            rfalNfcDepRLS();                                              /* Send a Release to device */
                            break;

                        default:
                            rfalNfcDepDSL();                                              /* Send a Deselect to device */
                            aux = true;                                                   /* Mark device as deselected */
                            break;
            
                    }
                    break;
            #endif /* RFAL_FEATURE_NFC_DEP */
                    
                default:
                    return RFAL_ERR_REQUEST;
            }
        }
    }
    
    /* If deactivation type is only to Sleep, mark it and keep Field On  */
    if( (gNfcDev.deactType == RFAL_NFC_DEACTIVATE_SLEEP) && (gNfcDev.activeDev != NULL) && (aux) )
    {
        gNfcDev.isOperOngoing = false;
        
        
        if( gNfcDev.activeDev->type == RFAL_NFC_LISTEN_TYPE_NFCA )
        {
            gNfcDev.activeDev->dev.nfca.isSleep = true;
        }
        else if( gNfcDev.activeDev->type == RFAL_NFC_LISTEN_TYPE_NFCB )
        {
            gNfcDev.activeDev->dev.nfcb.isSleep = true;
        }
        else
        {
            /* MISRA 15.7 - Empty else */
        }
    }
    else
    {
        if( !gNfcDev.isDeactivating )                                                            /* Check if the Field deactivation has not started */
        {
        #if RFAL_FEATURE_WAKEUP_MODE
            rfalWakeUpModeStop();
        #endif /* RFAL_FEATURE_WAKEUP_MODE */
        
        #if RFAL_FEATURE_LISTEN_MODE
            rfalListenStop();
        #else
            rfalFieldOff();
        #endif
         
            if( (gNfcDev.isFieldOn) && rfalNfcHasPollerTechs() )                                 /* Check if configured to Poll modes and the Field is On */
            {
                aux = platformTimerIsExpired(gNfcDev.discTmr);                                   /* Check total duration timer is already expired */
                if( ((platformGetSysTick() + RFAL_NFC_T_FIELD_OFF) > gNfcDev.discTmr) || (aux) ) /* In case Total Duration has expired or expring in less than tFIELD_OFF */
                {
                    platformTimerDestroy( gNfcDev.discTmr );
                    gNfcDev.discTmr = (uint32_t)platformTimerCreate( RFAL_NFC_T_FIELD_OFF );     /* Ensure that Operating Field is in Off condition at least tFIELD_OFF */
                }
                
                gNfcDev.isDeactivating = true;
                return RFAL_ERR_BUSY;
            }
        }
        else                                                                                     /* The Field deactivation has started */
        {
            if( !platformTimerIsExpired(gNfcDev.discTmr) )
            {
                return RFAL_ERR_BUSY;                                                            /* Ensure Operating Field in Off condition for the time remaining */
            }
        }
    }
    
    gNfcDev.activeDev      = NULL;                                                               /* Clear Active Device info */
    gNfcDev.isDeactivating = false;
    gNfcDev.isTechInit     = false;
    gNfcDev.isFieldOn      = false;
    return RFAL_ERR_NONE;
}

