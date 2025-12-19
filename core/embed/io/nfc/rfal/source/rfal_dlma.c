
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
 *      PROJECT:   ST25R firmware
 *      $Revision: $
 *      LANGUAGE:  ISO C99
 */
 
/*! \file rfal_dlma.c
 *
 *  \brief Functions to manage dynamically the LMA 
 *
 * 
 *  It provides handling for dynamic LMA for Passive Listen Mode
 *  
 *  \warning DLMA is applicable only when the ST25R driver is used for Passive
 *            Listen Mode, not if driven externally
 */

/*
 ******************************************************************************
 * INCLUDES
 ******************************************************************************
 */
#include "rfal_dlma.h"
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
 *    RFAL_FEATURE_DLMA
 */


#if RFAL_FEATURE_DLMA


/* Check for valid Configuration */
#if !RFAL_SUPPORT_CE
    #error " RFAL: Invalid configuration. DLMA only applicable for ST25R supporting Passive Listen Mode. "
#endif


/*
 ******************************************************************************
 * CONDITIONAL INCLUDES
 ******************************************************************************
 */
#include "rfal_dlmaTbl.h"

/*
 ******************************************************************************
 * DEFINES
 ******************************************************************************
 */
#define RFAL_DLMA_ANALOGCONFIG_SHIFT       13U
#define RFAL_DLMA_ANALOGCONFIG_MASK        0x6000U
    
/*
 ******************************************************************************
 * LOCAL DATA TYPES
 ******************************************************************************
 */

/*! RFAL DLMA instance                                                                                */
typedef struct{
    bool                 enabled;
    const rfalDlmaEntry* currentDlma;
    uint8_t              tableEntries;
    rfalDlmaEntry        table[RFAL_DLMA_TABLE_MAX_ENTRIES];
    uint8_t              tableEntry;
    uint8_t              refMeasurement;
    rfalDlmaMeasureFunc  measureCallback;
    rfalDlmaAdjustFunc   adjustCallback;
}rfalDlma;


/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

static rfalDlma gRfalDlma;

/*
 ******************************************************************************
 * GLOBAL FUNCTIONS
 ******************************************************************************
 */
void rfalDlmaInitialize( void )
{
    /* By default DLMA is disabled */
    rfalDlmaSetEnabled( false );
    
    /* Set default measurement and adjust methods */    
    gRfalDlma.measureCallback = &rfalChipGetLmFieldInd;
    gRfalDlma.adjustCallback  = &rfalChipSetLMMod;
    
    
    /* Use the default Dynamic LMA values */
    gRfalDlma.currentDlma  = rfalDlmaDefaultSettings;
    gRfalDlma.tableEntries = (sizeof(rfalDlmaDefaultSettings) / RFAL_DLMA_TABLE_PARAM_LEN);
    
    RFAL_MEMCPY( gRfalDlma.table, gRfalDlma.currentDlma, sizeof(rfalDlmaDefaultSettings) );
}


/*******************************************************************************/
void rfalDlmaSetMeasureCallback( rfalDlmaMeasureFunc pFunc )
{
    gRfalDlma.measureCallback = pFunc;
}


/*******************************************************************************/
void rfalDlmaSetAdjustCallback( rfalDlmaAdjustFunc pFunc )
{
    gRfalDlma.adjustCallback = pFunc;
}


/*******************************************************************************/
ReturnCode rfalDlmaTableWrite( const rfalDlmaEntry* powerTbl, uint8_t powerTblEntries )
{
    uint8_t entry;
    
    /* Check if the table size parameter is too big */
    if( powerTblEntries > RFAL_DLMA_TABLE_MAX_ENTRIES)
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
    RFAL_MEMCPY( gRfalDlma.table, powerTbl, (powerTblEntries * RFAL_DLMA_TABLE_PARAM_LEN) );
    gRfalDlma.currentDlma  = gRfalDlma.table;
    gRfalDlma.tableEntries = powerTblEntries;
    
    if( gRfalDlma.tableEntry > powerTblEntries )
    {
        /* powerTblEntries is always greater then zero, verified at parameter check */
        gRfalDlma.tableEntry = (powerTblEntries - 1U); 
    }
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalDlmaTableRead( rfalDlmaEntry* tblBuf, uint8_t tblBufEntries, uint8_t* tableEntries )
{
    /* Check parameters */
    if( (tblBuf == NULL) || (tblBufEntries < gRfalDlma.tableEntries) || (tableEntries == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
    
    /* Not properly initialized */
    if( gRfalDlma.currentDlma == NULL )
    {
        return RFAL_ERR_WRONG_STATE;
    }
        
    /* Copy the whole Table to the given buffer */
    RFAL_MEMCPY( tblBuf, gRfalDlma.currentDlma, (tblBufEntries * RFAL_DLMA_TABLE_PARAM_LEN) );
    *tableEntries = gRfalDlma.tableEntries;
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
ReturnCode rfalDlmaAdjust( void )
{
    uint8_t              refValue;
    uint16_t             modeID;
    rfalBitRate          br;
    rfalMode             mode;
    uint8_t              tableEntry;
    uint8_t              i;
    const rfalDlmaEntry* dlmaTable;
    
    /* Initialize local vars */
    tableEntry = gRfalDlma.tableEntry;
    dlmaTable  = gRfalDlma.currentDlma;
    refValue   = 0;
    mode       = RFAL_MODE_NONE;
    br         = RFAL_BR_KEEP;
    
    /* Obtain RFAL's current mode and bit rate */
    mode = rfalGetMode();
    rfalGetBitRate( &br, NULL );
    
    
    /* Check if the Power Adjustment is disabled and                  *
     * if the callback to the measurement method is properly set      */
    if( (!gRfalDlma.enabled) || (gRfalDlma.measureCallback == NULL) || (gRfalDlma.adjustCallback == NULL) )
    {
        return RFAL_ERR_PARAM;
    }
        
    /* Ensure that the table is initialized*/
    if( gRfalDlma.currentDlma == NULL )
    {
        return RFAL_ERR_WRONG_STATE;
    }
    
    /* Ensure a proper measure reference value */
    if( RFAL_ERR_NONE != gRfalDlma.measureCallback( &refValue ) )
    {
        return RFAL_ERR_IO;
    }
    
    for( i = 0; i < RFAL_DLMA_TABLE_MAX_ENTRIES; i++ )
    {
        /* Search the table to find matching entry */        
        if( (refValue <= dlmaTable[i].inc) && (refValue >= dlmaTable[i].dec) )
        {
            tableEntry = i;
            break;
        }
    }
    
    /* Apply configs and Update local context */
    gRfalDlma.refMeasurement = refValue;
    gRfalDlma.tableEntry     = tableEntry;
    
    
    /* Set the new value for LMA (e.g. RFO resistance) form the table and apply it */ 
    gRfalDlma.adjustCallback( dlmaTable[gRfalDlma.tableEntry].modRes, dlmaTable[gRfalDlma.tableEntry].unmodRes );
    
    /* Apply the DLMA Analog Config according to this threshold */
    /* Technology field is being extended for DLMA: 2msb are used for threshold step (only 4 allowed) */
    modeID  = rfalAnalogConfigGenModeID( mode, br, RFAL_ANALOG_CONFIG_DLMA ); /* Generate Analog Config mode ID  */
    modeID |= (((uint16_t)gRfalDlma.tableEntry << RFAL_DLMA_ANALOGCONFIG_SHIFT) & RFAL_DLMA_ANALOGCONFIG_MASK);   /* Add DLMA threshold step|level    */
    rfalSetAnalogConfig( modeID );                                                                                /* Apply DLMA Analog Config         */
    
    return RFAL_ERR_NONE;
}


/*******************************************************************************/
void rfalDlmaSetEnabled( bool enable )
{
    gRfalDlma.enabled        = enable;
    gRfalDlma.tableEntry     = 0;
    gRfalDlma.refMeasurement = 0;
}


/*******************************************************************************/
bool rfalDlmaIsEnabled( void )
{
    return gRfalDlma.enabled;
}


/*******************************************************************************/
ReturnCode rfalDlmaGetInfo( rfalDlmaInfo* info )
{
    if( info == NULL )
    {
        return RFAL_ERR_PARAM;
    }

    /* Clear info structure */
    RFAL_MEMSET( info, 0, sizeof(rfalDlmaInfo) );
    
    info->enabled         = gRfalDlma.enabled;
    info->refMeasurement  = gRfalDlma.refMeasurement;
    info->tableEntry      = gRfalDlma.tableEntry;
    info->tableEntries    = gRfalDlma.tableEntries;
    info->measureCallback = gRfalDlma.measureCallback;
    info->adjustCallback  = gRfalDlma.adjustCallback;
    
    return RFAL_ERR_NONE;
}

#endif /* RFAL_FEATURE_DLMA */
