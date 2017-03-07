#include STM32_HAL_H

#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_cdc_msc_hid.h"
#include "usbd_cdc_interface.h"
#include "usbd_hid_interface.h"

USBD_HandleTypeDef hUSBDDevice;
extern PCD_HandleTypeDef pcd_fs_handle;
extern PCD_HandleTypeDef pcd_hs_handle;

int usb_init(void) {
    const uint16_t vid = 0x1209;
    const uint16_t pid = 0x53C1;

    USBD_HID_ModeInfoTypeDef hid_info = {
        .subclass = 0,
        .protocol = 0,
        .max_packet_len = 64,
        .polling_interval = 1,
        .report_desc = (const uint8_t*)"\x06\x00\xff\x09\x01\xa1\x01\x09\x20\x15\x00\x26\xff\x00\x75\x08\x95\x40\x81\x02\x09\x21\x15\x00\x26\xff\x00\x75\x08\x95\x40\x91\x02\xc0",
        .report_desc_len = 34,
    };

    USBD_SetVIDPIDRelease(vid, pid, 0x0200, 0);
    if (USBD_SelectMode(USBD_MODE_CDC_HID, &hid_info) != 0) {
        return 1;
    }
    USBD_Init(&hUSBDDevice, (USBD_DescriptorsTypeDef*)&USBD_Descriptors, 0); // 0 == full speed
    USBD_RegisterClass(&hUSBDDevice, &USBD_CDC_MSC_HID);
    USBD_CDC_RegisterInterface(&hUSBDDevice, (USBD_CDC_ItfTypeDef*)&USBD_CDC_fops);
    USBD_HID_RegisterInterface(&hUSBDDevice, (USBD_HID_ItfTypeDef*)&USBD_HID_fops);
    USBD_Start(&hUSBDDevice);

    return 0;
}

#if defined(USE_USB_FS)
/**
  * @brief  This function handles USB-On-The-Go FS global interrupt request.
  * @param  None
  * @retval None
  */
void OTG_FS_IRQHandler(void) {
    HAL_PCD_IRQHandler(&pcd_fs_handle);
}
#endif

#if defined(USE_USB_HS)
/**
  * @brief  This function handles USB-On-The-Go HS global interrupt request.
  * @param  None
  * @retval None
  */
void OTG_HS_IRQHandler(void) {
    HAL_PCD_IRQHandler(&pcd_hs_handle);
}
#endif

#if defined(USE_USB_FS) || defined(USE_USB_HS)
/**
  * @brief  This function handles USB OTG Common FS/HS Wakeup functions.
  * @param  *pcd_handle for FS or HS
  * @retval None
  */
STATIC void OTG_CMD_WKUP_Handler(PCD_HandleTypeDef *pcd_handle) {
    if (!(pcd_handle->Init.low_power_enable)) {
        return;
    }

    /* Reset SLEEPDEEP bit of Cortex System Control Register */
    SCB->SCR &= (uint32_t) ~((uint32_t)(SCB_SCR_SLEEPDEEP_Msk | SCB_SCR_SLEEPONEXIT_Msk));

    /* Configures system clock after wake-up from STOP: enable HSE, PLL and select
    PLL as system clock source (HSE and PLL are disabled in STOP mode) */

    __HAL_RCC_HSE_CONFIG(RCC_HSE_ON);

    /* Wait till HSE is ready */
    while (__HAL_RCC_GET_FLAG(RCC_FLAG_HSERDY) == RESET) {}

    /* Enable the main PLL. */
    __HAL_RCC_PLL_ENABLE();

    /* Wait till PLL is ready */
    while (__HAL_RCC_GET_FLAG(RCC_FLAG_PLLRDY) == RESET) {}

    /* Select PLL as SYSCLK */
    MODIFY_REG(RCC->CFGR, RCC_CFGR_SW, RCC_SYSCLKSOURCE_PLLCLK);

    while (__HAL_RCC_GET_SYSCLK_SOURCE() != RCC_CFGR_SWS_PLL) {}

    /* ungate PHY clock */
    __HAL_PCD_UNGATE_PHYCLOCK(pcd_handle);
}
#endif

#if defined(USE_USB_FS)
/**
  * @brief  This function handles USB OTG FS Wakeup IRQ Handler.
  * @param  None
  * @retval None
  */
void OTG_FS_WKUP_IRQHandler(void) {
    OTG_CMD_WKUP_Handler(&pcd_fs_handle);

    /* Clear EXTI pending Bit*/
    __HAL_USB_FS_EXTI_CLEAR_FLAG();
}
#endif

#if defined(USE_USB_HS)
/**
  * @brief  This function handles USB OTG HS Wakeup IRQ Handler.
  * @param  None
  * @retval None
  */
void OTG_HS_WKUP_IRQHandler(void) {
    OTG_CMD_WKUP_Handler(&pcd_hs_handle);

    /* Clear EXTI pending Bit*/
    __HAL_USB_HS_EXTI_CLEAR_FLAG();
}
#endif
