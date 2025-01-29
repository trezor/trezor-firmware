

#include <stdint.h>
#include <string.h>
#include "ndef.h"

// ndef_status_t parse_ndef_message(uint8_t *buffer, uint16_t buffer_len ,ndef_message_t *message){

//     memset(message, 0, sizeof(ndef_message_t));

//     uint16_t offset = 0;
//     uint16_t remainin_len = buffer_len

//     while(1){

//         ndef_record_t record;
//         parse_ndef_record(buffer + offset, remainin_len , &record);
//         offset += record.payload_length;

//         message->records_cnt++;
//         if(message->records_cnt >= NDEF_MAX_RECORDS){
//             break; // Max records reached
//         }
//     }

//     return NDEF_OK;
// }

ndef_status_t parse_ndef_record(uint8_t *buffer, uint16_t len, ndef_record_t *rec){

  uint8_t bp = 0;

  // Check if there is enough items to cover first part of the header revelaing record length
  if(len < 3){
    return NDEF_ERROR; // Not enough data to parse
  }

  // Look at first byte, parse header
  memcpy(&(rec->header), buffer, 1);
  bp++;

  if(rec->header.tnf == 0x00 || rec->header.tnf > 0x06){
    return NDEF_ERROR; // Empty or non-existing record
  }

  rec->type_length = buffer[bp++];

  if(rec->header.sr){
    rec->payload_length = buffer[bp++];
  }else{
    memcpy(&(rec->payload_length), buffer + bp, 4);
    bp += 4;
  }

  if(rec->header.il){
    rec->id_length = buffer[bp++];
  }else{
    // ID length ommited
    rec->id_length = 0;
  }

  if(rec->type_length > 0){
    memcpy(&(rec->type), buffer + bp, rec->type_length);
    bp += rec->type_length;
  }else{
    // Type length ommited
    rec->type = 0;
  }

  if(rec->id_length > 0){
    memcpy(&(rec->id), buffer + bp, rec->id_length);
    bp += rec->id_length;
  }else{
    // ID length ommited
    rec->id = 0;
  }

  if(rec->payload_length > 0){
    memcpy(rec->payload, buffer + bp, rec->payload_length);
    bp += rec->payload_length;
  }else{
    // Payload length ommited;
  }

  rec->record_total_len = bp;

  return NDEF_OK;

}



