#include "i18n-block.h"
#include <string.h>
#include "blake2s.h"
#include "ed25519-donna/ed25519.h"

typedef struct {
  const uint8_t *ptr_items;
  const uint8_t *ptr_values;
  uint32_t items_count;
  uint32_t values_size;
  const uint8_t *label;
  char code[6];
} i18n_block_t;

static bool i18n_initialized = false;
static i18n_block_t block = {0};
static ed25519_public_key i18n_pubkey = {0xa3, 0x0c, 0x46, 0x1c, 0xdd, 0x0c, 0xfe, 0xc9, 0x5f, 0xf4, 0xa6, 0xfe, 0x09, 0xc0, 0xd4, 0x7f, 0x5d, 0x2a, 0x18, 0x6c, 0xbc, 0x8b, 0x51, 0xd2, 0xad, 0xeb, 0x5c, 0xe3, 0xac, 0x3a, 0xa0, 0x64};

#ifdef TREZOR_EMULATOR
#include <fcntl.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#endif

static bool _i18n_load(const uint8_t *ptr) {
  // check magic
  if (0 != memcmp(ptr, "TRIB", 4)) {
    return false;
  }
  // check signature
  const ed25519_signature *sig = (const ed25519_signature *)(ptr + 0xC0);
  if (0 != ed25519_sign_open(ptr, 0xC0, i18n_pubkey, *sig)) {
    return false;
  }

  // copy language code
  block.code[0] = ptr[0x2C];
  block.code[1] = ptr[0x2D];
  block.code[2] = '-';
  block.code[3] = ptr[0x2E];
  block.code[4] = ptr[0x2F];
  block.code[5] = 0;
  // assign label
  block.label = ptr + 0x30;

  // assign items/values
  memcpy(&(block.items_count), ptr + 4, sizeof(uint32_t));
  memcpy(&(block.values_size), ptr + 8, sizeof(uint32_t));
  block.ptr_items = ptr + 256;
  block.ptr_values = ptr + 256 + 4 * block.items_count;

  // compute the hash of items + values
  uint8_t hash[BLAKE2S_DIGEST_LENGTH];
  blake2s(block.ptr_items, 4 * block.items_count + block.values_size, hash,
          BLAKE2S_DIGEST_LENGTH);
  // compare the hash
  if (0 != memcmp(ptr + 0x0C, hash, BLAKE2S_DIGEST_LENGTH)) {
    return false;
  }

  // all OK
  i18n_initialized = true;
  return true;
}

bool i18n_init(void) {
#ifdef TREZOR_EMULATOR
  // TODO: this could use some love (similar to mmap in flash.c)
  int fd = open("i18n.dat", O_RDONLY);
  if (fd < 0) return false;
  struct stat s;
  fstat(fd, &s);
  const uint8_t *ptr =
      (const uint8_t *)mmap(0, s.st_size, PROT_READ, MAP_SHARED, fd, 0);
#else
  // the last 128K sector of flash
  const uint8_t *ptr = (const uint8_t *)0x081E0000;
#endif
  return _i18n_load(ptr);
}


const char *i18n_get(uint16_t id, uint16_t *len) {
  if (!i18n_initialized || id >= block.items_count) {
    return NULL;
  }
  memcpy(len, block.ptr_items + 4 * id + 2, 2);
  if (*len == 0) {
    return NULL;
  }
  uint32_t offset = 0;
  memcpy(&offset, block.ptr_items + 4 * id, 2);
  offset *= 4;
  if (offset + *len > block.values_size) {
    return NULL;
  }
  return (const char *)(block.ptr_values + offset);
}
