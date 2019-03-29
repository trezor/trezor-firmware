#define USB_INTERFACE_INDEX_MAIN 0

#define ENDPOINT_ADDRESS_IN (0x81)
#define ENDPOINT_ADDRESS_OUT (0x01)

static const struct usb_device_descriptor dev_descr = {
    .bLength = USB_DT_DEVICE_SIZE,
    .bDescriptorType = USB_DT_DEVICE,
    .bcdUSB = 0x0210,
    .bDeviceClass = 0,
    .bDeviceSubClass = 0,
    .bDeviceProtocol = 0,
    .bMaxPacketSize0 = 64,
    .idVendor = 0x1209,
    .idProduct = 0x53c0,
    .bcdDevice = 0x0100,
    .iManufacturer = 1,
    .iProduct = 2,
    .iSerialNumber = 3,
    .bNumConfigurations = 1,
};

static const struct usb_endpoint_descriptor endpoints[2] = {
    {
        .bLength = USB_DT_ENDPOINT_SIZE,
        .bDescriptorType = USB_DT_ENDPOINT,
        .bEndpointAddress = ENDPOINT_ADDRESS_IN,
        .bmAttributes = USB_ENDPOINT_ATTR_INTERRUPT,
        .wMaxPacketSize = 64,
        .bInterval = 1,
    },
    {
        .bLength = USB_DT_ENDPOINT_SIZE,
        .bDescriptorType = USB_DT_ENDPOINT,
        .bEndpointAddress = ENDPOINT_ADDRESS_OUT,
        .bmAttributes = USB_ENDPOINT_ATTR_INTERRUPT,
        .wMaxPacketSize = 64,
        .bInterval = 1,
    }};

static const struct usb_interface_descriptor iface[] = {{
    .bLength = USB_DT_INTERFACE_SIZE,
    .bDescriptorType = USB_DT_INTERFACE,
    .bInterfaceNumber = USB_INTERFACE_INDEX_MAIN,
    .bAlternateSetting = 0,
    .bNumEndpoints = 2,
    .bInterfaceClass = USB_CLASS_VENDOR,
    .bInterfaceSubClass = 0,
    .bInterfaceProtocol = 0,
    .iInterface = 0,
    .endpoint = endpoints,
    .extra = NULL,
    .extralen = 0,
}};

static const struct usb_interface ifaces[] = {{
    .num_altsetting = 1,
    .altsetting = iface,
}};

static const struct usb_config_descriptor config = {
    .bLength = USB_DT_CONFIGURATION_SIZE,
    .bDescriptorType = USB_DT_CONFIGURATION,
    .wTotalLength = 0,
    .bNumInterfaces = 1,
    .bConfigurationValue = 1,
    .iConfiguration = 0,
    .bmAttributes = 0x80,
    .bMaxPower = 0x32,
    .interface = ifaces,
};

static const char *usb_strings[] = {
    "SatoshiLabs",
    "TREZOR",
    "000000000000000000000000",
};
