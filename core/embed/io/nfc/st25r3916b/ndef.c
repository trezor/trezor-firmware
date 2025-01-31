

#include <stdint.h>
#include <string.h>
#include "ndef.h"



// ndef_status_t create_ndef_record_uri(uint8_t *bytearray, )


ndef_status_t parse_ndef_message(uint8_t *buffer, uint16_t buffer_len ,ndef_message_t *message){


    memset(message, 0, sizeof(ndef_message_t));

    uint16_t remaining_len = buffer_len;


    // Indicate TLV header
    if(*buffer == 0x3){
        buffer++;
    }else{
      return NDEF_ERROR; // Not a valid TLV structure
    }

    // TLV length
    if(*buffer == 0xFF){

        // TLV 3 byte length format
        buffer++;
        message->message_total_len = (int16_t) (buffer[0] << 8 | buffer[1]);
        buffer = buffer + 2;

    }else{

      message->message_total_len  = *buffer;
      buffer++;

    }

    remaining_len = message->message_total_len;

    while(1){

        parse_ndef_record(buffer, remaining_len , &(message->records[message->records_cnt]));
        buffer += message->records[message->records_cnt].record_total_len;
        remaining_len -= message->records[message->records_cnt].record_total_len;
        message->records_cnt++;

        if(message->records_cnt >= NDEF_MAX_RECORDS){
            break; // Max records reached
        }

        if(remaining_len == 0){
          break;
        }

    }

    // Check TLV termination character
    if(*buffer != 0xFE){
      return NDEF_ERROR; // Not a valid TLV structure
    }

    return NDEF_OK;
}

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



