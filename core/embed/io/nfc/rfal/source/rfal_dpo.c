
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
 *      $Revision: $
 *      LANGUAGE:  ISO C99
 */
 
/*! \file rfal_dpo.c
 *
 *  \author Martin Zechleitner
 *
 *  \brief Functions to manage and set dynamic power settings
 *  
 */

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_dpoTbl.h"
#include "rfal_dpo.h"
#include "rfal_platform.h"
#include "rfal_rf.h"
#include "rfal_chip.h"
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
 *    RFAL_FEATURE_DPO
 */

#if RFAL_FEATURE_DPO


/*
 ******************************************************************************
 * DEFINES
 ******************************************************************************
 */
#define RFAL_DPO_ANALOGCONFIG_SHIFT       13U
#define RFAL_DPO_ANALOGCONFIG_MASK        0x6000U
    
/*
 ******************************************************************************
 * LOCAL DATA TYPES
 ******************************************************************************
 */

/*! RFAL DPO instance                                                                                */
typedef struct{
    bool                enabled;
    const rfalDpoEntry* currentDpo;
    uint8_t             tableEntries;
    rfalDpoEntry        table[RFAL_DPO_TABLE_MAX_ENTRIES];
    uint8_t             tableEntry;
    rfalDpoMeasureFunc  measureCallback;
    rfalMode            curMode;
    rfalBitRate         curBR;
}rfalDpo;


/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

static rfalDpo gRfalDpo;

/*
 ******************************************************************************
 * GLOBAL FUNCTIONS
 ******************************************************************************
 */
void rfalDpoInitialize( void )
{
    /* By default DPO is disabled */
    rfalDpoSetEnabled( false );
    
    
    /* Set default measurement */
    #if defined(ST25R3911) || defined(ST25R3916) || defined(ST25R3916B)
        gRfalDpo.measureCallback = rfalChipMeasureAmplitude;
    #else
        gRfalDpo.measureCallback = rfalChipMeasureCombinedIQ;
    #endif /* ST25R */
    
    
    /* Use the default Dynamic Power values */
    gRfalDpo.currentDpo   = rfalDpoDefaultSettings;
    gRfalDpo.tableEntries = (sizeof(rfalDpoDefaultSettings) / RFAL_DPO_TABLE_PARAM_LEN);
    
    RFAL_MEMCPY( gRfalDpo.table, gRfalDpo.currentDpo, sizeof(rfalDpoDefaultSettings) );
}


/*******************************************************************************/
void rfalDpoSetMeasureCallback( rfalDpoMeasureFunc pFunc )
{
    gRfalDpo.measureCallback = pFunc;
}


/*******************************************************************************/
ReturnCode rfalDpoTableWrite( const rfalDpoEntry* powerTbl, uint8_t powerTblEntries )
{
    uint8_t entry;
    
    /* Check if the table size parameter is too big */
    if( (powerTblEntries * RFAL_DPO_TABLE_PARAM_LEN) > RFAL_DPO_TABLE_SIZE_MAX)
    {
        return RFAL_ERR_NOMEM;
    }
    
    /* Check if the first increase entry is 0xFF */
    if( (powerTblEntries == 0U) || (powerTbl == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
                
    /* Check if the entries of the dynamic power table are valid */
    for( entry = 0; entry < powerTblEntries; entry++ )
    {
        if(powerTbl[entry].inc < powerTbl[entry].dec)
        {
            return RFAL_ERR_PARAM;
        }
    }
    
    /* Copy the data set  */
    RFAL_MEMCPY( gRfalDpo.table, powerTbl, (powerTblEntries * RFAL_DPO_TABLE_PARAM_LEN) );    
    
    gRfalDpo.currentDpo   = gRfalDpo.table;
    gRfalDpo.tableEntries = powerTblEntries;
    
    if( gRfalDpo.tableEntry > powerTblEntries )
    {
        /* powerTblEntries is always greater then zero, verified at parameter check */
        gRfalDpo.tableEntry = (powerTblEntries - 1U); 
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalDpoTableRead( rfalDpoEntry* tblBuf, uint8_t tblBufEntries, uint8_t* tableEntries )
{
    /* Wrong request */
    if( (tblBuf == NULL) || (tblBufEntries < gRfalDpo.tableEntries) || (tableEntries == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Not properly initialized */
    if( gRfalDpo.currentDpo == NULL )
    {
        return RFAL_ERR_WRONG_STATE;
    }
        
    /* Copy the whole Table to the given buffer */
    RFAL_MEMCPY( tblBuf, gRfalDpo.currentDpo, (tblBufEntries * RFAL_DPO_TABLE_PARAM_LEN) );
    *tableEntries = gRfalDpo.tableEntries;
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalDpoAdjust( void )
{
    uint8_t             refValue;
    uint16_t            modeID;
    rfalBitRate         br;
    rfalMode            mode;
    uint8_t             tableEntry;
    const rfalDpoEntry* dpoTable;
    
    /* Initialize local vars */
    tableEntry = gRfalDpo.tableEntry;
    dpoTable   = (const rfalDpoEntry*) gRfalDpo.currentDpo;
    refValue   = 0;
    mode       = RFAL_MODE_NONE;
    br         = RFAL_BR_KEEP;
    
    /* Obtain RFAL's current mode and bit rate */
    mode = rfalGetMode();
    rfalGetBitRate( &br, NULL );
    
    
    /* Check if the Power Adjustment is disabled and                  *
     * if the callback to the measurement method is properly set      */
    if( (!gRfalDpo.enabled) || (gRfalDpo.measureCallback == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Ensure that the current mode is Passive Poller and table is initialized*/
    if( (!rfalIsModePassivePoll( mode )) || (gRfalDpo.currentDpo == NULL) )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Ensure a proper measure reference value */
    if( RFAL_ERR_NONE != gRfalDpo.measureCallback( &refValue ) )
    {
        return RFAL_ERR_IO;
    }

    if( refValue >= dpoTable[gRfalDpo.tableEntry].inc )
    {   /* Increase the output power */
        /* the top of the table represents the highest amplitude value*/
        if( gRfalDpo.tableEntry == 0U )
        {
            /* Maximum driver value has been reached */
        }
        else
        {
            /* Go up in the table to decrease the driver resistance */
            tableEntry--;
        }
    }
    else if( refValue <= dpoTable[gRfalDpo.tableEntry].dec )
    {   /* Decrease the output power */
        /* The bottom is the highest possible value */
        if( (gRfalDpo.tableEntry + 1U) >= gRfalDpo.tableEntries )
        {
            /* minimum driver value has been reached */
        }
        else
        {
            /* Go down in the table to increase the driver resistance */
            tableEntry++;
        }
    }
    else
    {
        /* Fall through to evaluate whether to write dpo and its associated analog configs */
    }
    
    /* Apply new configs if there was a change on DPO level or RFAL mode|bitrate  */
    /* Also adjust power in case mode is not yet set and a different table entry|setting is applicbale */
    if( (mode != gRfalDpo.curMode) || (br != gRfalDpo.curBR) || (tableEntry != gRfalDpo.tableEntry) || ((mode == RFAL_MODE_NONE) && (tableEntry != gRfalDpo.tableEntry)) )
    {
        /* Update local context */
        gRfalDpo.curMode    = mode;
        gRfalDpo.curBR      = br;
        gRfalDpo.tableEntry = tableEntry;
        
        /* Get the new value for RFO resistance form the table and apply the new RFO resistance setting */ 
        rfalChipSetRFO( dpoTable[gRfalDpo.tableEntry].rfoRes );
        
        /* Apply the DPO Analog Config according to this threshold */
        /* Technology field is being extended for DPO: 2msb are used for threshold step (only 4 allowed) */
        modeID  = rfalAnalogConfigGenModeID( gRfalDpo.curMode, gRfalDpo.curBR, RFAL_ANALOG_CONFIG_DPO );           /* Generate Analog Config mode ID  */
        modeID |= (((uint16_t)gRfalDpo.tableEntry << RFAL_DPO_ANALOGCONFIG_SHIFT) & RFAL_DPO_ANALOGCONFIG_MASK);   /* Add DPO threshold step|level    */
        rfalSetAnalogConfig( modeID );                                                                             /* Apply DPO Analog Config         */
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
const rfalDpoEntry* rfalDpoGetCurrentTableEntry( void )
{

    return &gRfalDpo.currentDpo[gRfalDpo.tableEntry];
}


/*******************************************************************************/
uint8_t rfalDpoGetCurrentTableIndex( void )
{
    return gRfalDpo.tableEntry;
}


/*******************************************************************************/
void rfalDpoSetEnabled( bool enable )
{
    gRfalDpo.enabled    = enable;
    gRfalDpo.curMode    = RFAL_MODE_NONE;
    gRfalDpo.curBR      = RFAL_BR_KEEP;
    gRfalDpo.tableEntry = 0;
}


/*******************************************************************************/
bool rfalDpoIsEnabled( void )
{
    return gRfalDpo.enabled;
}

#endif /* RFAL_FEATURE_DPO */
