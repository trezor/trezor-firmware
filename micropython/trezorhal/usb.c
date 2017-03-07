#include STM32_HAL_H

#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_cdc_msc_hid.h"
#include "usbd_cdc_interface.h"
#include "usbd_hid_interface.h"

USBD_HandleTypeDef hUSBDDevice;

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
