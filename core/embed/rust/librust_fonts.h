typedef struct {
  const uint8_t* ptr;
  uint32_t len;
} PointerData;

// TODO: Theoretically, the `len` is not used by the client and does not have to be sent
PointerData get_utf8_glyph(uint16_t char_code, int font);
