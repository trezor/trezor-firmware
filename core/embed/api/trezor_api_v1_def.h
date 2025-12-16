// clang-format off

API_FN_VOID(system_exit,
  (int exitcode),
  (exitcode))

API_FN_VOID(system_exit_error,
  (const char* title, const char* message, const char* footer),
  (title, message, footer))

API_FN_VOID(system_exit_error_ex,
  (const char* title, size_t title_len,
   const char* message, size_t message_len,
   const char* footer, size_t footer_len),
  (title, title_len, message, message_len, footer, footer_len))

API_FN_VOID(system_exit_fatal,
  (const char* message, const char* file, int line),
  (message, file, line))

API_FN_VOID(system_exit_fatal_ex,
  (const char* message, size_t message_len,
   const char* file, size_t file_len, int line),
  (message, message_len, file, file_len, line))

API_FN(ssize_t, dbg_console_write,
  (const void* data, size_t size),
  (data, size))

API_FN(uint32_t, systick_ms,
  (void),
  ())

API_FN_VOID(sysevents_poll,
  (const sysevents_t* awaited, sysevents_t* signalled, uint32_t deadline),
  (awaited, signalled, deadline))

API_FN(ssize_t, syshandle_read,
  (syshandle_t handle, void* buffer, size_t buffer_size),
  (handle, buffer, buffer_size))

API_FN(bool, ipc_register,
  (systask_id_t remote, void *buffer, size_t size),
  (remote, buffer, size))

API_FN_VOID(ipc_unregister,
  (systask_id_t remote),
  (remote))

API_FN(bool, ipc_try_receive,
  (ipc_message_t *msg),
  (msg))

API_FN_VOID(ipc_message_free,
  (ipc_message_t *msg),
  (msg))

API_FN(bool, ipc_send,
  (systask_id_t remote, uint32_t fn, const void * data, size_t data_size),
  (remote, fn, data, data_size))

// clang-format on
