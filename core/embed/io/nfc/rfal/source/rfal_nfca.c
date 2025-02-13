
/******************************************************************************
  * @attention
  *
  * COPYRIGHT 2016 STMicroelectronics, all rights reserved
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
 *      PROJECT:   ST25R391x firmware
 *      Revision:
 *      LANGUAGE:  ISO C99
 */

/*! \file rfal_nfca.c
 *
 *  \author Gustavo Patricio
 *
 *  \brief Provides several NFC-A convenience methods and definitions
 *  
 *  It provides a Poller (ISO14443A PCD) interface and as well as 
 *  some NFC-A Listener (ISO14443A PICC) helpers.
 *
 *  The definitions and helpers methods provided by this module are only
 *  up to ISO14443-3 layer
 *  
 */

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_nfca.h"
#include "rfal_utils.h"

/*
 ******************************************************************************
 * ENABLE SWITCH
 ******************************************************************************
 */

/* Feature switch may be enabled or disabled by user at rfal_platform.h 
 * Default configuration (ST25R dependant) also provided at rfal_defConfig.h
 *  
 *    RFAL_FEATURE_NFCA
 */

#if RFAL_FEATURE_NFCA

/*
 ******************************************************************************
 * GLOBAL DEFINES
 ******************************************************************************
 */

#define RFAL_NFCA_SLP_FWT           rfalConvMsTo1fc(1)    /*!< Check 1ms for any modulation  ISO14443-3 6.4.3   */
#define RFAL_NFCA_SLP_CMD           0x50U                 /*!< SLP cmd (byte1)    Digital 1.1  6.9.1 & Table 20 */
#define RFAL_NFCA_SLP_BYTE2         0x00U                 /*!< SLP byte2          Digital 1.1  6.9.1 & Table 20 */
#define RFAL_NFCA_SLP_CMD_POS       0U                    /*!< SLP cmd position   Digital 1.1  6.9.1 & Table 20 */
#define RFAL_NFCA_SLP_BYTE2_POS     1U                    /*!< SLP byte2 position Digital 1.1  6.9.1 & Table 20 */

#define RFAL_NFCA_SDD_CT            0x88U                 /*!< Cascade Tag value Digital 1.1 6.7.2              */
#define RFAL_NFCA_SDD_CT_LEN        1U                    /*!< Cascade Tag length                               */

#define RFAL_NFCA_SLP_REQ_LEN       2U                    /*!< SLP_REQ length                                   */

#define RFAL_NFCA_SEL_CMD_LEN       1U                    /*!< SEL_CMD length                                   */
#define RFAL_NFCA_SEL_PAR_LEN       1U                    /*!< SEL_PAR length                                   */
#define RFAL_NFCA_SEL_SELPAR        rfalNfcaSelPar(7U, 0U)/*!< SEL_PAR on Select is always with 4 data/nfcid    */
#define RFAL_NFCA_BCC_LEN           1U                    /*!< BCC length                                       */

#define RFAL_NFCA_SDD_REQ_LEN       (RFAL_NFCA_SEL_CMD_LEN + RFAL_NFCA_SEL_PAR_LEN)   /*!< SDD_REQ length       */
#define RFAL_NFCA_SDD_RES_LEN       (RFAL_NFCA_CASCADE_1_UID_LEN + RFAL_NFCA_BCC_LEN) /*!< SDD_RES length       */

#define RFAL_NFCA_T_RETRANS         5U                    /*!< t RETRANSMISSION [3, 33]ms   EMVCo 2.6  A.5      */
#define RFAL_NFCA_N_RETRANS         2U                    /*!< Number of retries            EMVCo 2.6  9.6.1.3  */
 

/*! SDD_REQ (Select) Cascade Levels  */
enum
{
    RFAL_NFCA_SEL_CASCADE_L1 = 0,  /*!< SDD_REQ Cascade Level 1 */
    RFAL_NFCA_SEL_CASCADE_L2 = 1,  /*!< SDD_REQ Cascade Level 2 */
    RFAL_NFCA_SEL_CASCADE_L3 = 2   /*!< SDD_REQ Cascade Level 3 */
};

/*! SDD_REQ (Select) request Cascade Level command   Digital 1.1 Table 15 */
enum
{
    RFAL_NFCA_CMD_SEL_CL1 = 0x93, /*!< SDD_REQ command Cascade Level 1 */
    RFAL_NFCA_CMD_SEL_CL2 = 0x95, /*!< SDD_REQ command Cascade Level 2 */
    RFAL_NFCA_CMD_SEL_CL3 = 0x97, /*!< SDD_REQ command Cascade Level 3 */
};

/*
******************************************************************************
* GLOBAL MACROS
******************************************************************************
*/
#define rfalNfcaSelPar( nBy, nbi )         (uint8_t)((((nBy)<<4U) & 0xF0U) | ((nbi)&0x0FU) )         /*!< Calculates SEL_PAR with the bytes/bits to be sent */
#define rfalNfcaCLn2SELCMD( cl )           (uint8_t)((uint8_t)(RFAL_NFCA_CMD_SEL_CL1) + (2U*(cl)))   /*!< Calculates SEL_CMD with the given cascade level   */
#define rfalNfcaNfcidLen2CL( len )         ((len) / 5U)                                              /*!< Calculates cascade level by the NFCID length      */

/*
******************************************************************************
* GLOBAL TYPES
******************************************************************************
*/

/*! Technology Detection context */
typedef struct{
    rfalComplianceMode    compMode;        /*!< Compliancy mode to be used      */
    ReturnCode            ret;             /*!< Outcome of presence check       */
}rfalNfcaTechDetParams;


/*! Colission Resolution states */
typedef enum{
    RFAL_NFCA_CR_IDLE,                      /*!< IDLE state                      */
    RFAL_NFCA_CR_CL,                        /*!< New Cascading Level state       */
    RFAL_NFCA_CR_SDD_TX,                    /*!< Perform anticollsion Tx state   */
    RFAL_NFCA_CR_SDD,                       /*!< Perform anticollsion state      */
    RFAL_NFCA_CR_SEL_TX,                    /*!< Perform CL Selection Tx state   */
    RFAL_NFCA_CR_SEL,                       /*!< Perform CL Selection state      */
    RFAL_NFCA_CR_DONE                       /*!< Collision Resolution done state */
}rfalNfcaColResState;


/*! Full Colission Resolution states */
typedef enum{
    RFAL_NFCA_CR_FULL_START,                /*!< Start Full Collision Resolution state                   */
    RFAL_NFCA_CR_FULL_SLPCHECK,             /*!< Sleep and Check for restart state                       */
    RFAL_NFCA_CR_FULL_RESTART               /*!< Restart Full Collision Resolution state                 */
}rfalNfcaFColResState;


/*! Colission Resolution context */
typedef struct{
    uint8_t               devLimit;         /*!< Device limit to be used                                 */
    rfalComplianceMode    compMode;         /*!< Compliancy mode to be used                              */
    rfalNfcaListenDevice* nfcaDevList;      /*!< Location of the device list                             */
    uint8_t*              devCnt;           /*!< Location of the device counter                          */
    bool                  collPending;      /*!< Collision pending flag                                  */
    
    bool*                 collPend;         /*!< Location of collision pending flag (Single CR)          */
    rfalNfcaSelReq        selReq;           /*!< SelReqused during anticollision (Single CR)             */
    rfalNfcaSelRes*       selRes;           /*!< Location to place of the SEL_RES(SAK) (Single CR)       */
    uint8_t*              nfcId1;           /*!< Location to place the NFCID1 (Single CR)                */
    uint8_t*              nfcId1Len;        /*!< Location to place the NFCID1 length (Single CR)         */
    uint8_t               cascadeLv;        /*!< Current Cascading Level (Single CR)                     */
    rfalNfcaColResState   state;            /*!< Single Collision Resolution state (Single CR)           */
    rfalNfcaFColResState  fState;           /*!< Full Collision Resolution state (Full CR)               */
    uint8_t               bytesTxRx;        /*!< TxRx bytes used during anticollision loop (Single CR)   */
    uint8_t               bitsTxRx;         /*!< TxRx bits used during anticollision loop (Single CR)    */
    uint16_t              rxLen;            /*!< Local reception length                                  */
    uint32_t              tmrFDT;           /*!< FDT timer used between SED_REQs  (Single CR)            */
    uint8_t               retries;          /*!< Retries to be performed upon a timeout error (Single CR)*/
    uint8_t               backtrackCnt;     /*!< Backtrack retries (Single CR)                           */
    bool                  doBacktrack;      /*!< Backtrack flag (Single CR)                              */
}rfalNfcaColResParams;


/*! Colission Resolution context */
typedef struct{
    
    uint8_t               cascadeLv;        /*!< Current Cascading Level                                 */
    uint8_t               fCascadeLv;       /*!< Final Cascading Level                                   */
    rfalNfcaSelRes*       selRes;           /*!< Location to place of the SEL_RES(SAK)                   */
    uint16_t              rxLen;            /*!< Local reception length                                  */
    const uint8_t*        nfcid1;           /*!< Location of the NFCID to be selected                    */
    uint8_t               nfcidOffset;      /*!< Selected NFCID offset                                   */
    bool                  isRx;             /*!< Selection is in reception state                         */
}rfalNfcaSelParams;


/*! SLP_REQ (HLTA) format   Digital 1.1  6.9.1 & Table 20 */
typedef struct
{
    uint8_t      frame[RFAL_NFCA_SLP_REQ_LEN];  /*!< SLP:  0x50 0x00  */
} rfalNfcaSlpReq;


/*! RFAL NFC-A instance */
typedef struct{
    rfalNfcaTechDetParams DT;               /*!< Technology Detection context                            */
    rfalNfcaColResParams  CR;               /*!< Collision Resolution context                            */
    rfalNfcaSelParams     SEL;              /*!< Selection|Activation context                            */
    
    rfalNfcaSlpReq        slpReq;           /*!< SLP_REx buffer                                          */
} rfalNfca;


/*
******************************************************************************
* LOCAL VARIABLES
******************************************************************************
*/
static rfalNfca gNfca;  /*!< RFAL NFC-A instance  */

/*
******************************************************************************
* LOCAL FUNCTION PROTOTYPES
******************************************************************************
*/
static uint8_t    rfalNfcaCalculateBcc( const uint8_t* buf, uint8_t bufLen );
static ReturnCode rfalNfcaPollerStartSingleCollisionResolution( uint8_t devLimit, bool *collPending, rfalNfcaSelRes *selRes, uint8_t *nfcId1, uint8_t *nfcId1Len );
static ReturnCode rfalNfcaPollerGetSingleCollisionResolutionStatus( void );

/*
 ******************************************************************************
 * LOCAL FUNCTIONS
 ******************************************************************************
 */

static uint8_t rfalNfcaCalculateBcc( const uint8_t* buf, uint8_t bufLen )
{
    uint8_t i;
    uint8_t BCC;
    
    BCC = 0;
    
    /* BCC is XOR over first 4 bytes of the SDD_RES  Digital 1.1 6.7.2 */
    for(i = 0; i < bufLen; i++)
    {
        BCC ^= buf[i];
    }
    
    return BCC;
}

/*******************************************************************************/
static ReturnCode rfalNfcaPollerStartSingleCollisionResolution( uint8_t devLimit, bool *collPending, rfalNfcaSelRes *selRes, uint8_t *nfcId1, uint8_t *nfcId1Len )
{
    /* Check parameters */
    if( (collPending == NULL) || (selRes == NULL) || (nfcId1 == NULL) || (nfcId1Len == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Initialize output parameters */
    *collPending = false;  /* Activity 1.1  9.3.4.6 */
    *nfcId1Len   = 0;
    RFAL_MEMSET( nfcId1, 0x00, RFAL_NFCA_CASCADE_3_UID_LEN );
    
    
    /* Save parameters */
    gNfca.CR.devLimit    = devLimit;
    gNfca.CR.collPend    = collPending;
    gNfca.CR.selRes      = selRes;
    gNfca.CR.nfcId1      = nfcId1;
    gNfca.CR.nfcId1Len   = nfcId1Len;

    platformTimerDestroy( gNfca.CR.tmrFDT );
    gNfca.CR.tmrFDT      = RFAL_TIMING_NONE;
    gNfca.CR.retries     = RFAL_NFCA_N_RETRANS;
    gNfca.CR.cascadeLv   = (uint8_t)RFAL_NFCA_SEL_CASCADE_L1;
    gNfca.CR.state       = RFAL_NFCA_CR_CL;
   
    gNfca.CR.doBacktrack  = false;
    gNfca.CR.backtrackCnt = 3U;
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
static ReturnCode rfalNfcaPollerGetSingleCollisionResolutionStatus( void )
{
    ReturnCode ret;
    uint8_t    collBit = 1U;  /* standards mandate or recommend collision bit to be set to One. */
    
    
    /* Check if FDT timer is still running */
    if(gNfca.CR.tmrFDT != RFAL_TIMING_NONE )
    {
        if( (!platformTimerIsExpired( gNfca.CR.tmrFDT )) )
        {
            return RFAL_ERR_BUSY;
        }
    }
    
    /*******************************************************************************/
    /* Go through all Cascade Levels     Activity 1.1  9.3.4 */    
    if( gNfca.CR.cascadeLv > (uint8_t)RFAL_NFCA_SEL_CASCADE_L3 )
    {
        return RFAL_ERR_INTERNAL;
    }
    
    switch( gNfca.CR.state )
    {
        /*******************************************************************************/
        case RFAL_NFCA_CR_CL:
            
            /* Initialize the SDD_REQ to send for the new cascade level */
            RFAL_MEMSET( (uint8_t*)&gNfca.CR.selReq, 0x00, sizeof(rfalNfcaSelReq) );
        
            gNfca.CR.bytesTxRx = RFAL_NFCA_SDD_REQ_LEN;
            gNfca.CR.bitsTxRx  = 0U;
            gNfca.CR.state     = RFAL_NFCA_CR_SDD_TX;
        
            /* fall through */
        
        /*******************************************************************************/
        case RFAL_NFCA_CR_SDD_TX:   /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /* Calculate SEL_CMD and SEL_PAR with the bytes/bits to be sent */
            gNfca.CR.selReq.selCmd = rfalNfcaCLn2SELCMD( gNfca.CR.cascadeLv );
            gNfca.CR.selReq.selPar = rfalNfcaSelPar(gNfca.CR.bytesTxRx, gNfca.CR.bitsTxRx);
        
            /* Send SDD_REQ (Anticollision frame) */
            rfalISO14443AStartTransceiveAnticollisionFrame( (uint8_t*)&gNfca.CR.selReq, &gNfca.CR.bytesTxRx, &gNfca.CR.bitsTxRx, &gNfca.CR.rxLen, RFAL_NFCA_FDTMIN );
        
            gNfca.CR.state = RFAL_NFCA_CR_SDD;
            break;

        
        /*******************************************************************************/
        case RFAL_NFCA_CR_SDD:
            
            RFAL_EXIT_ON_BUSY( ret, rfalISO14443AGetTransceiveAnticollisionFrameStatus() );
        
            /* Retry upon timeout  EMVCo 2.6  9.6.1.3 */
            if( (ret == RFAL_ERR_TIMEOUT) && (gNfca.CR.devLimit==0U) && (gNfca.CR.retries != 0U) )
            {
                gNfca.CR.retries--;
                platformTimerDestroy( gNfca.CR.tmrFDT );
                gNfca.CR.tmrFDT = platformTimerCreate( RFAL_NFCA_T_RETRANS );
                
                gNfca.CR.state = RFAL_NFCA_CR_SDD_TX;
                break;
            }

            /* Covert rxLen into bytes */
            gNfca.CR.rxLen = rfalConvBitsToBytes( gNfca.CR.rxLen );
            
            
            if( (ret == RFAL_ERR_TIMEOUT) && (gNfca.CR.backtrackCnt != 0U) && (!gNfca.CR.doBacktrack)
                && (!((RFAL_NFCA_SDD_REQ_LEN == gNfca.CR.bytesTxRx) && (0U == gNfca.CR.bitsTxRx)))     )
            {
                /* In multiple card scenarios it may always happen that some 
                 * collisions of a weaker tag go unnoticed. If then a later 
                 * collision is recognized and the strong tag has a 0 at the 
                 * collision position then no tag will respond. Catch this 
                 * corner case and then try with the bit being sent as zero. */
                rfalNfcaSensRes sensRes;
                ret = RFAL_ERR_RF_COLLISION;
                rfalNfcaPollerCheckPresence( RFAL_14443A_SHORTFRAME_CMD_REQA, &sensRes );
                /* Algorithm below does a post-increment, decrement to go back to current position */
                if (0U == gNfca.CR.bitsTxRx)
                {
                    gNfca.CR.bitsTxRx = 7;
                    gNfca.CR.bytesTxRx--;
                }
                else
                {
                    gNfca.CR.bitsTxRx--;
                }
                collBit = (uint8_t)( ((uint8_t*)&gNfca.CR.selReq)[gNfca.CR.bytesTxRx] & (1U << gNfca.CR.bitsTxRx) );
                collBit = (uint8_t)((0U==collBit) ? 1U:0U);                              /* Invert the collision bit */
                gNfca.CR.doBacktrack = true;
                gNfca.CR.backtrackCnt--;
            }
            else
            {
                gNfca.CR.doBacktrack = false;
            }

            if( ret == RFAL_ERR_RF_COLLISION )
            {
                /* Check received length */
                if( (gNfca.CR.bytesTxRx + ((gNfca.CR.bitsTxRx != 0U) ? 1U : 0U)) > (RFAL_NFCA_SDD_RES_LEN + RFAL_NFCA_SDD_REQ_LEN) )
                {
                    return RFAL_ERR_PROTO;
                }

                /* Collision in BCC: Anticollide only UID part */
                if( ((gNfca.CR.bytesTxRx + ((gNfca.CR.bitsTxRx != 0U) ? 1U : 0U)) > (RFAL_NFCA_CASCADE_1_UID_LEN + RFAL_NFCA_SDD_REQ_LEN)) && (gNfca.CR.backtrackCnt != 0U) )
                {
                    gNfca.CR.backtrackCnt--;
                    gNfca.CR.bytesTxRx = (RFAL_NFCA_CASCADE_1_UID_LEN + RFAL_NFCA_SDD_REQ_LEN) - 1U;
                    gNfca.CR.bitsTxRx = 7;
                    collBit = (uint8_t)( ((uint8_t*)&gNfca.CR.selReq)[gNfca.CR.bytesTxRx] & (1U << gNfca.CR.bitsTxRx) ); /* Not a real collision, extract the actual bit for the subsequent code */
                }
                
                
                /* Activity 1.0 & 1.1  9.3.4.12: If CON_DEVICES_LIMIT has a value of 0, then 
                 * NFC Forum Device is configured to perform collision detection only       */
                if( (gNfca.CR.devLimit == 0U) && (!(*gNfca.CR.collPend)) )
                {
                    *gNfca.CR.collPend = true;
                    return RFAL_ERR_IGNORE;
                }
                
                *gNfca.CR.collPend = true;
                
                /* Set and select the collision bit, with the number of bytes/bits successfully TxRx */
                if (collBit != 0U)
                {
                    ((uint8_t*)&gNfca.CR.selReq)[gNfca.CR.bytesTxRx] = (uint8_t)(((uint8_t*)&gNfca.CR.selReq)[gNfca.CR.bytesTxRx] | (1U << gNfca.CR.bitsTxRx));   /* MISRA 10.3 */
                }
                else
                {
                    ((uint8_t*)&gNfca.CR.selReq)[gNfca.CR.bytesTxRx] = (uint8_t)(((uint8_t*)&gNfca.CR.selReq)[gNfca.CR.bytesTxRx] & ~(1U << gNfca.CR.bitsTxRx));  /* MISRA 10.3 */
                }

                gNfca.CR.bitsTxRx++;
                
                /* Check if number of bits form a byte */
                if( gNfca.CR.bitsTxRx == RFAL_BITS_IN_BYTE )
                {
                    gNfca.CR.bitsTxRx = 0;
                    gNfca.CR.bytesTxRx++;
                }
                
                gNfca.CR.state = RFAL_NFCA_CR_SDD_TX;
                break;
            }
            
            /*******************************************************************************/
            /* Check if Collision loop has failed */
            if( ret != RFAL_ERR_NONE )
            {
                return ret;
            }
            
            
            /* If collisions are to be reported check whether the response is complete */
            if( (gNfca.CR.devLimit == 0U) && (gNfca.CR.rxLen != sizeof(rfalNfcaSddRes)) )
            {
                return RFAL_ERR_PROTO;
            }
            
            /* Check if the received BCC match */
            if( gNfca.CR.selReq.bcc != rfalNfcaCalculateBcc( gNfca.CR.selReq.nfcid1, RFAL_NFCA_CASCADE_1_UID_LEN ) )
            {
                return RFAL_ERR_PROTO;
            }
            
            /*******************************************************************************/
            /* Anticollision OK, Select this Cascade Level */
            gNfca.CR.selReq.selPar = RFAL_NFCA_SEL_SELPAR;
            
            gNfca.CR.retries = RFAL_NFCA_N_RETRANS;
            gNfca.CR.state   = RFAL_NFCA_CR_SEL_TX;
            break;
            
        /*******************************************************************************/
        case RFAL_NFCA_CR_SEL_TX:
            
            /* Send SEL_REQ (Select command) - Retry upon timeout  EMVCo 2.6  9.6.1.3 */            
            rfalTransceiveBlockingTx( (uint8_t*)&gNfca.CR.selReq, sizeof(rfalNfcaSelReq), (uint8_t*)gNfca.CR.selRes, sizeof(rfalNfcaSelRes), &gNfca.CR.rxLen, RFAL_TXRX_FLAGS_DEFAULT, RFAL_NFCA_FDTMIN );        
            gNfca.CR.state   = RFAL_NFCA_CR_SEL;
            break;
        
        /*******************************************************************************/            
        case RFAL_NFCA_CR_SEL:
            
            RFAL_EXIT_ON_BUSY( ret, rfalGetTransceiveStatus() );
                
            /* Retry upon timeout  EMVCo 2.6  9.6.1.3 */
            if( (ret == RFAL_ERR_TIMEOUT) && (gNfca.CR.devLimit==0U) && (gNfca.CR.retries != 0U) )
            {
                gNfca.CR.retries--;
                platformTimerDestroy( gNfca.CR.tmrFDT );
                gNfca.CR.tmrFDT = platformTimerCreate( RFAL_NFCA_T_RETRANS );
                
                gNfca.CR.state = RFAL_NFCA_CR_SEL_TX;
                break;
            }
            
            if( ret != RFAL_ERR_NONE )
            {
                return ret;
            }
            
            gNfca.CR.rxLen = rfalConvBitsToBytes( gNfca.CR.rxLen );
            
            /* Ensure proper response length */
            if( gNfca.CR.rxLen != sizeof(rfalNfcaSelRes) )
            {
                return RFAL_ERR_PROTO;
            }
            
            /*******************************************************************************/
            /* Check cascade byte, if cascade tag then go next cascade level */
            if( *gNfca.CR.selReq.nfcid1 == RFAL_NFCA_SDD_CT )
            {
                /* Cascade Tag present, store nfcid1 bytes (excluding cascade tag) and continue for next CL */
                RFAL_MEMCPY( &gNfca.CR.nfcId1[*gNfca.CR.nfcId1Len], &((uint8_t*)&gNfca.CR.selReq.nfcid1)[RFAL_NFCA_SDD_CT_LEN], (RFAL_NFCA_CASCADE_1_UID_LEN - RFAL_NFCA_SDD_CT_LEN) );
                *gNfca.CR.nfcId1Len += (RFAL_NFCA_CASCADE_1_UID_LEN - RFAL_NFCA_SDD_CT_LEN);
                
                /* Go to next cascade level */
                gNfca.CR.state = RFAL_NFCA_CR_CL;
                gNfca.CR.cascadeLv++;
            }
            else
            {
                /* UID Selection complete, Stop Cascade Level loop */
                RFAL_MEMCPY( &gNfca.CR.nfcId1[*gNfca.CR.nfcId1Len], (uint8_t*)&gNfca.CR.selReq.nfcid1, RFAL_NFCA_CASCADE_1_UID_LEN );
                *gNfca.CR.nfcId1Len += RFAL_NFCA_CASCADE_1_UID_LEN;
                
                gNfca.CR.state = RFAL_NFCA_CR_DONE;
                break;                             /* Only flag operation complete on the next execution */
            }
            break;
        
        /*******************************************************************************/
        case RFAL_NFCA_CR_DONE:
            return RFAL_ERR_NONE;
        
        /*******************************************************************************/
        default:
            return RFAL_ERR_WRONG_STATE;
    }
    return RFAL_ERR_BUSY;
}

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/

/*******************************************************************************/
ReturnCode rfalNfcaPollerInitialize( void )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, rfalSetMode( RFAL_MODE_POLL_NFCA, RFAL_BR_106, RFAL_BR_106 ) );
    rfalSetErrorHandling( RFAL_ERRORHANDLING_NONE );
    
    rfalSetGT( RFAL_GT_NFCA );
    rfalSetFDTListen( RFAL_FDT_LISTEN_NFCA_POLLER );
    rfalSetFDTPoll( RFAL_FDT_POLL_NFCA_POLLER );
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerCheckPresence( rfal14443AShortFrameCmd cmd, rfalNfcaSensRes *sensRes )
{
    ReturnCode ret;
    uint16_t   rcvLen;
    
    /* Digital 1.1 6.10.1.3  For Commands ALL_REQ, SENS_REQ, SDD_REQ, and SEL_REQ, the NFC Forum Device      *
     *              MUST treat receipt of a Listen Frame at a time after FDT(Listen, min) as a Timeour Error */
    
    ret = rfalISO14443ATransceiveShortFrame(  cmd, (uint8_t*)sensRes, (uint8_t)rfalConvBytesToBits(sizeof(rfalNfcaSensRes)), &rcvLen, RFAL_NFCA_FDTMIN  );
    if( (ret == RFAL_ERR_RF_COLLISION) || (ret == RFAL_ERR_CRC)  || (ret == RFAL_ERR_NOMEM) || (ret == RFAL_ERR_FRAMING) || (ret == RFAL_ERR_PAR) || (ret == RFAL_ERR_INCOMPLETE_BYTE) )
    {
       ret = RFAL_ERR_NONE;
    }

    return ret;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerTechnologyDetection( rfalComplianceMode compMode, rfalNfcaSensRes *sensRes )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartTechnologyDetection( compMode, sensRes ) );
    rfalRunBlocking( ret, rfalNfcaPollerGetTechnologyDetectionStatus() );
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerStartTechnologyDetection( rfalComplianceMode compMode, rfalNfcaSensRes *sensRes )
{
    ReturnCode ret;
    
    gNfca.DT.compMode = compMode;
    gNfca.DT.ret      = rfalNfcaPollerCheckPresence( ((compMode == RFAL_COMPLIANCE_MODE_EMV) ? RFAL_14443A_SHORTFRAME_CMD_WUPA : RFAL_14443A_SHORTFRAME_CMD_REQA), sensRes );
    
    /* Send SLP_REQ as  Activity 1.1  9.2.3.6 and EMVCo 2.6  9.2.1.3 */
    if( (gNfca.DT.compMode != RFAL_COMPLIANCE_MODE_ISO) && (gNfca.DT.ret == RFAL_ERR_NONE) )
    {
        RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartSleep() );
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerGetTechnologyDetectionStatus( void )
{
    ReturnCode ret;
    
    /* If Sleep was sent, wait until its termination */
    if( (gNfca.DT.compMode != RFAL_COMPLIANCE_MODE_ISO) && (gNfca.DT.ret == RFAL_ERR_NONE) )
    {
        RFAL_EXIT_ON_BUSY( ret, rfalNfcaPollerGetSleepStatus() );
    }
    
    return gNfca.DT.ret;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerSingleCollisionResolution( uint8_t devLimit, bool *collPending, rfalNfcaSelRes *selRes, uint8_t *nfcId1, uint8_t *nfcId1Len )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartSingleCollisionResolution( devLimit, collPending, selRes, nfcId1, nfcId1Len ) );
    rfalRunBlocking( ret, rfalNfcaPollerGetSingleCollisionResolutionStatus() );
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerStartFullCollisionResolution( rfalComplianceMode compMode, uint8_t devLimit, rfalNfcaListenDevice *nfcaDevList, uint8_t *devCnt )
{
    ReturnCode      ret;
    rfalNfcaSensRes sensRes;
    uint16_t        rcvLen;
    
    if( (nfcaDevList == NULL) || (devCnt == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    *devCnt = 0;
    ret     = RFAL_ERR_NONE;
    
    /*******************************************************************************/
    /* Send ALL_REQ before Anticollision if a Sleep was sent before  Activity 1.1  9.3.4.1 and EMVco 2.6  9.3.2.1 */
    if( compMode != RFAL_COMPLIANCE_MODE_ISO )
    {
        ret = rfalISO14443ATransceiveShortFrame( RFAL_14443A_SHORTFRAME_CMD_WUPA, (uint8_t*)&nfcaDevList->sensRes, (uint8_t)rfalConvBytesToBits(sizeof(rfalNfcaSensRes)), &rcvLen, RFAL_NFCA_FDTMIN  );
        if(ret != RFAL_ERR_NONE)
        {
            if( (compMode == RFAL_COMPLIANCE_MODE_EMV) || ((ret != RFAL_ERR_RF_COLLISION) && (ret != RFAL_ERR_CRC) && (ret != RFAL_ERR_FRAMING) && (ret != RFAL_ERR_PAR) && (ret != RFAL_ERR_INCOMPLETE_BYTE)) )
            {
                return ret;
            }
        }
        
        /* Check proper SENS_RES/ATQA size */
        if( (ret == RFAL_ERR_NONE) && (rfalConvBytesToBits(sizeof(rfalNfcaSensRes)) != rcvLen) )
        {
            return RFAL_ERR_PROTO;
        }
    }
    
    /*******************************************************************************/
    /* Store the SENS_RES from Technology Detection or from WUPA */ 
    sensRes = nfcaDevList->sensRes;
    
    if( devLimit > 0U )  /* MISRA 21.18 */
    {
        RFAL_MEMSET( nfcaDevList, 0x00, (sizeof(rfalNfcaListenDevice) * devLimit) );
    }
    
    /* Restore the prev SENS_RES, assuming that the SENS_RES received is from first device
     * When only one device is detected it's not woken up then we'll have no SENS_RES (ATQA) */
    nfcaDevList->sensRes = sensRes;
    
    /* Save parameters */
    gNfca.CR.devCnt      = devCnt;
    gNfca.CR.devLimit    = devLimit;
    gNfca.CR.nfcaDevList = nfcaDevList;
    gNfca.CR.compMode    = compMode;
    gNfca.CR.fState      = RFAL_NFCA_CR_FULL_START;
    
    
    #if RFAL_FEATURE_T1T
    /*******************************************************************************/
    /* Only check for T1T if previous SENS_RES was received without a transmission  *
     * error. When collisions occur bits in the SENS_RES may look like a T1T        */
    /* If T1T Anticollision is not supported  Activity 1.1  9.3.4.3 */
    if( rfalNfcaIsSensResT1T( &nfcaDevList->sensRes ) && (devLimit != 0U) && (ret == RFAL_ERR_NONE) && (compMode != RFAL_COMPLIANCE_MODE_EMV) )
    {
        /* RID_REQ shall be performed              Activity 1.1  9.3.4.24 */
        rfalT1TPollerInitialize();
        RFAL_EXIT_ON_ERR( ret, rfalT1TPollerRid( &nfcaDevList->ridRes ) );
        
        *devCnt = 1U;
        nfcaDevList->isSleep   = false;
        nfcaDevList->type      = RFAL_NFCA_T1T;
        nfcaDevList->nfcId1Len = RFAL_NFCA_CASCADE_1_UID_LEN;
        RFAL_MEMCPY( &nfcaDevList->nfcId1, &nfcaDevList->ridRes.uid, RFAL_NFCA_CASCADE_1_UID_LEN );
        
        return RFAL_ERR_NONE;
    }
    #endif /* RFAL_FEATURE_T1T */
    
    
    RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartSingleCollisionResolution( devLimit, &gNfca.CR.collPending, &nfcaDevList->selRes, (uint8_t*)&nfcaDevList->nfcId1, &nfcaDevList->nfcId1Len ) );
    
    gNfca.CR.fState = RFAL_NFCA_CR_FULL_START;
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerGetFullCollisionResolutionStatus( void )
{
    ReturnCode ret;
    uint8_t    newDevType;
    
    if( (gNfca.CR.nfcaDevList == NULL) || (gNfca.CR.devCnt == NULL) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    
    switch( gNfca.CR.fState )
    {
        /*******************************************************************************/
        case RFAL_NFCA_CR_FULL_START:
            
            /*******************************************************************************/
            /* Check whether a T1T has already been detected */
            if( rfalNfcaIsSensResT1T( &gNfca.CR.nfcaDevList->sensRes ) && (gNfca.CR.nfcaDevList->type == RFAL_NFCA_T1T) )
            {
                /* T1T doesn't support Anticollision */
                return RFAL_ERR_NONE;
            }
            
            /* fall through */
        
        /*******************************************************************************/            
        case RFAL_NFCA_CR_FULL_RESTART:  /*  PRQA S 2003 # MISRA 16.3 - Intentional fall through */
            
            /*******************************************************************************/
            RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerGetSingleCollisionResolutionStatus() );

            /* Assign Listen Device */
            newDevType = ((uint8_t)gNfca.CR.nfcaDevList[*gNfca.CR.devCnt].selRes.sak) & RFAL_NFCA_SEL_RES_CONF_MASK;  /* MISRA 10.8 */
            /* PRQA S 4342 1 # MISRA 10.5 - Guaranteed that no invalid enum values are created: see guard_eq_RFAL_NFCA_T2T, .... */
            gNfca.CR.nfcaDevList[*gNfca.CR.devCnt].type    = (rfalNfcaListenDeviceType) newDevType;
            gNfca.CR.nfcaDevList[*gNfca.CR.devCnt].isSleep = false;
            (*gNfca.CR.devCnt)++;

            
            /* If a collision was detected and device counter is lower than limit  Activity 1.1  9.3.4.21 */
            if( (*gNfca.CR.devCnt < gNfca.CR.devLimit) && (gNfca.CR.collPending) )
            {
                /* Put this device to Sleep  Activity 1.1  9.3.4.22 */
                RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartSleep() );
                gNfca.CR.nfcaDevList[(*gNfca.CR.devCnt - 1U)].isSleep = true;
                
                gNfca.CR.fState = RFAL_NFCA_CR_FULL_SLPCHECK;
                return RFAL_ERR_BUSY;
            }
            else
            {
                /* Exit loop */
                gNfca.CR.collPending = false;
            }
            break;
            
            
        /*******************************************************************************/    
        case RFAL_NFCA_CR_FULL_SLPCHECK:
            
            RFAL_EXIT_ON_BUSY( ret, rfalNfcaPollerGetSleepStatus() );
    
            /* Send a new SENS_REQ to check for other cards  Activity 1.1  9.3.4.23 */
            ret = rfalNfcaPollerCheckPresence( RFAL_14443A_SHORTFRAME_CMD_REQA, &gNfca.CR.nfcaDevList[*gNfca.CR.devCnt].sensRes );
            if( ret == RFAL_ERR_TIMEOUT )
            {
                /* No more devices found, exit */
                gNfca.CR.collPending = false;
            }
            else
            {
                /* Another device found, restart|continue loop */
                gNfca.CR.collPending = true;
                
                /*******************************************************************************/
                /* Check if collision resolution shall continue */
                if( (*gNfca.CR.devCnt < gNfca.CR.devLimit) && (gNfca.CR.collPending) )
                {
                    RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartSingleCollisionResolution(  gNfca.CR.devLimit, 
                                                                                     &gNfca.CR.collPending, 
                                                                                     &gNfca.CR.nfcaDevList[*gNfca.CR.devCnt].selRes, 
                                                                                     (uint8_t*)&gNfca.CR.nfcaDevList[*gNfca.CR.devCnt].nfcId1, 
                                                                                     &gNfca.CR.nfcaDevList[*gNfca.CR.devCnt].nfcId1Len ) );
                
                    gNfca.CR.fState = RFAL_NFCA_CR_FULL_RESTART;
                    return RFAL_ERR_BUSY;
                }
            }
            break;
            
        /*******************************************************************************/
        default:
            return RFAL_ERR_WRONG_STATE;
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerFullCollisionResolution( rfalComplianceMode compMode, uint8_t devLimit, rfalNfcaListenDevice *nfcaDevList, uint8_t *devCnt )
{
    ReturnCode ret;
    
    RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartFullCollisionResolution( compMode, devLimit, nfcaDevList, devCnt ) );
    rfalRunBlocking( ret, rfalNfcaPollerGetFullCollisionResolutionStatus() );
    
    return ret;
}

ReturnCode rfalNfcaPollerSleepFullCollisionResolution( uint8_t devLimit, rfalNfcaListenDevice *nfcaDevList, uint8_t *devCnt )
{
    bool       firstRound;
    uint8_t    tmpDevCnt;
    ReturnCode ret;


    if( (nfcaDevList == NULL) || (devCnt == NULL) )
    {
        return RFAL_ERR_PARAM;
    }

    /* Only use ALL_REQ (WUPA) on the first round */
    firstRound = true;  
    *devCnt    = 0;
    
    
    /* Perform collision resolution until no new device is found */
    do
    {
        tmpDevCnt = 0;
        ret = rfalNfcaPollerFullCollisionResolution( (firstRound ? RFAL_COMPLIANCE_MODE_NFC : RFAL_COMPLIANCE_MODE_ISO), (devLimit - *devCnt), &nfcaDevList[*devCnt], &tmpDevCnt );

        if( (ret == RFAL_ERR_NONE) && (tmpDevCnt > 0U) )
        {
            *devCnt += tmpDevCnt;

            /* Check whether to seacrh for more devices */
            if( *devCnt < devLimit )
            {
                /* Set last found device to sleep (all others are slept already) */
                rfalNfcaPollerSleep();
                nfcaDevList[((*devCnt)-1U)].isSleep = true;
                
                /* Check if any other device is present */
                ret = rfalNfcaPollerCheckPresence( RFAL_14443A_SHORTFRAME_CMD_REQA, &nfcaDevList[*devCnt].sensRes );
                if( ret == RFAL_ERR_NONE )
                {
                    firstRound = false;
                    continue;
                }
            }
        }
        break;
    }
    while( true );

    return ((*devCnt > 0U) ? RFAL_ERR_NONE : ret);
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerSelect( const uint8_t *nfcid1, uint8_t nfcidLen, rfalNfcaSelRes *selRes )
{
    ReturnCode ret;

    RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartSelect( nfcid1, nfcidLen, selRes ) );
    rfalRunBlocking( ret, rfalNfcaPollerGetSelectStatus() );
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerStartSelect( const uint8_t *nfcid1, uint8_t nfcidLen, rfalNfcaSelRes *selRes )
{
    if( (nfcid1 == NULL) || (nfcidLen > RFAL_NFCA_CASCADE_3_UID_LEN) || (selRes == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    
    /* Calculate Cascate Level */
    gNfca.SEL.fCascadeLv = rfalNfcaNfcidLen2CL( nfcidLen );
    gNfca.SEL.cascadeLv  = RFAL_NFCA_SEL_CASCADE_L1;
    
    gNfca.SEL.nfcidOffset  = 0;
    gNfca.SEL.isRx         = false;
    gNfca.SEL.selRes       = selRes;
    gNfca.SEL.nfcid1       = nfcid1;
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerGetSelectStatus( void )
{
    ReturnCode     ret;
    rfalNfcaSelReq selReq;
    
    if( (!gNfca.SEL.isRx) )
    {
        /*******************************************************************************/
        /* Go through all Cascade Levels     Activity 1.1  9.4.4 */
        if( gNfca.SEL.cascadeLv <= gNfca.SEL.fCascadeLv )
        {
            /* Assign SEL_CMD according to the CLn and SEL_PAR*/
            selReq.selCmd = rfalNfcaCLn2SELCMD(gNfca.SEL.cascadeLv);
            selReq.selPar = RFAL_NFCA_SEL_SELPAR;
            
            /* Compute NFCID/Data on the SEL_REQ command   Digital 1.1  Table 18 */
            if( gNfca.SEL.fCascadeLv != gNfca.SEL.cascadeLv )
            {
                *selReq.nfcid1 = RFAL_NFCA_SDD_CT;
                RFAL_MEMCPY( &selReq.nfcid1[RFAL_NFCA_SDD_CT_LEN], &gNfca.SEL.nfcid1[gNfca.SEL.nfcidOffset], (RFAL_NFCA_CASCADE_1_UID_LEN - RFAL_NFCA_SDD_CT_LEN) );
                gNfca.SEL.nfcidOffset += (RFAL_NFCA_CASCADE_1_UID_LEN - RFAL_NFCA_SDD_CT_LEN);
            }
            else
            {
                RFAL_MEMCPY( selReq.nfcid1, &gNfca.SEL.nfcid1[gNfca.SEL.nfcidOffset], RFAL_NFCA_CASCADE_1_UID_LEN );
            }
            
            /* Calculate nfcid's BCC */
            selReq.bcc = rfalNfcaCalculateBcc( (uint8_t*)&selReq.nfcid1, sizeof(selReq.nfcid1) );
            
            /*******************************************************************************/
            /* Send SEL_REQ  */
            RFAL_EXIT_ON_ERR( ret, rfalTransceiveBlockingTx( (uint8_t*)&selReq, sizeof(rfalNfcaSelReq), (uint8_t*)gNfca.SEL.selRes, sizeof(rfalNfcaSelRes), &gNfca.SEL.rxLen, RFAL_TXRX_FLAGS_DEFAULT, RFAL_NFCA_FDTMIN ) );
            
            /* Wait for Rx to conclude */
            gNfca.SEL.isRx = true;
            
            return RFAL_ERR_BUSY;
        }
    }
    else
    {
        RFAL_EXIT_ON_BUSY( ret, rfalGetTransceiveStatus() );
        
        /* Ensure proper response length */
        if( rfalConvBitsToBytes( gNfca.SEL.rxLen ) != sizeof(rfalNfcaSelRes) )
        {
            return RFAL_ERR_PROTO;
        }
        
        /* Check if there are more level(s) to be selected */
        if( gNfca.SEL.cascadeLv < gNfca.SEL.fCascadeLv )
        {
            /* Advance to the next cascade lavel */
            gNfca.SEL.cascadeLv++;
            gNfca.SEL.isRx = false;
            
            return RFAL_ERR_BUSY;
        }
    }
    
    /* REMARK: Could check if NFCID1 is complete */
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerSleep( void )
{
    ReturnCode ret;

    RFAL_EXIT_ON_ERR( ret, rfalNfcaPollerStartSleep() );
    rfalRunBlocking( ret, rfalNfcaPollerGetSleepStatus() );
    
    return ret;
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerStartSleep( void )
{
    rfalTransceiveContext ctx;
    
    gNfca.slpReq.frame[RFAL_NFCA_SLP_CMD_POS]   = RFAL_NFCA_SLP_CMD;
    gNfca.slpReq.frame[RFAL_NFCA_SLP_BYTE2_POS] = RFAL_NFCA_SLP_BYTE2;
    
    rfalCreateByteFlagsTxRxContext( ctx, (uint8_t*)&gNfca.slpReq, sizeof(rfalNfcaSlpReq), (uint8_t*)&gNfca.slpReq, sizeof(gNfca.slpReq), NULL, RFAL_TXRX_FLAGS_DEFAULT, RFAL_NFCA_SLP_FWT );
    return rfalStartTransceive( &ctx );
}


/*******************************************************************************/
ReturnCode rfalNfcaPollerGetSleepStatus( void )
{
    ReturnCode ret;
    
    /* ISO14443-3 6.4.3  HLTA - If PICC responds with any modulation during 1 ms this response shall be interpreted as not acknowledge 
       Digital 2.0  6.9.2.1 & EMVCo 3.0  5.6.2.1 - consider the HLTA command always acknowledged
       No check to be compliant with NFC and EMVCo, and to improve interoprability (Kovio RFID Tag)
    */
    RFAL_EXIT_ON_BUSY( ret, rfalGetTransceiveStatus() );
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
bool rfalNfcaListenerIsSleepReq( const uint8_t *buf, uint16_t bufLen )
{
    /* Check if length and payload match */
    if( (bufLen != sizeof(rfalNfcaSlpReq)) || (buf[RFAL_NFCA_SLP_CMD_POS] != RFAL_NFCA_SLP_CMD) || (buf[RFAL_NFCA_SLP_BYTE2_POS] != RFAL_NFCA_SLP_BYTE2) )
    {
        return false;
    }
    
    return true;
}

/* If the guards here don't compile then the code above cannot work anymore. */
extern uint8_t guard_eq_RFAL_NFCA_T2T[((RFAL_NFCA_SEL_RES_CONF_MASK&(uint8_t)RFAL_NFCA_T2T) == (uint8_t)RFAL_NFCA_T2T)?1:(-1)];
extern uint8_t guard_eq_RFAL_NFCA_T4T[((RFAL_NFCA_SEL_RES_CONF_MASK&(uint8_t)RFAL_NFCA_T4T) == (uint8_t)RFAL_NFCA_T4T)?1:(-1)];
extern uint8_t guard_eq_RFAL_NFCA_NFCDEP[((RFAL_NFCA_SEL_RES_CONF_MASK&(uint8_t)RFAL_NFCA_NFCDEP) == (uint8_t)RFAL_NFCA_NFCDEP)?1:(-1)];
extern uint8_t guard_eq_RFAL_NFCA_T4T_NFCDEP[((RFAL_NFCA_SEL_RES_CONF_MASK&(uint8_t)RFAL_NFCA_T4T_NFCDEP) == (uint8_t)RFAL_NFCA_T4T_NFCDEP)?1:(-1)];
#endif /* RFAL_FEATURE_NFCA */
