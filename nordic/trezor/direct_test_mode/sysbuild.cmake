#
# Copyright (c) 2024 Nordic Semiconductor
#
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause

if(SB_CONFIG_DTM_NO_DFE)
  add_overlay_dts(
    direct_test_mode
    ${CMAKE_CURRENT_LIST_DIR}/no-dfe.overlay)
endif()

if(SB_CONFIG_DTM_TRANSPORT_HCI)
  set_config_bool(${DEFAULT_IMAGE} CONFIG_DTM_TRANSPORT_HCI y)
else()
  set_config_bool(${DEFAULT_IMAGE} CONFIG_DTM_TRANSPORT_HCI n)
endif()
