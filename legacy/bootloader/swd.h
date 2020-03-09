#ifndef __SWD_H_DEFINED__
#define __SWD_H_DEFINED__
#include <string.h>
#include "nrf52.h"

extern unsigned int g_dp_select;
extern unsigned int g_page_size;
extern unsigned int g_page_number;
extern unsigned int g_offset;
extern unsigned short g_crc;
extern unsigned char flashram[512];

#define SWD_REQUEST_START_BITNUM 0
#define SWD_REQUEST_APnDP_BITNUM 1
#define SWD_REQUEST_RnW_BITNUM 2
#define SWD_REQUEST_ADDR_BITNUM 3
#define SWD_REQUEST_A2_BITNUM 3
#define SWD_REQUEST_A3_BITNUM 4
#define SWD_REQUEST_PARITY_BITNUM 5
#define SWD_REQUEST_STOP_BITNUM 6
#define SWD_REQUEST_PARK_BITNUM 7

#define SWD_REQUEST_START_VAL 1
#define SWD_REQUEST_STOP_VAL 0
#define SWD_REQUEST_PARK_VAL 1
#define SWD_REQUEST_BITLEN 8

#define SWD_ADDR_MINVAL 0
#define SWD_ADDR_MAXVAL 0xC

#define SWD_ACK_BITLEN 3
#define SWD_ACK_OK_VAL 1
#define SWD_ACK_WAIT_VAL 2
#define SWD_ACK_FAULT_VAL 4

/// Retry count default value
#define SWD_RETRY_COUNT_DEFAULT 10
/// Retry delay default value
#define SWD_RETRY_DELAY_DEFAULT 5

// RO
#define SWD_DP_IDCODE_ADDR 0
// WO
#define SWD_DP_ABORT_ADDR 0
//(R/W,CTRSEL=b0)
#define SWD_DP_CTRLSTAT_ADDR 0x4
//(R/W, CTRLSEL=b1)
#define SWD_DP_WCR_ADDR 0x4
//(RO)
#define SWD_DP_RESEND_ADDR 0x8
//(WO)
#define SWD_DP_SELECT_ADDR 0x8
//(RO)
#define SWD_DP_RDBUFF_ADDR 0xC
//(WO)
#define SWD_DP_ROUTESEL_ADDR 0xC
#define SWD_AP_IDR_ADDR 0xC
#define SWD_AP_DRW_ADDR 0xC
#define SWD_AP_PSEL_ADDR 0x4
#define SWD_AP_RAZ_WI_ADDR 0x8

#define SWD_DP_ABORT_DAPABORT_BITNUM 0
#define SWD_DP_ABORT_STKCMPCLR_BITNUM 1
#define SWD_DP_ABORT_STKERRCLR_BITNUM 2
#define SWD_DP_ABORT_WDERRCLR_BITNUM 3
#define SWD_DP_ABORT_ORUNERRCLR_BITNUM 4

#define SWD_DP_ABORT_DAPABORT (1 << SWD_DP_ABORT_DAPABORT_BITNUM)
#define SWD_DP_ABORT_STKCMPCLR (1 << SWD_DP_ABORT_STKCMPCLR_BITNUM)
#define SWD_DP_ABORT_STKERRCLR (1 << SWD_DP_ABORT_STKERRCLR_BITNUM)
#define SWD_DP_ABORT_WDERRCLR (1 << SWD_DP_ABORT_WDERRCLR_BITNUM)
#define SWD_DP_ABORT_ORUNERRCLR (1 << SWD_DP_ABORT_ORUNERRCLR_BITNUM)

#define SWD_DP_CTRLSTAT_ORUNDETECT_BITNUM 0
#define SWD_DP_CTRLSTAT_STICKYORUN_BITNUM 1
#define SWD_DP_CTRLSTAT_TRNMODE_BITNUM 2
#define SWD_DP_CTRLSTAT_STICKYCMP_BITNUM 4
#define SWD_DP_CTRLSTAT_STICKYERR_BITNUM 5
#define SWD_DP_CTRLSTAT_READOK_BITNUM 6
#define SWD_DP_CTRLSTAT_WDATAERR_BITNUM 7
#define SWD_DP_CTRLSTAT_MASKLANE_BITNUM 8
#define SWD_DP_CTRLSTAT_TRNCNT_BITNUM 12
#define SWD_DP_CTRLSTAT_CDBGRSTREQ_BITNUM 26
#define SWD_DP_CTRLSTAT_CDBGRSTACK_BITNUM 27
#define SWD_DP_CTRLSTAT_CDBGPWRUPREQ_BITNUM 28
#define SWD_DP_CTRLSTAT_CDBGPWRUPACK_BITNUM 29
#define SWD_DP_CTRLSTAT_CSYSPWRUPREQ_BITNUM 30
#define SWD_DP_CTRLSTAT_CSYSPWRUPACK_BITNUM 31

#define SWD_DP_CTRLSTAT_ORUNDETECT \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_ORUNDETECT_BITNUM)
#define SWD_DP_CTRLSTAT_STICKYORUN \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_STICKYORUN_BITNUM)
#define SWD_DP_CTRLSTAT_TRNMODE \
  ((unsigned int)3 << SWD_DP_CTRLSTAT_TRNMODE_BITNUM)
#define SWD_DP_CTRLSTAT_STICKYCMP \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_STICKYCMP_BITNUM)
#define SWD_DP_CTRLSTAT_STICKYERR \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_STICKYERR_BITNUM)
#define SWD_DP_CTRLSTAT_READOK \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_READOK_BITNUM)
#define SWD_DP_CTRLSTAT_WDATAERR \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_WDATAERR_BITNUM)
#define SWD_DP_CTRLSTAT_MASKLANE \
  ((unsigned int)0x0F << SWD_DP_CTRLSTAT_MASKLANE_BITNUM)
#define SWD_DP_CTRLSTAT_TRNCNT \
  ((unsigned int)0x0FFF << SWD_DP_CTRLSTAT_TRNCNT_BITNUM)
#define SWD_DP_CTRLSTAT_CDBGRSTREQ \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_CDBGRSTREQ_BITNUM)
#define SWD_DP_CTRLSTAT_CDBGRSTACK \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_CDBGRSTACK_BITNUM)
#define SWD_DP_CTRLSTAT_CDBGPWRUPREQ \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_CDBGPWRUPREQ_BITNUM)
#define SWD_DP_CTRLSTAT_CDBGPWRUPACK \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_CDBGPWRUPACK_BITNUM)
#define SWD_DP_CTRLSTAT_CSYSPWRUPREQ \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_CSYSPWRUPREQ_BITNUM)
#define SWD_DP_CTRLSTAT_CSYSPWRUPACK \
  ((unsigned int)1 << SWD_DP_CTRLSTAT_CSYSPWRUPACK_BITNUM)

#define SWD_DP_SELECT_CTRLSEL_BITNUM 0
#define SWD_DP_SELECT_APBANKSEL_BITNUM 4
#define SWD_DP_SELECT_APSEL_BITNUM 24
#define SWD_DP_SELECT_CTRLSEL ((unsigned int)1 << SWD_DP_SELECT_CTRLSEL_BITNUM)
#define SWD_DP_SELECT_APBANKSEL \
  ((unsigned int)0x0F << SWD_DP_SELECT_APBANKSEL_BITNUM)
#define SWD_DP_SELECT_APSEL ((unsigned int)0x00FF << SWD_DP_SELECT_APSEL_BITNUM)

#define SWD_DP_WCR_PRESCALER_BITNUM 0
#define SWD_DP_WCR_WIREMODE_BITNUM 6
#define SWD_DP_WCR_TURNROUND_BITNUM 8

#define SWD_MEMAP_CSW_ADDR 0x00
#define SWD_MEMAP_TAR_ADDR 0x04
#define SWD_MEMAP_DRW_ADDR 0x0C
#define SWD_MEMAP_BD0_ADDR 0x10
#define SWD_MEMAP_BD1_ADDR 0x14
#define SWD_MEMAP_BD2_ADDR 0x18
#define SWD_MEMAP_BD3_ADDR 0x1C
#define SWD_MEMAP_CFG_ADDR 0xF4
#define SWD_MEMAP_BASE_ADDR 0xF8
#define SWD_MEMAP_IDR_ADDR 0xFC

#define SWD_MEMAP_APSEL_VAL 0x00
#define SWD_MEMAP_CSW_APBANKSEL_VAL 0x00
#define SWD_MEMAP_TAR_APBANKSEL_VAL 0x00
#define SWD_MEMAP_DRW_APBANKSEL_VAL 0x00
#define SWD_MEMAP_BD0_APBANKSEL_VAL 0x01
#define SWD_MEMAP_BD1_APBANKSEL_VAL 0x01
#define SWD_MEMAP_BD2_APBANKSEL_VAL 0x01
#define SWD_MEMAP_BD3_APBANKSEL_VAL 0x01
#define SWD_MEMAP_CFG_APBANKSEL_VAL 0x0F
#define SWD_MEMAP_BASE_APBANKSEL_VAL 0x0F
#define SWD_MEMAP_IDR_APBANKSEL_VAL 0x0F
#define SWD_MEMAP_CSW_DBGSWENABLE_BITNUM 31
#define SWD_MEMAP_CSW_PROT_BITNUM 24
#define SWD_MEMAP_CSW_SPIDEN_BITNUM 23
#define SWD_MEMAP_CSW_MODE_BITNUM 8
#define SWD_MEMAP_CSW_TRINPROG_BITNUM 7
#define SWD_MEMAP_CSW_DEVICEEN_BITNUM 6
#define SWD_MEMAP_CSW_ADDRINC_BITNUM 4
#define SWD_MEMAP_CSW_SIZE_BITNUM 0
#define SWD_MEMAP_CSW_DBGSWENABLE (1 << SWD_MEMAP_CSW_DBGSWENABLE_BITNUM)
#define SWD_MEMAP_CSW_PROT (0x07F << SWD_MEMAP_CSW_PROT_BITNUM)
#define SWD_MEMAP_CSW_SPIDEN (1 << SWD_MEMAP_CSW_SPIDEN_BITNUM)
#define SWD_MEMAP_CSW_MODE (0x0F << SWD_MEMAP_CSW_MODE_BITNUM)
#define SWD_MEMAP_CSW_TRINPROG (1 << SWD_MEMAP_CSW_TRINPROG_BITNUM)
#define SWD_MEMAP_CSW_DEVICEEN (1 << SWD_MEMAP_CSW_DEVICEEN_BITNUM)
#define SWD_MEMAP_CSW_ADDRINC (3 << SWD_MEMAP_CSW_ADDRINC_BITNUM)
#define SWD_MEMAP_CSW_SIZE (7 << SWD_MEMAP_CSW_SIZE_BITNUM)
#define SWD_MEMAP_CSW_SIZE_8BIT (0x0 << SWD_MEMAP_CSW_SIZE_BITNUM)
#define SWD_MEMAP_CSW_SIZE_16BIT (0x1 << SWD_MEMAP_CSW_SIZE_BITNUM)
#define SWD_MEMAP_CSW_SIZE_32BIT (0x2 << SWD_MEMAP_CSW_SIZE_BITNUM)

#define SWD_MEMAP_CSW_ADDRINC_OFF (0x0 << SWD_MEMAP_CSW_ADDRINC_BITNUM)
#define SWD_MEMAP_CSW_ADDRINC_SINGLE (0x1 << SWD_MEMAP_CSW_ADDRINC_BITNUM)
#define SWD_MEMAP_CSW_ADDRINC_PACKED (0x2 << SWD_MEMAP_CSW_ADDRINC_BITNUM)

#define SWD_MEMAP_CFG_BIGENDIAN_BITNUM 0

#define SWD_MEMAP_CFG_BIGENDIAN (1 << SWD_MEMAP_CFG_BIGENDIAN_BITNUM)

#define SWD_MEMAP_BASE_BASEADDR_BITNUM 12
#define SWD_MEMAP_BASE_FORMAT_BITNUM 1
#define SWD_MEMAP_BASE_ENTRYPRESENT_BITNUM 0
#define SWD_MEMAP_BASE_BASEADDR (1 << SWD_MEMAP_BASE_BASEADDR_BITNUM)
#define SWD_MEMAP_BASE_FORMAT (1 << SWD_MEMAP_BASE_FORMAT_BITNUM)
#define SWD_MEMAP_BASE_ENTRYPRESENT (1 << SWD_MEMAP_BASE_ENTRYPRESENT_BITNUM)

typedef enum {
  SWD_OK = 1,
  SWD_ERROR_GENERAL = -1,
  SWD_ERROR_PARITY = -2,
  SWD_ERROR_APnDP = -3,
  SWD_ERROR_RnW = -4,
  SWD_ERROR_ADDR = -5,
  SWD_ERROR_NULLPOINTER = -6,
  SWD_ERROR_MAXRETRY = -7,
  SWD_ERROR_ACK = -8,
  SWD_ERROR_MEMAPACCSIZE = -9
} swd_error_code_t;

#define SWD_TURNROUND_1_CODE 0
#define SWD_TURNROUND_1_VAL 1
#define SWD_TURNROUND_2_CODE 1
#define SWD_TURNROUNT_2_VAL 2
#define SWD_TURNROUND_3_CODE 2
#define SWD_TURNROUND_3_VAL 3
#define SWD_TURNROUND_4_CODE 3
#define SWD_TURNROUND_4_VAL 4
#define SWD_TURNROUND_MIN_VAL SWD_TURNROUND_1_VAL
#define SWD_TURNROUND_MIN_CODE SWD_TURNOUND_1_CODE
#define SWD_TURNROUND_MAX_VAL SWD_TURNROUND_4_VAL
#define SWD_TURNROUND_MAX_CODE SWD_TURNROUND_4_CODE
#define SWD_TURNROUND_DEFAULT_VAL SWD_TURNROUND_1_VAL

void vHAL_Read(unsigned int usAddr, unsigned char *pucDes,
               unsigned short usLen);
/// SW-DP Reset sequence.
static const unsigned char SWD_CMD_SWDPRESET[] = {0x00, 0xff, 0xff, 0xff, 0xff,
                                                  0xff, 0xff, 0xff, 0xff};
/// Switches DAP from JTAG to SWD.
static const unsigned char SWD_CMD_JTAG2SWD[] = {0x9e, 0xe7, 0xff, 0xff, 0xff,
                                                 0xff, 0xff, 0xff, 0xff, 0xff};

static const unsigned char TEST[] = {0xff, 0x00};
/// Switches DAP from SWD to JTAG.
static const unsigned char SWD_CMD_SWD2JTAG[] = {0xff, 0xff, 0xff, 0xff, 0xff,
                                                 0xff, 0xff, 0xff, 0x3c, 0xe7};
/// Inserts idle clocks for proper data processing.
static const unsigned char SWD_CMD_IDLE[] = {0x00};

// swd io
#define GPIO_SWD_PORT GPIOC
#define GPIO_SWD_CLK GPIO12
#define GPIO_SWD_SDA GPIO11

#define set_swd_clk() (gpio_set(GPIO_SWD_PORT, GPIO_SWD_CLK))
#define clr_swd_clk() (gpio_clear(GPIO_SWD_PORT, GPIO_SWD_CLK))
#define set_swd_sda() (gpio_set(GPIO_SWD_PORT, GPIO_SWD_SDA))
#define clr_swd_sda() (gpio_clear(GPIO_SWD_PORT, GPIO_SWD_SDA))
#define get_swd_sda() (gpio_get(GPIO_SWD_PORT, GPIO_SWD_SDA))

// sda in out change
#define swd_output()                                                  \
  (gpio_mode_setup(GPIO_SWD_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_PULLUP, \
                   GPIO_SWD_SDA))
#define swd_input()                                                \
  (gpio_mode_setup(GPIO_SWD_PORT, GPIO_MODE_INPUT, GPIO_PUPD_NONE, \
                   GPIO_SWD_SDA))
void HAL_Delay(unsigned int uiDelay_Ms);
void swd_io_init(void);
short swd_dap_init(void);
unsigned char swd_ap_ereaseNpage(unsigned int dest, unsigned int pagenum);
unsigned char swd_ap_ereaseall(void);
unsigned char swd_ereaseall(void);
unsigned char swd_ucReadProtect(void);
unsigned char swd_download(unsigned char *p, unsigned int len,
                           unsigned char base);
unsigned char swd_check_code(unsigned int bleaddr, unsigned int len,
                             unsigned char base);
unsigned char swd_read_memory(unsigned int addr, unsigned char *p,
                              unsigned int len);
unsigned char swd_get_flash_tag(void);
void swd_update_crc(unsigned char *buff, unsigned int len);
unsigned char swd_ap_ereasepage(unsigned int dest);

#endif