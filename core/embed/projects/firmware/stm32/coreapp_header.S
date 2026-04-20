  .syntax unified

  .text

  .section .coreapp_header, "a"
coreapp_header:
  .word reset_handler
  .word _stack_section_start
  .word _stack_section_size

#ifdef USE_APP_LOADING
  .word _tls_section_start
  .word _tls_section_size
  .word coreapp_api_get
#else
  .word 0
  .word 0
  .word 0
#endif

#if USE_STORAGE_HWKEY
  .word saes_unpriv_input
  .word saes_unpriv_output
  .word saes_unpriv_callback
#else
  .word 0
  .word 0
  .word 0
#endif


  .end
