typedef struct {
  const uint8_t* ptr;
  uint32_t len;
} PointerData;

PointerData get_utf8_glyph(uint16_t char_code, int font);
