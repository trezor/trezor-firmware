static void send_msg_success(usbd_device *dev) {
  uint8_t response[64];
  memzero(response, sizeof(response));
  // response: Success message (id 2), payload len 0
  memcpy(response,
         // header
         "?##"
         // msg_id
         "\x00\x02"
         // msg_size
         "\x00\x00\x00\x00",
         9);
  while (usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN, response, 64) != 64) {
  }
}

static void send_msg_failure(usbd_device *dev, uint8_t code) {
  uint8_t response[64];
  memzero(response, sizeof(response));
  // response: Failure message (id 3), payload len 2
  memcpy(response,
         // header
         "?##"
         // msg_id
         "\x00\x03"
         // msg_size
         "\x00\x00\x00\x02"
         // code field id
         "\x08",
         10);
  // assign code value
  response[10] = code;
  while (usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN, response, 64) != 64) {
  }
}

static void send_msg_features(usbd_device *dev) {
  uint8_t response[64];
  memzero(response, sizeof(response));
  // response: Features message (id 17), payload len 26 / 41
  //           - vendor = "trezor.io"
  //           - major_version = VERSION_MAJOR
  //           - minor_version = VERSION_MINOR
  //           - patch_version = VERSION_PATCH
  //           - bootloader_mode = True
  //           - firmware_present = True/False
  //           - model = "1"
  //           ? fw_version_major = version_major
  //           ? fw_version_minor = version_minor
  //           ? fw_version_patch = version_patch
  const bool firmware_present = firmware_present_new();
  const image_header *current_hdr = (const image_header *)FLASH_FWHEADER_START;
  uint32_t version = firmware_present ? current_hdr->version : 0;

  // clang-format off
  const uint8_t feature_bytes[] = {
    0x0a,  // vendor field
    0x09,  // vendor length
    't', 'r', 'e', 'z', 'o', 'r', '.', 'i', 'o',
    0x10, VERSION_MAJOR,
    0x18, VERSION_MINOR,
    0x20, VERSION_PATCH,
    0x28, 0x01, // bootloader_mode
    0x90, 0x01, // firmware_present field
    firmware_present ? 0x01 : 0x00,
    0xaa, 0x01, // model field
    0x01,      // model length
    '1',
  };

  const uint8_t version_bytes[] = {
    // fw_version_major
    0xb0, 0x01, version & 0xff,
    // fw_version_minor
    0xb8, 0x01, (version >> 8) & 0xff,
    // fw_version_patch
    0xc0, 0x01, (version >> 16) & 0xff,
  };

  uint8_t header_bytes[] = {
    // header
    '?', '#', '#',
    // msg_id
    0x00, 0x11,
    // msg_size
    0x00, 0x00, 0x00, sizeof(feature_bytes) + (firmware_present ? sizeof(version_bytes) : 0),
  };
  // clang-format on

  // Check that the response will fit into an USB packet, and also that the
  // sizeof expression above fits into a single byte
  _Static_assert(
      sizeof(feature_bytes) + sizeof(version_bytes) + sizeof(header_bytes) <=
          64,
      "Features response too long");

  memcpy(response, header_bytes, sizeof(header_bytes));
  memcpy(response + sizeof(header_bytes), feature_bytes, sizeof(feature_bytes));
  if (firmware_present) {
    memcpy(response + sizeof(header_bytes) + sizeof(feature_bytes),
           version_bytes, sizeof(version_bytes));
  }

  while (usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN, response, 64) != 64) {
  }
}

static void send_msg_buttonrequest_firmwarecheck(usbd_device *dev) {
  uint8_t response[64];
  memzero(response, sizeof(response));
  // response: ButtonRequest message (id 26), payload len 2
  //           - code = ButtonRequest_FirmwareCheck (9)
  memcpy(response,
         // header
         "?##"
         // msg_id
         "\x00\x1a"
         // msg_size
         "\x00\x00\x00\x02"
         // data
         "\x08"
         "\x09",
         11);
  while (usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN, response, 64) != 64) {
  }
}
