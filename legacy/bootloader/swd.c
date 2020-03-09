#include "swd.h"
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/rcc.h>
#include "nrf52.h"
#include "updateble.h"

unsigned int g_dp_select;
unsigned int g_page_size;
unsigned int g_page_number;
unsigned int g_offset;
unsigned short g_crc;
unsigned char flashram[512];

void HAL_Delay(unsigned int uiDelay_Ms) {
  uint32_t uiTimeout = uiDelay_Ms * 30000;
  while (uiTimeout--) {
    __asm__("nop");
  }
}

void vHAL_Read(unsigned int usAddr, unsigned char *pucDes,
               unsigned short usLen) {
  unsigned char *pucAddr;
  unsigned short i;

  //---------------------------------------------
  // start read data
  //---------------------------------------------
  pucAddr = (unsigned char *)usAddr;

  for (i = 0; i < usLen; i++) {
    pucDes[i] = pucAddr[i];
  }
}

unsigned char ucSRAM_MemoryCmp(void *pvDst, void *pvSrc, unsigned short usLen) {
  unsigned short i;
  unsigned char ret = 1;

  for (i = 0x00; i < usLen; i++) {
    if (*((unsigned char *)pvSrc + i) != *((unsigned char *)pvDst + i)) {
      ret = 0;
    }
  }

  return ret;
}

static void Delay_n_us(unsigned int uiDelay_us) {
  uint32_t uiTimeout = uiDelay_us * 8;
  while (uiTimeout--) {
    __asm__("nop");
  }
}

void swd_clock_cycle(void)  // one cycle plus
{
  clr_swd_clk();
  Delay_n_us(2);
  set_swd_clk();
  Delay_n_us(2);
}

void swd_write_bit(unsigned char b)  // send ong bit,pull down clk,set
                                     // data,delay,pull up clk ,delay
{
  clr_swd_clk();
  if (b & 0x01) {
    set_swd_sda();
  } else {
    clr_swd_sda();
  }
  Delay_n_us(2);
  set_swd_clk();
  Delay_n_us(2);
}

unsigned char swd_read_bit(void)  // read one bit
{
  unsigned char b = 0;
  clr_swd_clk();
  Delay_n_us(2);
  if (get_swd_sda()) {
    b = 1;
  } else {
    b = 0;
  }
  set_swd_clk();
  Delay_n_us(2);
  return b;
}

static short swd_send(unsigned char *in, unsigned short bits)  // send data
{
  unsigned char t, j;
  unsigned short i;
  t = bits / 8;
  in = in + t - 1;
  for (i = 0; i < bits / 8; i++) {
    for (j = 0; j < 8; j++) {
      t = *in & (0x01 << j);
      t = t >> j;
      swd_write_bit(t);
    }
    in--;
  }
  return 0;
}

static short swd_receive(unsigned char *out, unsigned short bits)  // read data
{
  unsigned char i, j, t, b;
  unsigned char *tmp = out;
  for (j = 0; j <= bits / 8; j++) {
    t = bits - 8 * j;
    if (t >= 8) {
      t = 8;
    }
    for (i = 0; i < t; i++) {
      b = swd_read_bit();
      *tmp |= b << i;
    }
    tmp++;
  }
  return 0;
}

// get parity even
static short swd_parity_even(unsigned char *p, unsigned char *parity,
                             unsigned short bit_len) {
  unsigned char i, n;
  unsigned char test = *p;
  *parity = 0;
  n = bit_len / 8;
  while (n > 0) {
    for (i = 0; i <= 8; i++) {
      *parity ^= ((test >> i) & 0x01);
    }
    n--;
    // p++;
    test = *(p++);
  }
  if (*parity > 1) {
    return SWD_ERROR_PARITY;
  }
  return SWD_OK;
}

/*
APnDP:
    0:DP   1:AP
RnW:
    0:W    1:R
generate  REQUEST byte
*/
static short swd_generate_request(unsigned char *APnDP, unsigned char *RnW,
                                  unsigned char *addr, unsigned char *request) {
  unsigned char reqhdr = 0;
  unsigned char parity;
  unsigned char req;
  short res;
  reqhdr |= (((*addr & (1 << 2)) ? 1 : 0) << SWD_REQUEST_A2_BITNUM);
  reqhdr |= (((*addr & (1 << 3)) ? 1 : 0) << SWD_REQUEST_A3_BITNUM);
  reqhdr |= ((*APnDP ? 1 : 0) << SWD_REQUEST_APnDP_BITNUM);
  reqhdr |= (((*RnW ? 1 : 0) << SWD_REQUEST_RnW_BITNUM));
  req = reqhdr;
  res = swd_parity_even((unsigned char *)&req, &parity, 8);
  if (res < 0) {
    return res;
  }
  reqhdr |= (parity << SWD_REQUEST_PARITY_BITNUM);
  reqhdr |= (SWD_REQUEST_START_VAL << SWD_REQUEST_START_BITNUM);
  reqhdr |= (SWD_REQUEST_STOP_VAL << SWD_REQUEST_STOP_BITNUM);
  reqhdr |= (SWD_REQUEST_PARK_VAL << SWD_REQUEST_PARK_BITNUM);
  *request = reqhdr;
  return SWD_OK;
}

// sen SWD command
unsigned char swd_transfer(unsigned char request, unsigned int *p) {
  unsigned char ack = 0;
  unsigned char parity = 0;
  unsigned char i, b;
  unsigned int val = 0;
  swd_output();
  swd_send(&request, 8);
  swd_input();
  swd_clock_cycle();
  swd_receive(&ack, 3);
  if (ack == SWD_ACK_OK_VAL) {
    if (request & (1 << SWD_REQUEST_RnW_BITNUM)) {
      // swd_receive((unsigned char *)p,32);
      val = 0;
      parity = 0;
      for (i = 0; i < 32; i++) {
        b = swd_read_bit();
        parity ^= b;
        val >>= 1;
        val |= (unsigned int)b << 31;
      }
      b = swd_read_bit();
      // swd_receive(&parity,1);
      // swd_parity_even((unsigned char *)p,&cparity,32);
      if ((b ^ parity) & 1) {
        return SWD_ERROR_PARITY;
      }
      *p = val;
      swd_output();
      swd_clock_cycle();
      /*if(cparity != parity)
      {
          return SWD_ERROR_PARITY;
      }*/
      // swd_output();
      // swd_clock_cycle();
    } else {
      swd_clock_cycle();
      swd_output();
      val = *p;
      parity = 0;
      for (i = 0; i < 32; i++) {
        b = val & 0x01;
        swd_write_bit(b);
        parity ^= b;
        val >>= 1;
      }
      swd_write_bit(parity % 2);
      // swd_parity_even((unsigned char *)p, &parity,32);
      // swd_send((unsigned char *)p,32);
      // swd_send(&parity,1);
    }
    clr_swd_sda();
    for (i = 0; i < 8; i++) {
      swd_clock_cycle();
    }
    clr_swd_clk();
    return ack;
  } else if ((ack == SWD_ACK_WAIT_VAL) || (ack == SWD_ACK_FAULT_VAL)) {
    // if(request & (1 << SWD_REQUEST_RnW_BITNUM))
    //{
    // for(i=0;i<33;i++)
    //{
    // swd_clock_cycle();
    //}
    //}
    swd_clock_cycle();
    swd_output();
    //}
    // if((request & (1 << SWD_REQUEST_RnW_BITNUM)) == 0)
    //{
    /*clr_swd_out();
    for(i=0;i<33;i++)
    {
        swd_clock_cycle();
    }
    set_swd_out();*/
    // swd_clock_cycle();
    // swd_output();
    //}
    clr_swd_sda();
    for (i = 0; i < 8; i++) {
      swd_clock_cycle();
    }
    clr_swd_clk();
    return ack;
  } else {
    for (i = 0; i < 34; i++) {
      swd_clock_cycle();
    }
    return ack;
  }
}
// retry send SWD
unsigned char swd_transfer_retry(unsigned char req, unsigned int *p) {
  unsigned char i, ack;
  for (i = 0; i < SWD_RETRY_COUNT_DEFAULT; i++) {
    ack = swd_transfer(req, p);
    if (ack != SWD_ACK_WAIT_VAL) {
      return ack;
    }
  }
  return ack;
}

// read DP register
static unsigned char swd_dp_write(unsigned char addr, unsigned int *p) {
  unsigned char APnDP = 0;
  unsigned char RnW = 0;
  unsigned char request = 0;
  unsigned char ack = 0;
  if (p == NULL) {
    return 0;
  }
  swd_generate_request(&APnDP, &RnW, &addr, &request);
  HAL_Delay(1);
  ack = swd_transfer_retry(request, p);
  if (ack != 0x01) {
    // CException_ThrowISOException(ack);
    return 0;
  } else {
    return 1;
  }
}

// read DP register
static unsigned char swd_dp_read(unsigned char addr, unsigned int *p) {
  unsigned char APnDP = 0;
  unsigned char RnW = 1;
  unsigned char ack = 0;
  unsigned char request = 0;
  unsigned int val;
  swd_generate_request(&APnDP, &RnW, &addr, &request);
  ack = swd_transfer_retry(request, &val);
  *p = val;
  if (ack != 0x01) {
    return 0;
  } else {
    return 1;
  }
}
// read address's value
static unsigned char swd_read_data(unsigned int addr, unsigned int *p) {
  unsigned char req;
  unsigned char APnDP, RnW;
  unsigned char tmp;
  APnDP = 1;
  RnW = 0;
  tmp = SWD_MEMAP_TAR_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, &addr) != 0x01) {
    return 0;
  }
  APnDP = 1;
  RnW = 1;
  tmp = SWD_MEMAP_DRW_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, p) != 0x01) {
    return 0;
  }
  APnDP = 0;
  RnW = 1;
  tmp = SWD_DP_RDBUFF_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, p) != 0x01) {
    return 0;
  }
  return 1;
}
///////////////////////////
// write AP
static unsigned char swd_apreg_write(unsigned char addr, unsigned int *p) {
  unsigned char APnDP = 1;
  unsigned char RnW = 0;
  unsigned char request = 0;
  unsigned char ack = 0;
  if (p == NULL) {
    return 0;
  }
  swd_generate_request(&APnDP, &RnW, &addr, &request);
  ack = swd_transfer_retry(request, p);
  if (ack != 0x01) {
    // CException_ThrowISOException(ack);
    return 0;
  }
  return 1;
}
///////////////////////
// READ AP
static unsigned char swd_ap_read(unsigned char addr, unsigned int *p) {
  unsigned char APnDP = 1;
  unsigned char RnW = 1;
  unsigned char ack = 0;
  unsigned char request = 0;
  unsigned int val;
  swd_generate_request(&APnDP, &RnW, &addr, &request);
  ack = swd_transfer_retry(request, &val);
  *p = val;
  if (ack != 0x01) {
    return 0;
  } else {
    return 1;
  }
}
// write AP register
static unsigned char swd_ap_write(unsigned char addr, unsigned int *p) {
  unsigned int apsel = 0;
  unsigned int bank_sel = 0;
  unsigned int tmp = 0;
  unsigned char req;
  unsigned char APnDP, RnW;
  apsel = addr & 0xff000000;
  bank_sel = addr & SWD_DP_SELECT_APBANKSEL;
  // if(!swd_dp_write(SWD_DP_SELECT_ADDR, &bank_sel))//apsel | bank_sel))
  tmp = apsel | bank_sel;
  if (!swd_dp_write(SWD_DP_SELECT_ADDR, &tmp)) {
    return 0;
  }
  APnDP = 1;
  RnW = 0;
  addr = addr & 0x0c;
  swd_generate_request(&APnDP, &RnW, &addr, &req);
  if (swd_transfer_retry(req, p) != 0x01) {
    return 0;
  }
  APnDP = 0;
  RnW = 1;
  addr = SWD_DP_RDBUFF_ADDR & 0x0c;
  swd_generate_request(&APnDP, &RnW, &addr, &req);
  if (swd_transfer_retry(req, &tmp) != 0x01) {
    return 0;
  }
  return 1;
}

static unsigned char swd_read_word(unsigned int addr, unsigned int *val) {
  // 32-bit accrss,Increment single,enable
  unsigned int csw_value = 0x23000052;
  if (!swd_ap_write(SWD_MEMAP_CSW_ADDR, &csw_value)) {
    return 0;
  }
  if (!swd_read_data(addr, val)) {
    return 0;
  }
  return 1;
}

// DAP init
short swd_dap_init() {
  unsigned int idr;
  unsigned int dpctrlstat;
  unsigned char addr, res;

  unsigned int p = 0x0000001E;  // 0xFFFFFFFF;
  addr = SWD_DP_IDCODE_ADDR;
  g_page_size = 0;
  g_page_number = 0;
  swd_output();
  swd_send((unsigned char *)SWD_CMD_JTAG2SWD, 80);
  swd_send((unsigned char *)SWD_CMD_SWDPRESET, 72);
  swd_send((unsigned char *)SWD_CMD_SWDPRESET, 72);
  HAL_Delay(1);
  res = swd_dp_read(addr, &idr);
  if (res != 1) {
    return 0;
  }
  // 5.99777612	Operation	read	DebugPort	IDCODE	0xA5	OK
  // 0x2BA01477 DESIGNER=0x477, PARTNO=0xBA01, Version=0x2 5.99930187
  // Operation	write	DebugPort	ABORT	0x81	OK	0x0000001E
  // ORUNERRCLR=1, WDERRCLR=1, STKERRCLR=1, STKCMPCLR=1, DAPABORT=0 6.00128262
  // Operation	write	DebugPort	CTRL/STAT	0xA9	OK
  // 0x00000000 CSYSPWRUPACK=0, CSYSPWRUPREQ=0, CDBGPWRUPACK=0, CDBGPWRUPREQ=0,
  // CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0, WDATAERR=0,
  // READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal, STICKYORUN=0,
  // ORUNDETECT=0 6.00353337	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0
  // 6.00608612	Operation	write	DebugPort	CTRL/STAT	0xA9
  // OK 0x50000000	CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0,
  // CDBGPWRUPREQ=1, CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0,
  // WDATAERR=0, READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal,
  // STICKYORUN=0,
  // ORUNDETECT=0 6.00814450	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0
  // 6.01027075	Operation	write	DebugPort	CTRL/STAT	0xA9
  // OK 0x50000000	CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0,
  // CDBGPWRUPREQ=1, CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0,
  // WDATAERR=0, READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal,
  // STICKYORUN=0,
  // ORUNDETECT=0 6.01230262	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x010000F0	APSEL=0x01, APBANKSEL=0xF, PRESCALER=0x0
  // 6.01429237	Operation	read	AccessPort	IDR	0x9F	OK
  // 0x00000000 Revision=0x0, JEP-106 continuation=0x0, JEP-106 identity=0x00,
  // Class=This AP is not a Memory Acces Port, AP Identfication=0x00 6.01536450
  // Operation	read	DebugPort	RDBUFF	0xBD	OK 0x02880000
  addr = SWD_DP_ABORT_ADDR;
  res = swd_dp_write(addr, &p);  // 0x0000001E
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x010000F0;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  res = swd_ap_read(SWD_MEMAP_IDR_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  res = swd_dp_read(SWD_DP_RDBUFF_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  // 6.01631100	Operation	write	DebugPort	SELECT	0xB1	OK
  // 0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0 6.01827137
  // Operation	write	DebugPort	CTRL/STAT	0xA9	OK
  // 0x50000000 CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0, CDBGPWRUPREQ=1,
  // CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0, WDATAERR=0,
  // READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal, STICKYORUN=0,
  // ORUNDETECT=0 6.02028250	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x01000000	APSEL=0x01, APBANKSEL=0x0, PRESCALER=0x0
  // 6.02228525	Operation	write	AccessPort	TAR	0x8B	OK
  // 0x00000001
  // 6.52364125	Operation	write	DebugPort	SELECT	0xB1	OK
  // 0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0 6.52635087
  // Operation	write	DebugPort	CTRL/STAT	0xA9	OK
  // 0x50000000 CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0, CDBGPWRUPREQ=1,
  // CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0, WDATAERR=0,
  // READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal, STICKYORUN=0,
  // ORUNDETECT=0 6.52834650	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x01000000	APSEL=0x01, APBANKSEL=0x0, PRESCALER=0x0
  // 6.53149425	Operation	read	AccessPort	RAZ_WI	0xB7	OK
  // 0x02880000
  // 6.53345800	Operation	read	DebugPort	RDBUFF	0xBD	OK
  // 0x00000000

  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x01000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000001;
  res = swd_apreg_write(SWD_MEMAP_TAR_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x01000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  res = swd_ap_read(SWD_AP_RAZ_WI_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  res = swd_dp_read(SWD_DP_RDBUFF_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  // 6.53559625	Operation	write	DebugPort	SELECT	0xB1	OK
  // 0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0 6.53913512
  // Operation	write	DebugPort	CTRL/STAT	0xA9	OK
  // 0x50000000 CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0, CDBGPWRUPREQ=1,
  // CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0, WDATAERR=0,
  // READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal, STICKYORUN=0,
  // ORUNDETECT=0 6.54131300	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x01000000	APSEL=0x01, APBANKSEL=0x0, PRESCALER=0x0
  // 6.54331325	Operation	write	AccessPort	TAR	0x8B	OK
  // 0x00000000
  // 6.54531712	Operation	write	DebugPort	SELECT	0xB1	OK
  // 0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0 6.54730750
  // Operation	write	DebugPort	CTRL/STAT	0xA9	OK
  // 0x50000000 CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0, CDBGPWRUPREQ=1,
  // CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0, WDATAERR=0,
  // READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal, STICKYORUN=0,
  // ORUNDETECT=0 6.54930775	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0
  // 6.55265812	Operation	write	DebugPort	CTRL/STAT	0xA9
  // OK 0x50000000	CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0,
  // CDBGPWRUPREQ=1, CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0,
  // WDATAERR=0, READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal,
  // STICKYORUN=0,
  // ORUNDETECT=0 6.55430812	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x010000F0	APSEL=0x01, APBANKSEL=0xF, PRESCALER=0x0
  // 6.55640337	Operation	read	AccessPort	IDR	0x9F	OK
  // 0x00000000 Revision=0x0, JEP-106 continuation=0x0, JEP-106 identity=0x00,
  // Class=This AP is not a Memory Acces Port, AP Identfication=0x00 6.55752425
  // Operation	read	DebugPort	RDBUFF	0xBD	OK 0x02880000
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x01000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000000;
  res = swd_apreg_write(SWD_MEMAP_TAR_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x010000F0;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  res = swd_ap_read(SWD_MEMAP_IDR_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  res = swd_dp_read(SWD_DP_RDBUFF_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  // 6.55841150	Operation	write	DebugPort	SELECT	0xB1	OK
  // 0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0 6.56044087
  // Operation	write	DebugPort	CTRL/STAT	0xA9	OK
  // 0x50000000 CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0, CDBGPWRUPREQ=1,
  // CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0, WDATAERR=0,
  // READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal, STICKYORUN=0,
  // ORUNDETECT=0 6.56240250	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x00000000	APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0
  // 6.56459962	Operation	write	DebugPort	CTRL/STAT	0xA9
  // OK 0x50000000	CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0,
  // CDBGPWRUPREQ=1, CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0,
  // WDATAERR=0, READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal,
  // STICKYORUN=0,
  // ORUNDETECT=0 6.56833162	Operation	write	DebugPort SELECT
  // 0xB1	OK	0x01000000	APSEL=0x01, APBANKSEL=0x0, PRESCALER=0x0
  // 6.57066337	Operation	write	AccessPort	CSW	0xA3	OK
  // 0x00000001 DbgSwEnable=0, Prot=0x00, SPIDEN=0, Mode=0x0, TrInProg=0,
  // DeviceEn=0, AddrInc=Auto-increment off, Size=Halfword (16 bits) 6.57255887
  // Operation	write	DebugPort	SELECT	0xB1	OK	0x00000000
  // APSEL=0x00, APBANKSEL=0x0, PRESCALER=0x0 6.57469837	Operation
  // write DebugPort	CTRL/STAT	0xA9	OK	0x50000000
  // CSYSPWRUPACK=0, CSYSPWRUPREQ=1, CDBGPWRUPACK=0, CDBGPWRUPREQ=1,
  // CDBGRSTACK=0, CDBGRSTREQ=0, TRNCNT=0x000, MASKLANE=0x0, WDATAERR=0,
  // READOK=0, STICKYERR=0, STICKYCMP=0, TRNMODE=Normal, STICKYORUN=0,
  // ORUNDETECT=0 6.57665662	Operation	write	DebugPort SELECT
  // 0xB1	OK 0x01000000	APSEL=0x01, APBANKSEL=0x0,
  // PRESCALER=0x0 6.57864712
  // Operation	write	AccessPort	CSW	0xA3	OK	0x00000000
  // DbgSwEnable=0, Prot=0x00, SPIDEN=0, Mode=0x0, TrInProg=0, DeviceEn=0,
  // AddrInc=Auto-increment off, Size=Byte (8 bits)
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x01000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000001;
  res = swd_apreg_write(SWD_MEMAP_CSW_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  dpctrlstat = 0x00000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x50000000;
  res = swd_dp_write(SWD_DP_CTRLSTAT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x01000000;
  res = swd_dp_write(SWD_DP_SELECT_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }
  HAL_Delay(10);
  dpctrlstat = 0x00000000;
  res = swd_apreg_write(SWD_MEMAP_CSW_ADDR, &dpctrlstat);
  if (res != 1) {
    return 0;
  }

  g_page_size = 128;

  ////////////////////////////////////////////////////////////////////////
  return 1;
}

static unsigned char swd_write_block(unsigned int addr, unsigned char *p,
                                     unsigned int len) {
  unsigned char ack, req;
  unsigned char APnDP, RnW;
  unsigned char tmp;
  unsigned int size_in_words, i;
  unsigned int csw_value = 0x23000052;
  if (len == 0) {
    return 0;
  }
  size_in_words = len / 4;
  if (!swd_ap_write(SWD_MEMAP_CSW_ADDR, &csw_value)) {
    return 0;
  }
  // TAR
  APnDP = 1;
  RnW = 0;
  tmp = SWD_MEMAP_TAR_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, &addr) != 0x01) {
    return 0;
  }

  // DRW write
  APnDP = 1;
  RnW = 0;
  tmp = SWD_MEMAP_DRW_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  for (i = 0; i < size_in_words; i++) {
    //       reverse((unsigned int *)p); //
    //       swd_update_crc(p,4);//
    if (swd_transfer_retry(req, (unsigned int *)p) != 0x01) {
      return 0;
    }
    p += 4;
  }
  // return 1;
  // dumy read
  APnDP = 0;
  RnW = 1;
  tmp = SWD_DP_RDBUFF_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  ack = swd_transfer_retry(req, &csw_value);
  if (ack != 0x01) {
    return 0;
  } else {
    return 1;
  }
}

static unsigned char swd_write_data(unsigned int addr, unsigned int *p) {
  unsigned char ack, req;
  unsigned char APnDP, RnW;
  unsigned char tmp;
  APnDP = 1;
  RnW = 0;
  tmp = SWD_MEMAP_TAR_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, &addr) != 0x01) {
    return 0;
  }
  APnDP = 1;
  RnW = 0;
  tmp = SWD_MEMAP_DRW_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, p) != 0x01) {
    return 0;
  }

  APnDP = 0;
  RnW = 1;
  tmp = SWD_DP_RDBUFF_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  ack = swd_transfer_retry(req, p);
  /*if(ack != 0x01)
  {
      return 0;
  }
  else
  {
      return 1;
  }*/
  return (ack == 0x01);
}

static unsigned char swd_write_byte(unsigned int addr, unsigned char p) {
  unsigned int tmp;
  unsigned int csw_value = 0x23000050;
  if (!swd_ap_write(SWD_MEMAP_CSW_ADDR, &csw_value)) {
    return 0;
  }
  tmp = p << ((addr & 0x03) << 3);
  if (!swd_write_data(addr, &tmp)) {
    return 0;
  }
  return 1;
}

static unsigned char swd_write_word(unsigned int addr, unsigned int *val) {
  // 32-bit accrss,Increment single,enable
  unsigned int csw_value = 0x23000052;
  if (!swd_ap_write(SWD_MEMAP_CSW_ADDR, &csw_value)) {
    return 0;
  }
  if (!swd_write_data(addr, val)) {
    return 0;
  }
  return 1;
}

static unsigned char swd_write_memory(unsigned int addr, unsigned char *p,
                                      unsigned int len) {
  unsigned int n;
  while ((len > 0) && (addr & 0x3)) {
    if (!swd_write_byte(addr, *p)) {
      return 0;
    }
    addr++;
    p++;
    len--;
  }
  while (len > 3) {
    n = g_page_size - (addr & (g_page_size - 1));
    if (len < n) {
      n = len & 0xFFFFFFFC;
    }
    if (!swd_write_block(addr, p, n)) {
      return 0;
    }
    addr += n;
    p += n;
    len -= n;
  }
  while (len > 0) {
    if (!swd_write_byte(addr, *p)) {
      return 0;
    }
    addr++;
    p++;
    len--;
  }
  return 1;
}

static unsigned char swd_read_block(unsigned int addr, unsigned char *p,
                                    unsigned int len) {
  unsigned char req;
  unsigned char APnDP, RnW;
  unsigned char tmp;
  unsigned int size_in_words, i;
  unsigned int csw_value = 0x23000052;
  if (len == 0) {
    return 0;
  }
  size_in_words = len / 4;
  if (!swd_ap_write(SWD_MEMAP_CSW_ADDR, &csw_value)) {
    return 0;
  }
  // TAR
  APnDP = 1;
  RnW = 0;
  tmp = SWD_MEMAP_TAR_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, &addr) != 0x01) {
    return 0;
  }

  // READ
  APnDP = 1;
  RnW = 1;
  tmp = SWD_MEMAP_DRW_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, (unsigned int *)p) != 0x01) {
    return 0;
  }

  for (i = 0; i < size_in_words; i++) {
    if (swd_transfer_retry(req, (unsigned int *)p) != 0x01) {
      return 0;
    }
    p += 4;
  }

  // dummy read
  APnDP = 0;
  RnW = 1;
  tmp = SWD_DP_RDBUFF_ADDR;
  swd_generate_request(&APnDP, &RnW, &tmp, &req);
  if (swd_transfer_retry(req, &csw_value) != 0x01) {
    return 0;
  }
  return 1;
}

static unsigned char swd_read_byte(unsigned int addr, unsigned char *p) {
  unsigned int val;
  // 32-bit accrss,Increment single,enable
  // unsigned int csw_value = 0x23000052;
  unsigned int csw_value = 0x23000050;
  if (!swd_ap_write(SWD_MEMAP_CSW_ADDR, &csw_value)) {
    return 0;
  }
  if (!swd_read_data(addr, &val)) {
    return 0;
  }
  *p = (unsigned char)(val >> ((addr & 0x03) << 3));
  return 1;
}

// static
unsigned char swd_read_memory(unsigned int addr, unsigned char *p,
                              unsigned int len) {
  unsigned int n;
  // Read until word aligned
  while ((len > 0) && (addr & 0x3)) {
    if (!swd_read_byte(addr, p)) {
      return 0;
    }
    addr++;
    p++;
    len--;
  }
  while (len > 3) {
    n = g_page_size - (addr & (g_page_size - 1));
    if (len < n) {
      n = len & 0xFFFFFFFC;
    }
    if (!swd_read_block(addr, p, n)) {
      return 0;
    }
    addr += n;
    p += n;
    len -= n;
  }
  while (len > 0) {
    if (!swd_read_byte(addr, p)) {
      return 0;
    }
    addr++;
    p++;
    len--;
  }
  return 1;
}
#define REG_APPROTECTSTATUS_ADDR 0x0000000C
#define REG_ERASEALLSTATUS_ADDR 0x00000008
#define REG_ERASEALL_ADDR 0x00000004
#define REG_RESET_ADDR 0x00000000

unsigned char swd_download(unsigned char *p, unsigned int len,
                           unsigned char base) {
  unsigned int tmp;
  tmp = SWD_DP_ABORT_STKCMPCLR | SWD_DP_ABORT_STKERRCLR |
        SWD_DP_ABORT_WDERRCLR | SWD_DP_ABORT_ORUNERRCLR;
  if (!swd_dp_write(SWD_DP_ABORT_ADDR, &tmp)) {
    // CException_ThrowISOException(SW_SWD_ERROR);
    return 0;
  }
  tmp = 0;
  if (!swd_dp_write(SWD_DP_SELECT_ADDR, &tmp)) {
    // CException_ThrowISOException(SW_SWD_ERROR);
    return 0;
  }
  do {
    swd_read_word(NVMC_ADDRESS + READY_OFFSET, &tmp);
  } while (tmp != NVMCREADY);

  tmp = NVMCWEN;
  if (!swd_write_word(NVMC_ADDRESS + CONFIG_OFFSET, &tmp)) {
    // CException_ThrowISOException(SW_SWD_ERROR);
    return 0;
  }
  if (base == ERASE_ALL) {
    return swd_write_memory(EEPROM_START + g_offset, p, len);
  } else if (base == ERASE_PAGE) {
    return swd_write_memory(EEPROM_START_APP + g_offset, p, len);
  } else {
    return swd_write_memory(FIRMWARE_PIN_ADDRESS, p, len);
  }
}

unsigned char swd_get_flash_tag() {
  unsigned char val[128];
  unsigned int tmp;
  tmp = SWD_DP_ABORT_STKCMPCLR | SWD_DP_ABORT_STKERRCLR |
        SWD_DP_ABORT_WDERRCLR | SWD_DP_ABORT_ORUNERRCLR;
  if (!swd_dp_write(SWD_DP_ABORT_ADDR, &tmp)) {
    return 0;
  }
  tmp = 0;
  if (!swd_dp_write(SWD_DP_SELECT_ADDR, &tmp)) {
    return 0;
  }
  do {
    swd_read_word(NVMC_ADDRESS + READY_OFFSET, &tmp);
  } while (tmp != NVMCREADY);
  tmp = NVMCREN;
  if (!swd_write_word(NVMC_ADDRESS + CONFIG_OFFSET, &tmp)) {
    return 0;
  }
  do {
    swd_read_word(NVMC_ADDRESS + READY_OFFSET, &tmp);
  } while (tmp != NVMCREADY);
  swd_read_memory(EEPROM_START, val, g_page_size);
  return val[0];
}

unsigned char swd_check_code(unsigned int bleaddr, unsigned int len,
                             unsigned char base) {
  unsigned char val[128];
  //   unsigned short check1;
  unsigned int tmp;
  tmp = SWD_DP_ABORT_STKCMPCLR | SWD_DP_ABORT_STKERRCLR |
        SWD_DP_ABORT_WDERRCLR | SWD_DP_ABORT_ORUNERRCLR;
  if (!swd_dp_write(SWD_DP_ABORT_ADDR, &tmp)) {
    return 0;
  }
  tmp = 0;
  if (!swd_dp_write(SWD_DP_SELECT_ADDR, &tmp)) {
    return 0;
  }
  do {
    swd_read_word(NVMC_ADDRESS + READY_OFFSET, &tmp);
  } while (tmp != NVMCREADY);
  tmp = NVMCREN;
  if (!swd_write_word(NVMC_ADDRESS + CONFIG_OFFSET, &tmp)) {
    return 0;
  }
  //    check1 = 0;
  tmp = 0;
  while (len > g_page_size) {
    if (base == ERASE_ALL) {
      // swd_read_memory(EEPROM_START+tmp,val,g_page_size);
      swd_read_block(EEPROM_START + tmp, val, g_page_size);
    } else if (base == ERASE_PAGE) {
      // swd_read_memory(EEPROM_START_APP+tmp,val,g_page_size);
      swd_read_block(EEPROM_START_APP + tmp, val, g_page_size);
    }
    // swd_update_crc(val,g_page_size);

    // not use crc
    vHAL_Read(bleaddr + tmp, flashram, (unsigned short)g_page_size);
    if (0 == ucSRAM_MemoryCmp(flashram, val, (unsigned short)g_page_size)) {
      //			bleaddr += tmp ;
      //			vSRAM_MemoryMove(&g_ucAbRam[16], (INT8U
      //*)&bleaddr, 4); 			vSRAM_MemoryMove(&g_ucAbRam[20],
      //(INT8U *)&len, 4); vSRAM_MemoryMove(&g_ucAbRam[24], (INT8U
      //*)&g_page_size, 4);
      // vSRAM_MemoryMove(&g_ucAbRam[28], val, 16);
      //			vSRAM_MemoryMove(&g_ucAbRam[44], flashram, 16);
      return 0;
    }
    len -= g_page_size;
    tmp += g_page_size;
  }
  if (len) {
    if (base == ERASE_ALL) {
      // swd_read_memory(EEPROM_START+tmp,val,g_page_size);
      swd_read_block(EEPROM_START + tmp, val, len);
    } else if (base == ERASE_PAGE) {
      // swd_read_memory(EEPROM_START_APP+tmp,val,g_page_size);
      swd_read_block(EEPROM_START_APP + tmp, val, len);
    }
    // swd_update_crc(val,g_page_size);

    // not use crc
    vHAL_Read(bleaddr + tmp, flashram, (unsigned short)len);
    if (0 == ucSRAM_MemoryCmp(flashram, val, (unsigned short)len)) {
      //			bleaddr += tmp ;
      //			vSRAM_MemoryMove(&g_ucAbRam[16], (INT8U
      //*)&bleaddr, 4); 			vSRAM_MemoryMove(&g_ucAbRam[20],
      //(INT8U *)&len, 4); vSRAM_MemoryMove(&g_ucAbRam[24], (INT8U
      //*)&g_page_size, 4);
      // vSRAM_MemoryMove(&g_ucAbRam[28], val, 16);
      //			vSRAM_MemoryMove(&g_ucAbRam[44], flashram, 16);
      return 0;
    }
  }
  //    check1 = CRC_RES;
  //    return (check1 == g_crc);
  return 1;
}

void swd_io_init() {
  rcc_periph_clock_enable(RCC_GPIOC);
  gpio_mode_setup(GPIO_SWD_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_PULLUP,
                  GPIO_SWD_CLK);
  gpio_mode_setup(GPIO_SWD_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_PULLUP,
                  GPIO_SWD_SDA);
  set_swd_clk();
  set_swd_sda();
}
