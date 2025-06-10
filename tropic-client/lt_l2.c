#include <string.h>
#include <stdint.h>
#include <assert.h>
#include <stdio.h>

#include "libtropic_common.h"
#include "lt_l2.h"

static uint8_t half_byte_to_hex(uint8_t input) {
    assert(input < 16);
    return (input < 10) ? (input + '0') : (input - 10 + 'A');
}

static uint8_t hex_to_half_byte(uint8_t input) {
    assert((input >= '0' && input <= '9') || (input >= 'A' && input <= 'F'));
    return (input < 'A') ? (input - '0') : (input - 'A' + 10);
}

static void bytes_to_hex(const uint8_t *input, size_t input_length,
                         uint8_t *output, size_t *output_length) {
  assert(input != NULL);
  assert(output != NULL);
  assert(output_length != NULL);
  // assert(*output_length >= input_length * 2 + 1);

  size_t i;
  for (i = 0; i < input_length; i++) {
      output[i * 2] = half_byte_to_hex((input[i] >> 4) & 0x0F);
      output[i * 2 + 1] = half_byte_to_hex(input[i] & 0x0F);
  }
  output[i * 2] = '\0';  // Null-terminate the string

  *output_length = input_length * 2 + 1;
}

static void hex_to_bytes(const uint8_t *input, size_t input_length,
                         uint8_t *output, size_t *output_length) {
  assert(input != NULL);
  assert(output != NULL);
  assert(output_length != NULL);
  // assert(*output_length >= input_length/2);

  size_t i;
  for (i = 0; i < input_length / 2; i++) {
      output[i] = (hex_to_half_byte(input[i * 2]) << 4) |
                  hex_to_half_byte(input[i * 2 + 1]);
  }
  *output_length = input_length / 2;
}

void request_data(uint8_t *input, size_t input_length, uint8_t *output, size_t *output_length)
{
  uint8_t hex_buffer[10000] = {0};
  size_t hex_length = sizeof(hex_buffer);

  bytes_to_hex(input, input_length, hex_buffer, &hex_length);

  printf("Sending data: %s\n", hex_buffer);
  printf("Receiving data: ");

  fgets((char*)hex_buffer, sizeof(hex_buffer), stdin);
  hex_length = strlen((const char *)hex_buffer) - 1;

  hex_to_bytes(hex_buffer, hex_length, output, output_length);
}

void send_data(uint8_t *data, size_t data_length)
{
    uint8_t hex_buffer[10000] = {0};
    size_t hex_length = sizeof(hex_buffer);

    bytes_to_hex(data, data_length, hex_buffer, &hex_length);

    printf("Sending data: %s\n", hex_buffer);
}

void receive_data(uint8_t *data, size_t data_max_length, size_t *data_length)
{
    uint8_t hex_buffer[10000] = {0};
    size_t hex_length = sizeof(hex_buffer);

    fgets((char*)hex_buffer, sizeof(hex_buffer), stdin);
    hex_length = strlen((const char *)hex_buffer) - 1;

    if (hex_length > data_max_length * 2) {
        return;
    }

    hex_to_bytes(hex_buffer, hex_length, data, data_length);
}

lt_ret_t lt_l2_read(lt_handle_t *h, uint8_t *data, size_t data_max_length, size_t *data_length)
{
    if (!h || !data || !data_length) {
        return LT_PARAM_ERR;
    }

    size_t length = h->l2.buff[1] + 2;

    if (length > data_max_length) {
        return LT_PARAM_ERR;
    }

    memcpy(data, h->l2.buff, length);
    *data_length = length;

    return LT_OK;
}

lt_ret_t lt_l2_write(lt_handle_t *h, const uint8_t *data, size_t data_length)
{
    if (!h || !data) {
        return LT_PARAM_ERR;
    }

    memcpy(h->l2.buff, data, data_length);

    // TODO: Chech if the data_length equals to h->l2.buff[1] + 2

    return LT_OK;
}

lt_ret_t lt_l2_transfer(lt_handle_t *h)
{
    size_t length = h->l2.buff[1] + 2;
    printf("input length: %zu\n", length);
    size_t max_length = sizeof(h->l2.buff);

    request_data(h->l2.buff, length, h->l2.buff, &max_length);
    printf("output length: %zu\n", max_length);

    return LT_OK;
}

lt_ret_t lt_l2_encrypted_cmd(lt_handle_t *h)
{
    printf("L3\n");
    size_t input_length = ((struct lt_l3_gen_frame_t*)h->l3.buff)->cmd_size + 2 + 16;
    size_t output_length = sizeof(h->l3.buff);
    request_data(h->l3.buff, input_length, h->l3.buff, &output_length);
    return LT_OK;
}

lt_ret_t lt_l3_read(lt_handle_t *h, uint8_t *data, size_t data_max_length, size_t *data_length)
{
    if (!h || !data || !data_length) {
        return LT_PARAM_ERR;
    }

    size_t length = ((struct lt_l3_gen_frame_t*)h->l3.buff)->cmd_size + 2 + 16;

    if (length > data_max_length) {
        return LT_PARAM_ERR;
    }

    memcpy(data, h->l3.buff, length);
    *data_length = length;

    return LT_OK;
}

lt_ret_t lt_l3_write(lt_handle_t *h, const uint8_t *data, size_t max_data_length, size_t *data_length)
{
    if (!h || !data) {
        return LT_PARAM_ERR;
    }

    size_t length = ((struct lt_l3_gen_frame_t*)data)->cmd_size + 2 + 16;

    if (max_data_length < length) {
        return LT_PARAM_ERR;
    }

    memcpy(h->l3.buff, data, length);
    *data_length = length;

    return LT_OK;

    // TODO: Check if the data_length equals to ((struct lt_l3_gen_frame_t*)h->l3.buff)->cmd_size + 2 + 16
}
