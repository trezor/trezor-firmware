#pragma GCC diagnostic ignored "-Wunused-value"
#pragma GCC diagnostic ignored "-Wunused-function"

static void _librust_qstrs(void) {
  // protobuf
  MP_QSTR_Msg;
  MP_QSTR_MsgDef;
  MP_QSTR_is_type_of;
  MP_QSTR_MESSAGE_WIRE_TYPE;
  MP_QSTR_MESSAGE_NAME;

  // layout
  MP_QSTR___name__;
  MP_QSTR_trezorui2;
  MP_QSTR_Layout;
  MP_QSTR_CONFIRMED;
  MP_QSTR_CANCELLED;
  MP_QSTR_confirm_action;
  MP_QSTR_confirm_text;
  MP_QSTR_request_pin;

  // storagedevice
  MP_QSTR___name_storage__;
  MP_QSTR_is_version_stored;
  MP_QSTR_is_initialized;
  MP_QSTR_set_is_initialized;
  MP_QSTR_get_version;
  MP_QSTR_set_version;
  MP_QSTR_get_rotation;
  MP_QSTR_set_rotation;
  MP_QSTR_get_label;
  MP_QSTR_set_label;
  MP_QSTR_get_device_id;
  MP_QSTR_set_device_id;
  MP_QSTR_get_mnemonic_secret;
  MP_QSTR_set_mnemonic_secret;
  MP_QSTR_is_passphrase_enabled;
  MP_QSTR_set_passphrase_enabled;
  MP_QSTR_get_passphrase_always_on_device;
  MP_QSTR_set_passphrase_always_on_device;
  MP_QSTR_unfinished_backup;
  MP_QSTR_set_unfinished_backup;
  MP_QSTR_needs_backup;
  MP_QSTR_set_backed_up;
  MP_QSTR_no_backup;
  MP_QSTR_get_backup_type;
  MP_QSTR_get_homescreen;
  MP_QSTR_set_homescreen;
  MP_QSTR_get_slip39_identifier;
  MP_QSTR_set_slip39_identifier;
  MP_QSTR_get_slip39_iteration_exponent;
  MP_QSTR_set_slip39_iteration_exponent;
  MP_QSTR_get_autolock_delay_ms;
  MP_QSTR_set_autolock_delay_ms;
  MP_QSTR_get_flags;
  MP_QSTR_set_flags;
  MP_QSTR_get_safety_check_level;
  MP_QSTR_set_safety_check_level;
  MP_QSTR_get_sd_salt_auth_key;
  MP_QSTR_set_sd_salt_auth_key;
  MP_QSTR_get_next_u2f_counter;
  MP_QSTR_set_u2f_counter;
  MP_QSTR_get_private_u2f_counter;
  MP_QSTR_delete_private_u2f_counter;
  MP_QSTR_get_experimental_features;
  MP_QSTR_set_experimental_features;

  // storagerecovery
  MP_QSTR___name_recovery__;
  MP_QSTR_is_in_progress;
  MP_QSTR_set_in_progress;
  MP_QSTR_is_dry_run;
  MP_QSTR_set_dry_run;
  MP_QSTR_get_slip39_group_count;
  MP_QSTR_set_slip39_group_count;
  MP_QSTR_get_slip39_remaining_shares;
  MP_QSTR_fetch_slip39_remaining_shares;
  MP_QSTR_set_slip39_remaining_shares;
  MP_QSTR_end_progress;

  // storageresidentcredentials
  // TODO: some of these Qstr like MP_QSTR_set are already defined - define them
  // again?
  MP_QSTR___name_residentcredentials__;
  MP_QSTR_set;
  MP_QSTR_get;
  MP_QSTR_delete;
  MP_QSTR_delete_all;

  // storageresidentcredentials
  // TODO: some of these Qstr like MP_QSTR_set are already defined - define them
  // again?
  MP_QSTR___name_recoveryshares__;
  MP_QSTR_set;
  MP_QSTR_get;
  MP_QSTR_fetch_group;
  MP_QSTR_delete;

  MP_QSTR_set_timer_fn;
  MP_QSTR_touch_event;
  MP_QSTR_button_event;
  MP_QSTR_timer;
  MP_QSTR_paint;
  MP_QSTR_trace;
  MP_QSTR_bounds;

  MP_QSTR_title;
  MP_QSTR_action;
  MP_QSTR_description;
  MP_QSTR_verb;
  MP_QSTR_verb_cancel;
  MP_QSTR_reverse;
  MP_QSTR_prompt;
  MP_QSTR_subprompt;
  MP_QSTR_warning;
  MP_QSTR_allow_cancel;
  MP_QSTR_max_len;
  MP_QSTR_secret;
}
