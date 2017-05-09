#include "../../trezorhal/usb.h"

int usb_init(const usb_dev_info_t *dev_info) {
    return 0;
}

int usb_deinit(void) {
    return 0;
}

int usb_start(void) {
    return 0;
}

int usb_stop(void) {
    return 0;
}

int usb_hid_add(const usb_hid_info_t *info) {
    return 0;
}

int usb_vcp_add(const usb_vcp_info_t *info) {
    return 0;
}

void pendsv_kbd_intr(void) {
}

void mp_hal_set_vcp_iface(int iface_num) {
}
