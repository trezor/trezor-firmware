/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

void pendsv_kbd_intr(void);

/// package: trezorio.__init__

/// class VCP:
///     """
///     USB VCP interface configuration.
///     """
typedef struct _mp_obj_VCP_t {
  mp_obj_base_t base;
  usb_vcp_info_t info;
} mp_obj_VCP_t;

/// def __init__(
///     self,
///     iface_num: int,
///     data_iface_num: int,
///     ep_in: int,
///     ep_out: int,
///     ep_cmd: int,
///     emu_port: int,
/// ) -> None:
///     """
///     """
STATIC mp_obj_t mod_trezorio_VCP_make_new(const mp_obj_type_t *type,
                                          size_t n_args, size_t n_kw,
                                          const mp_obj_t *args) {
  STATIC const mp_arg_t allowed_args[] = {
      {MP_QSTR_iface_num,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_data_iface_num,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_ep_in,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_ep_out,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_ep_cmd,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
      {MP_QSTR_emu_port,
       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT,
       {.u_int = 0}},
  };
  mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)] = {0};
  mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args),
                            allowed_args, vals);

  const mp_int_t iface_num = vals[0].u_int;
  const mp_int_t data_iface_num = vals[1].u_int;
  const mp_int_t ep_in = vals[2].u_int;
  const mp_int_t ep_out = vals[3].u_int;
  const mp_int_t ep_cmd = vals[4].u_int;
  const mp_int_t emu_port = vals[5].u_int;

  CHECK_PARAM_RANGE(iface_num, 0, 32)
  CHECK_PARAM_RANGE(data_iface_num, 0, 32)
  CHECK_PARAM_RANGE(ep_in, 0, 255)
  CHECK_PARAM_RANGE(ep_out, 0, 255)
  CHECK_PARAM_RANGE(ep_cmd, 0, 255)
  CHECK_PARAM_RANGE(emu_port, 0, 65535)

  const size_t vcp_buffer_len = 1024;
  const size_t vcp_packet_len = 64;

  mp_obj_VCP_t *o = m_new_obj(mp_obj_VCP_t);
  o->base.type = type;

  o->info.tx_packet = m_new(uint8_t, vcp_packet_len);
  o->info.tx_buffer = m_new(uint8_t, vcp_buffer_len);
  o->info.rx_packet = m_new(uint8_t, vcp_packet_len);
  o->info.rx_buffer = m_new(uint8_t, vcp_buffer_len);
  o->info.tx_buffer_len = vcp_buffer_len;
  o->info.rx_buffer_len = vcp_buffer_len;
  o->info.rx_intr_fn = pendsv_kbd_intr;
  o->info.rx_intr_byte = 3;  // Ctrl-C
  o->info.iface_num = (uint8_t)(iface_num);
  o->info.data_iface_num = (uint8_t)(data_iface_num);
#ifdef TREZOR_EMULATOR
  o->info.emu_port = (uint16_t)(emu_port);
#else
  o->info.ep_cmd = (uint8_t)(ep_cmd);
  o->info.ep_in = (uint8_t)(ep_in);
  o->info.ep_out = (uint8_t)(ep_out);
#endif
  o->info.polling_interval = 10;
  o->info.max_packet_len = (uint8_t)(vcp_packet_len);

  return MP_OBJ_FROM_PTR(o);
}

/// def iface_num(self) -> int:
///     """
///     Returns the configured number of this interface.
///     """
STATIC mp_obj_t mod_trezorio_VCP_iface_num(mp_obj_t self) {
  mp_obj_VCP_t *o = MP_OBJ_TO_PTR(self);
  return MP_OBJ_NEW_SMALL_INT(o->info.iface_num);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_VCP_iface_num_obj,
                                 mod_trezorio_VCP_iface_num);

STATIC const mp_rom_map_elem_t mod_trezorio_VCP_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_iface_num),
     MP_ROM_PTR(&mod_trezorio_VCP_iface_num_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_VCP_locals_dict,
                            mod_trezorio_VCP_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_VCP_type = {
    {&mp_type_type},
    .name = MP_QSTR_VCP,
    .make_new = mod_trezorio_VCP_make_new,
    .locals_dict = (void *)&mod_trezorio_VCP_locals_dict,
};
