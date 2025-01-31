

#ifndef NDEF_H
#define NDEF_H

#define NDEF_MAX_RECORDS 3
#define NDEF_MAX_RECORD_PAYLOAD_BYTES 50


typedef enum{
    NDEF_OK = 0,
    NDEF_ERROR = 1,
} ndef_status_t;

typedef struct{
  uint8_t tnf : 3;
  uint8_t il  : 1;
  uint8_t sr  : 1;
  uint8_t cf  : 1;
  uint8_t me  : 1;
  uint8_t mb  : 1;
}ndef_record_header_t;

typedef struct{
  ndef_record_header_t header;
  uint8_t type_length;
  uint32_t payload_length;
  uint8_t id_length;
  uint8_t type;
  uint8_t id;
  uint8_t payload[NDEF_MAX_RECORD_PAYLOAD_BYTES];
  uint16_t record_total_len;
}ndef_record_t;

typedef struct{
    uint32_t message_total_len;
    uint8_t records_cnt;
    ndef_record_t records[NDEF_MAX_RECORDS];
} ndef_message_t;

ndef_status_t parse_ndef_message(uint8_t *buffer, uint16_t buffer_len ,ndef_message_t *message);
ndef_status_t parse_ndef_record(uint8_t *buffer, uint16_t len, ndef_record_t *rec);

#endif
