#pragma once
#pragma endian little

// You must download standard libraries via menu
// Help->Content Store->Libraries

#include <std/io.pat>
#include <std/mem.pat>
#include <std/sys.pat>

#define FW_MAGIC_OLD "TRZR"
#define FW_MAGIC_NEW "TRZF"

struct ImageHeader_v1 {
  char magic_old[4];
  u32 code_length;
  u8 key_indexes[3];
  u8 flags;
  u8 __reserved1[52];
  u8 sig1[64];
  u8 sig2[64];
  u8 sig3[64];
};

struct ImageHeader_v2 {
  char magic_new[4];
  u32 hdrlen_or_reset_handler_thumb;
  u32 expiry;
  u32 codelen;
  u32 version;
  u32 fix_version;
  u8 __reserved1[8];
  u8 hashes[512];
  u8 sig1[64];
  u8 sig2[64];
  u8 sig3[64];
  u8 sigindex1;
  u8 sigindex2;
  u8 sigindex3;
  u8 __reserved2[220];
  u8 __sigmask;
  u8 __sig[64];
};

fn base() {
    return std::mem::base_address();
};

//#define VTOR    (base()+0x500)
 //0x8010400

bitfield ARMAddress {
  ThumbMode : 1;
  Address : 31 [[transform("address_transform")]];
} [[right_to_left]];

fn address_transform(u32 value) {
  return value << 1;
};

fn address_mask(u32 value) {
  return value & 0xFFFFFFFE;
};

using Address = u32;

struct Exceptions {
        Address reset [[name("Reset Handler"), transform("address_mask")]];
        // size is just estimate so that it highlights some bytes
        u8 reset_function[256] @ reset;
        Address nmi [[name("Non-maskable Interrupt Handler")]];
        Address hard_fault [[name("HardFault Handler")]];
        Address mem_manage [[name("Memory Protection Error Handler")]];
        Address bus_fault [[name("Bus Fault Handler")]];
        Address usage_fault [[name("UsageFault (Instruction Execution fault) Handler")]];
        Address reserved_1[4] [[hidden]];
        Address sv_call [[name("Synchronous Supervisor Call (SVC Instruction) Handler")]];
        Address debug_monitor [[name("Synchronous Debug Event Handler")]];
        Address reserved_2[1] [[hidden]];
        Address pend_sv [[name("Asynchronous Supervisor Call Handler")]];
        Address sys_tick [[name("System Timer Tick Handler")]];
};

struct VectorTable {
        Address initial_sp [[name("Initial Stack Pointer Value")]];
        Exceptions exceptions [[inline, name("Exceptions")]];
};




