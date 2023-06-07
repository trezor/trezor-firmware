#include "dis.h"
#include <string.h>
#include "app_error.h"
#include "ble_dis.h"
#include "sdk_errors.h"

#define MANUFACTURER_NAME                                               \
  "SatoshiLabs" /**< Manufacturer. Will be passed to Device Information \
                   Service. */

void dis_init(void) {
  ret_code_t err_code;
  ble_dis_init_t dis_init_obj;

  memset(&dis_init_obj, 0, sizeof(dis_init_obj));

  ble_srv_ascii_to_utf8(&dis_init_obj.manufact_name_str, MANUFACTURER_NAME);

  dis_init_obj.dis_char_rd_sec = SEC_JUST_WORKS;

  err_code = ble_dis_init(&dis_init_obj);
  APP_ERROR_CHECK(err_code);
}
