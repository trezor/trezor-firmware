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

/*! \file rfal_cd.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief RFAL Card Detection
 *
 *  This module implements the Card Detection Algorithm. 
 *  It may be used for applications that require to identify if a card is on 
 *  the vicinity of the NFC antenna, for example: to protect cards against 
 *  damage by a wireless charger (WPC Qi PTx).
 *
 *  Algorith details
 *  - The algorithm treats multiple devices as if a card is present 
 *  - The algorithm will identify cards by the following distinguishing features
 *     - Only cards support NFC-V or other non standard technologies (ST25TB, ...)
 *     - Compliant cards support only a single technology
 *  - The algorithm will identify phones by the following distinguishing features
 *     - Only phones support P2P (NFC-DEP)
 *     - Only phones are able to communicate on different NFC technologies
 *
 */

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_cd.h"
#include "rfal_rf.h"
#include "rfal_nfca.h"
#include "rfal_nfcb.h"
#include "rfal_nfcf.h"
#include "rfal_nfcv.h"
#include "rfal_st25tb.h"

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

#define RFAL_CD_NFCF_DEVLIMIT       4U    /*!<  NFC-F device limit (TechDet aligned)   */

/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/

/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! Card Detection states                                                              */
typedef enum{
    RFAL_CD_ST_IDLE,                      /*!<  CD idle                                */
    RFAL_CD_ST_START,                     /*!<  CD starting                            */
    RFAL_CD_ST_NFCA_INIT,                 /*!<  NFC-A Initialization                   */
    RFAL_CD_ST_NFCA_TECHDET,              /*!<  NFC-A Technology Detection             */
    RFAL_CD_ST_NFCA_COLRES_START,         /*!<  NFC-A Collision Resolution starting    */
    RFAL_CD_ST_NFCA_COLRES,               /*!<  NFC-A Collision Resolution             */
    RFAL_CD_ST_NFCB_INIT,                 /*!<  NFC-B Initialization                   */
    RFAL_CD_ST_NFCB_TECHDET,              /*!<  NFC-B Technology Detection             */
    RFAL_CD_ST_NFCB_COLRES_START,         /*!<  NFC-B Collision Resolution starting    */
    RFAL_CD_ST_NFCB_COLRES,               /*!<  NFC-B Collision Resolution             */
    RFAL_CD_ST_NFCF_INIT,                 /*!<  NFC-F Initialization                   */
    RFAL_CD_ST_NFCF_TECHDET_START,        /*!<  NFC-F Technology Detection starting    */
    RFAL_CD_ST_NFCF_TECHDET,              /*!<  NFC-F Technology Detection             */
    RFAL_CD_ST_NFCF_COLRES_START,         /*!<  NFC-F Collision Resolution starting    */
    RFAL_CD_ST_NFCF_COLRES,               /*!<  NFC-F Collision Resolution             */
    RFAL_CD_ST_NFCV_INIT,                 /*!<  NFC-V Initialization                   */
    RFAL_CD_ST_NFCV_TECHDET,              /*!<  NFC-V Technology Detection             */
    RFAL_CD_ST_NFCV_COLRES_START,         /*!<  NFC-V Collision Resolution starting    */
    RFAL_CD_ST_NFCV_COLRES,               /*!<  NFC-V Collision Resolution             */
    RFAL_CD_ST_PROPRIETARY,               /*!<  Proprietary NFC Technologies starting  */
    RFAL_CD_ST_ST25TB_INIT,               /*!<  ST25TB Initialization                  */
    RFAL_CD_ST_ST25TB_TECHDET,            /*!<  ST25TB Technology Detection            */
    RFAL_CD_ST_CHECK_PROTO,               /*!<  Evaluate device(s) found and protocols */
    RFAL_CD_ST_HB_START,                  /*!<  Heartbeat Detection start | Field reset*/
    RFAL_CD_ST_HB,                        /*!<  Heartbeat Detection                    */
    RFAL_CD_ST_DETECTED,                  /*!<  CD completed: card detected            */
    RFAL_CD_ST_NOT_DETECTED,              /*!<  CD completed: No card detected         */
    RFAL_CD_ST_ERROR                      /*!<  Error during card detection            */
}rfalCdState;


/*! Card Detection context                                                             */
typedef struct{
    rfalCdState           st;             /*!<  CD state                               */
    ReturnCode            lastErr;        /*!<  Last occured error                     */
    rfalNfcaListenDevice  nfcaDev;        /*!<  NFC-A Device Info                      */
    rfalNfcbListenDevice  nfcbDev;        /*!<  NFC-B Device Info                      */
    rfalNfcfListenDevice  nfcfDev[RFAL_CD_NFCF_DEVLIMIT]; /*!< NFC-F Device Info       */
    uint8_t               devCnt;         /*!<  Tech device counter                    */
    uint8_t               mulDevCnt;      /*!<  Multi Tech device counter              */
    rfalCdTech            techFound;      /*!<  First NFC Technology found             */
    bool                  skipTechFound;  /*!<  Second round ongoing, skip techFound   */
    rfalCdRes             *res;           /*!<  Card Detection output result location  */
    uint32_t              tmr;            /*!<  Field reset timer                      */
}rfalCdCtx;


/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

static rfalCdCtx gCd;


/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/
#ifdef RFAL_CD_HB
extern bool rfalCdHbDetect( rfalCdTech tech );
#endif /* RFAL_CD_HB */
    
/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES
******************************************************************************
*/

/*******************************************************************************/
ReturnCode rfalCdDetectCard( rfalCdRes *result )
{
    ReturnCode err;
    
    RFAL_EXIT_ON_ERR( err, rfalCdStartDetectCard( result ) );
    rfalRunBlocking( err, rfalCdGetDetectCardStatus() );
    
    return err;
}


/*******************************************************************************/
ReturnCode rfalCdStartDetectCard( rfalCdRes *result )
{
    if( result == NULL )
    {
        return RFAL_ERR_PARAM;
    }
        
    gCd.st  = RFAL_CD_ST_START;
    gCd.res = result;
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalCdGetDetectCardStatus( void )
{
    ReturnCode            err;
    rfalNfcaSensRes       sensRes;
    rfalNfcbSensbRes      sensbRes;
    rfalNfcvInventoryRes  invRes;
    
    
    switch( gCd.st )
    {
        /*******************************************************************************/
        case RFAL_CD_ST_START:
            
            gCd.mulDevCnt     = 0;                             /* Initialize Card Detection context */
            gCd.skipTechFound = false;
            gCd.techFound     = RFAL_CD_TECH_NONE;
            gCd.tmr           = RFAL_TIMING_NONE;
        
            gCd.st = RFAL_CD_ST_NFCA_INIT;
            break;
        
        
        /*******************************************************************************/
        case RFAL_CD_ST_NFCA_INIT:
            
            /* Verify if we are performing multi technology check */
            if( (gCd.skipTechFound) )
            {
                /* If staring multi technology check if field has been Off long enough */
                if( (!platformTimerIsExpired(gCd.tmr)) )
                {
                    break;
                }
                
                if( gCd.techFound == RFAL_CD_TECH_NFCA )
                {
                    gCd.st = RFAL_CD_ST_NFCB_INIT;             /* If single card card found before was NFC-A skip tech now */
                    break;
                }
            }
            
            rfalNfcaPollerInitialize();                        /* Initialize for NFC-A */
            err = rfalFieldOnAndStartGT();                     /* Turns the Field On if not already and start GT timer */
            if( err != RFAL_ERR_NONE )
            {
                gCd.lastErr = err;
                gCd.st      = RFAL_CD_ST_ERROR;                /* Unable to turn the field On, cannot continue Card Detection */
                break;
            }
        
            gCd.st = RFAL_CD_ST_NFCA_TECHDET;
            break;
        
            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCA_TECHDET:
            
            if( !rfalIsGTExpired() )
            {
                break;                                         /* Wait until GT has been fulfilled */
            }
            
            err = rfalNfcaPollerTechnologyDetection( RFAL_COMPLIANCE_MODE_ISO, &sensRes );
            if( err == RFAL_ERR_NONE )
            {
                if( gCd.skipTechFound )                        /* Verify if we are performing multi technology check */
                {
                    gCd.res->detType =  RFAL_CD_SINGLE_MULTI_TECH;
                    gCd.st           = RFAL_CD_ST_NOT_DETECTED;/* Single device was another technology and now NFC-A */
                    break;
                }
                    
                gCd.st = RFAL_CD_ST_NFCA_COLRES_START;         /* NFC-A detected perform collision resolution */
                break;
            }
            
            gCd.st = RFAL_CD_ST_NFCB_INIT;                     /* NFC-A not detected, move to NFC-B */
            break;
            
            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCA_COLRES_START:
            
            err = rfalNfcaPollerStartFullCollisionResolution( RFAL_COMPLIANCE_MODE_ISO, 0, &gCd.nfcaDev, &gCd.devCnt );
            if( err != RFAL_ERR_NONE )
            {
                gCd.lastErr = err;
                gCd.st      = RFAL_CD_ST_ERROR;                /* Collision resolution could not be performed */
                break;
            }
            
            gCd.st = RFAL_CD_ST_NFCA_COLRES;
            break;
            
        
        /*******************************************************************************/
        case RFAL_CD_ST_NFCA_COLRES:
            
            err = rfalNfcaPollerGetFullCollisionResolutionStatus();
            if( err != RFAL_ERR_BUSY )
            {
                if( (err == RFAL_ERR_NONE) && (gCd.devCnt == 1U) )  /* Collision resolution OK and a single card was found */
                {
                    gCd.mulDevCnt++;
                    gCd.techFound = RFAL_CD_TECH_NFCA;
                }
                
                /* Check if multiple cards or technologies have already been identified */
                if( (err != RFAL_ERR_NONE) || (gCd.devCnt > 1U) || (gCd.mulDevCnt > 1U) )
                {
                    gCd.res->detType = RFAL_CD_MULTIPLE_DEV;   /* Report multiple devices. A T1T will also fail at ColRes */
                    gCd.st           = RFAL_CD_ST_DETECTED;
                    
                    break;
                }
                
                gCd.st = RFAL_CD_ST_NFCB_INIT;                 /* Move to NFC-B */
            }
            break;
            
            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCB_INIT:
        
            /* Verify if we are performing multi technology check */
            if( (gCd.skipTechFound) && (gCd.techFound == RFAL_CD_TECH_NFCB) )
            {
                gCd.st = RFAL_CD_ST_NFCF_INIT;                 /* If single card card found before was NFC-B skip tech now */
                break;
            }
        
            rfalNfcbPollerInitialize();                        /* Initialize for NFC-B */
            rfalFieldOnAndStartGT();                           /* Turns the Field On if not already and start GT timer */
        
            gCd.st = RFAL_CD_ST_NFCB_TECHDET;
            break;
        
            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCB_TECHDET:
            
            if( !rfalIsGTExpired() )
            {
                break;                                         /* Wait until GT has been fulfilled */
            }
            
            err = rfalNfcbPollerTechnologyDetection( RFAL_COMPLIANCE_MODE_NFC, &sensbRes, &gCd.devCnt );
            if( err == RFAL_ERR_NONE )
            {
                /* Verify if we are performing multi technology check OR already found one on the first round */
                if( gCd.skipTechFound ) 
                {
                    gCd.res->detType = RFAL_CD_SINGLE_MULTI_TECH;
                    gCd.st           = RFAL_CD_ST_NOT_DETECTED;/* Single device was another technology and now NFC-B */
                    break;                                     
                }
                else if( gCd.techFound != RFAL_CD_TECH_NONE )  /* If on the first round check if other Tech was already found */
                {
                    gCd.res->detType =  RFAL_CD_MULTIPLE_TECH;
                    gCd.st           =  RFAL_CD_ST_DETECTED;
                    break;
                }
                else
                {
                    /* MISRA 15.7 - Empty else */
                }

                gCd.st = RFAL_CD_ST_NFCB_COLRES_START;         /* NFC-B detected perform collision resolution */
                break;                                         
            }                                                  
                                                               
            gCd.st = RFAL_CD_ST_NFCF_INIT;                     /* NFC-B not detected, move to NFC-B */
            break;

            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCB_COLRES_START:
            
            err = rfalNfcbPollerStartCollisionResolution( RFAL_COMPLIANCE_MODE_NFC, 0, &gCd.nfcbDev, &gCd.devCnt );
            if( err != RFAL_ERR_NONE )
            {
                gCd.lastErr = err;
                gCd.st      = RFAL_CD_ST_ERROR;                /* Collision resolution could not be performed */
                break;
            }
            
            gCd.st = RFAL_CD_ST_NFCB_COLRES;
            break;
        
            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCB_COLRES:
            
            err = rfalNfcbPollerGetCollisionResolutionStatus();
            if( err != RFAL_ERR_BUSY )
            {
                if( (err == RFAL_ERR_NONE) && (gCd.devCnt == 1U) )  /* Collision resolution OK and a single card was found */
                {
                    gCd.mulDevCnt++;
                    gCd.techFound = RFAL_CD_TECH_NFCB;
                }
                
                /* Check if multiple cards or technologies have already been identified */
                if( (err != RFAL_ERR_NONE) || (gCd.devCnt > 1U) || (gCd.mulDevCnt > 1U) )
                {
                    gCd.res->detType = RFAL_CD_MULTIPLE_DEV;
                    gCd.st           = RFAL_CD_ST_DETECTED;
                    break;
                }
        
                gCd.st = ( (RFAL_SUPPORT_MODE_POLL_NFCF) ? RFAL_CD_ST_NFCF_INIT : RFAL_CD_ST_NFCV_INIT);    /* Move to NFC-F or NFC-V */
            }
            break;
            
            
    #if RFAL_SUPPORT_MODE_POLL_NFCF
        /*******************************************************************************/
        case RFAL_CD_ST_NFCF_INIT:
            
            /* Verify if we are performing multi technology check */
            if( (gCd.skipTechFound) && (gCd.techFound == RFAL_CD_TECH_NFCF) )
            {
                gCd.st = RFAL_CD_ST_PROPRIETARY;               /* If single card card found before was NFC-F skip tech now */
                break;
            }
            
            rfalNfcfPollerInitialize(RFAL_BR_212);             /* Initialize for NFC-F */
            rfalFieldOnAndStartGT();                           /* Turns the Field On if not already and start GT timer */
        
            gCd.st = RFAL_CD_ST_NFCF_TECHDET_START;
            break;
            
        
        /*******************************************************************************/    
        case RFAL_CD_ST_NFCF_TECHDET_START:
            if( !rfalIsGTExpired() )
            {
                break;                                         /* Wait until GT has been fulfilled */
            }
            
            err = rfalNfcfPollerStartCheckPresence();
            gCd.st = RFAL_CD_ST_NFCF_TECHDET;
            break;
        
            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCF_TECHDET:
            
            err = rfalNfcfPollerGetCheckPresenceStatus();
            if( err == RFAL_ERR_BUSY )
            {
                break;                                         /* Wait until NFC-F Technlogy Detection is completed */
            }
            
            if( gCd.skipTechFound )                            /* Verify if we are performing multi technology check */
            {
                gCd.st = RFAL_CD_ST_PROPRIETARY;
                
                /* If single device was another technology and now NFC-F, otherwise conclude*/
                if(err == RFAL_ERR_NONE)
                {
                    gCd.res->detType =  RFAL_CD_SINGLE_MULTI_TECH;
                    gCd.st           =  RFAL_CD_ST_NOT_DETECTED;
                }
                break;
            }
            
            if( err == RFAL_ERR_NONE )
            {
                if( gCd.techFound != RFAL_CD_TECH_NONE )       /* If on the first round check if other Tech was already found */
                {
                    gCd.res->detType =  RFAL_CD_MULTIPLE_TECH;
                    gCd.st           =  RFAL_CD_ST_DETECTED;
                    break;
                }
                
                gCd.st = RFAL_CD_ST_NFCF_COLRES_START;         /* NFC-F detected, perform collision resolution */
                break;                                         
            }
            
            gCd.st = RFAL_CD_ST_NFCV_INIT;                     /* NFC-F not detected, move to NFC-V */
            break;

        
        /*******************************************************************************/
        case RFAL_CD_ST_NFCF_COLRES_START:
            
            err = rfalNfcfPollerStartCollisionResolution( RFAL_COMPLIANCE_MODE_NFC, RFAL_CD_NFCF_DEVLIMIT, gCd.nfcfDev, &gCd.devCnt );
            if( err != RFAL_ERR_NONE )
            {
                gCd.lastErr = err;
                gCd.st      = RFAL_CD_ST_ERROR;                /* Collision resolution could not be performed */
                break;
            }
            
            gCd.st = RFAL_CD_ST_NFCF_COLRES;
            break;
        
        
        /*******************************************************************************/
        case RFAL_CD_ST_NFCF_COLRES:
            
            err = rfalNfcfPollerGetCollisionResolutionStatus();
            if( err != RFAL_ERR_BUSY )
            {
                if( (err == RFAL_ERR_NONE) && (gCd.devCnt == 1U) )  /* Collision resolution OK and a single card was found */
                {
                    gCd.mulDevCnt++;
                    gCd.techFound = RFAL_CD_TECH_NFCF;
                }
                
                /* Check if multiple cards or technologies have already been identified */
                if( (err != RFAL_ERR_NONE) || (gCd.devCnt > 1U) || (gCd.mulDevCnt > 1U) )
                {
                    gCd.res->detType = RFAL_CD_MULTIPLE_DEV;
                    gCd.st           = RFAL_CD_ST_DETECTED;
                    break;
                }
                
                gCd.st = RFAL_CD_ST_NFCV_INIT;                 /* Move to NFC-V */
            }
            break;
    #endif /* RFAL_SUPPORT_MODE_POLL_NFCF*/
            
        /*******************************************************************************/
        case RFAL_CD_ST_NFCV_INIT:
            
            rfalNfcvPollerInitialize();                        /* Initialize for NFC-V */
            rfalFieldOnAndStartGT();                           /* Turns the Field On if not already and start GT timer */
        
            gCd.st = RFAL_CD_ST_NFCV_TECHDET;
            break;
        
        /*******************************************************************************/
        case RFAL_CD_ST_NFCV_TECHDET:
            
            if( !rfalIsGTExpired() )
            {
                break;                                         /* Wait until GT has been fulfilled */
            }                                                            
                                                                         
            err = rfalNfcvPollerCheckPresence( &invRes );            
            if( err == RFAL_ERR_NONE )
            {
                if( gCd.techFound != RFAL_CD_TECH_NONE )       /* If other Tech was already found */
                {
                    gCd.res->detType =  RFAL_CD_MULTIPLE_TECH;
                    gCd.st           =  RFAL_CD_ST_DETECTED;
                    break;
                }
                
                gCd.techFound    = RFAL_CD_TECH_NFCV;          /* If NFC-V is regarded as card as CE NFC-V is currently not supported by active devices */
                gCd.res->detType = RFAL_CD_CARD_TECH;
                gCd.st           = RFAL_CD_ST_DETECTED;                  
                break;                                                   
            }                                                            
                                                                         
            gCd.st = RFAL_CD_ST_PROPRIETARY;                   /* Move to Proprietary NFC Technologies  */
            break;
        
        
        /*******************************************************************************/
        case RFAL_CD_ST_PROPRIETARY:
        
            rfalFieldOff();
            platformTimerDestroy( gCd.tmr );
            gCd.tmr = platformTimerCreate( (uint8_t)rfalConv1fcToMs(RFAL_GT_NFCA) );
        
            /* If none of the other NFC technologies was not seen on a second round, regard as card */
            if( gCd.skipTechFound )
            {
                gCd.res->detType = RFAL_CD_SINGLE_DEV;
                gCd.st           = RFAL_CD_ST_DETECTED;
                
                
                /*******************************************************************************/
                /* Only one device found which does not support NFC-DEP and only               *
                 * answered in one technology, perform heartbeat detection                     */
                
            #ifdef RFAL_CD_HB
                gCd.st = RFAL_CD_ST_HB_START;
            #endif /* RFAL_CD_HB */
                
                /*******************************************************************************/
                
                break;
            }
        
            gCd.st = RFAL_CD_ST_ST25TB_INIT;
            break;
        
        
        /*******************************************************************************/
        case RFAL_CD_ST_ST25TB_INIT:
            
            if( (!platformTimerIsExpired( gCd.tmr )) )         /* Check if field has been Off long enough */
            {                                                            
                break;                                                   
            }                                                            
                                                                         
            rfalSt25tbPollerInitialize();                      /* Initialize for ST25TB */
            err = rfalFieldOnAndStartGT();                     /* Turns the Field On if not already and start GT timer */
                                                               
            if( err != RFAL_ERR_NONE )
            {                                                  
                gCd.lastErr = err;
                gCd.st      = RFAL_CD_ST_ERROR;                /* Unable to turn the field On, cannot continue Card Detection */
                break;
            }
        
            gCd.st = RFAL_CD_ST_ST25TB_TECHDET;
            break;
        
        
        /*******************************************************************************/
        case RFAL_CD_ST_ST25TB_TECHDET:
            
            if( (!rfalIsGTExpired()) )
            {
                break;                                         /* Wait until GT has been fulfilled */
            }                                                  
                                                               
            err = rfalSt25tbPollerCheckPresence( NULL );       
            if( err == RFAL_ERR_NONE )                              
            {                                                  
                gCd.techFound    = RFAL_CD_TECH_OTHER;         /* If ST25TB is regarded as card as CE is not supported by active devices */
                gCd.res->detType = RFAL_CD_CARD_TECH;
                gCd.st           = RFAL_CD_ST_DETECTED;
                break;
            }
            
            gCd.st = RFAL_CD_ST_CHECK_PROTO;
            break;
        
        
        /*******************************************************************************/
        case RFAL_CD_ST_CHECK_PROTO:

            if( gCd.mulDevCnt == 0U )                          /* No NFC listener has been detected */
            {
                gCd.res->detType = RFAL_CD_NOT_FOUND;
                gCd.st           = RFAL_CD_ST_NOT_DETECTED;
                break;
            }
            
            if( gCd.mulDevCnt == 1U )                          /* A single NFC listener has been identified */
            {
                /* Check if it supports NFC-DEP protocol */
                if( ( (gCd.techFound == RFAL_CD_TECH_NFCA) && ((gCd.nfcaDev.type == RFAL_NFCA_NFCDEP) || (gCd.nfcaDev.type == RFAL_NFCA_T4T_NFCDEP)) ) ||
                    ( (gCd.techFound == RFAL_CD_TECH_NFCF) && rfalNfcfIsNfcDepSupported( &gCd.nfcfDev[0] ) )                                               )
                {
                    gCd.res->detType = RFAL_CD_SINGLE_P2P;
                    gCd.st           = RFAL_CD_ST_NOT_DETECTED;/* NFC-DEP supported, regarded as non passive card */
                    break;
                }
                
                /*  If a single NFC listener has been detected, and did not announce NFC-DEP support,  *
                 *  check if it supports mutiple NFC technologies (skip the one it was previous seen)  */
                gCd.skipTechFound = true;
                gCd.st = RFAL_CD_ST_NFCA_INIT;
                
                /* Reset Field once again to avoid unwanted effect of Proprietary NFC Tech modulation */
                rfalFieldOff();
                platformTimerDestroy( gCd.tmr );
                gCd.tmr = platformTimerCreate( (uint8_t)rfalConv1fcToMs(RFAL_GT_NFCA) );
                break;
            }
        
        gCd.res->detType = RFAL_CD_MULTIPLE_DEV;
        gCd.st           = RFAL_CD_ST_DETECTED;
        break;
            
            
    #ifdef RFAL_CD_HB
        /*******************************************************************************/
        case RFAL_CD_ST_HB_START:
            
            if( (!platformTimerIsExpired( gCd.tmr )) )         /* Check if field has been Off long enough */
            {
                break;
            }
            
            switch( gCd.techFound )
            {
                case RFAL_CD_TECH_NFCF:
                    rfalNfcfPollerInitialize( RFAL_BR_212 );
                    break;
                
                case RFAL_CD_TECH_NFCB:
                    rfalNfcbPollerInitialize();
                    break;

                case RFAL_CD_TECH_NFCA:
                default:
                    rfalNfcaPollerInitialize();
                    break;
            }
            
            err = rfalFieldOnAndStartGT();
            if( err != RFAL_ERR_NONE )
            {                                                  
                gCd.lastErr = err;
                gCd.st      = RFAL_CD_ST_ERROR;                /* Unable to turn the field On, cannot continue Card Detection */
                break;
            }
            
            gCd.st = RFAL_CD_ST_HB;
            break;
        
        
        /*******************************************************************************/
        case RFAL_CD_ST_HB:
            if( !rfalIsGTExpired() )                           /* Check if GT has been fulfilled */
            {
                break;
            }
            
            if( rfalCdHbDetect( gCd.techFound ) )              /* Perform tha heartbeat detection sequence */
            {
                gCd.res->detType = RFAL_CD_SINGLE_HB;
                gCd.st           = RFAL_CD_ST_NOT_DETECTED;    /* Single device performing ALM, no passive card */
                break;
            }
            
            gCd.res->detType = RFAL_CD_SINGLE_DEV;
            gCd.st           = RFAL_CD_ST_DETECTED;            /* ALM not detected on single device, regard as card */
            break;
    #endif /* RFAL_CD_HB */
            

        /*******************************************************************************/
        case RFAL_CD_ST_DETECTED:
        case RFAL_CD_ST_NOT_DETECTED:
            
            /* Card Detection completed, return outcome */
            gCd.res->detected = ((gCd.st == RFAL_CD_ST_NOT_DETECTED) ? false : true);
            
            rfalFieldOff();
            gCd.st = RFAL_CD_ST_IDLE;
            
            return RFAL_ERR_NONE;
        
        
        /*******************************************************************************/        
        case RFAL_CD_ST_IDLE:
            return RFAL_ERR_WRONG_STATE;
        
        
        /*******************************************************************************/        
        case RFAL_CD_ST_ERROR:
            
            gCd.res->detType  = RFAL_CD_UNKOWN; 
            gCd.res->detected = true;                          /* Error ocurred, mark as card present to avoid damage */
        
            rfalFieldOff();
            gCd.st = RFAL_CD_ST_IDLE;
        
            return gCd.lastErr;
            
        
        /*******************************************************************************/
        default:
            return RFAL_ERR_INTERNAL;
    }
    
    return RFAL_ERR_BUSY;
}

