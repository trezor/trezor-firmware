package com.satoshilabs.trezor.ward.relay;

import com.fasterxml.jackson.databind.node.ObjectNode;

/** A Trezor protobuf message by NAME, with its JSON body (bytes as lowercase hex). */
public record DeviceMessage(String name, ObjectNode message) {}
