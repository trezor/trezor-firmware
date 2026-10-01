package com.satoshilabs.trezor.ward.relay;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.protobuf.DescriptorProtos.DescriptorProto;
import com.google.protobuf.DescriptorProtos.EnumDescriptorProto;
import com.google.protobuf.DescriptorProtos.EnumValueDescriptorProto;
import com.google.protobuf.DescriptorProtos.FieldDescriptorProto;
import com.google.protobuf.DescriptorProtos.FieldDescriptorProto.Label;
import com.google.protobuf.DescriptorProtos.FieldDescriptorProto.Type;
import com.google.protobuf.DescriptorProtos.FileDescriptorProto;
import com.google.protobuf.Descriptors.Descriptor;
import com.google.protobuf.Descriptors.FileDescriptor;
import com.google.protobuf.DynamicMessage;
import org.junit.jupiter.api.Test;

/** The relay's JSON shape over a WardEntryAck-like message, descriptors built in code. */
class ProtobufJsonTest {
    private static final ObjectMapper JSON = new ObjectMapper();

    private static FieldDescriptorProto field(String name, int n, Type type, Label label, String typeName) {
        FieldDescriptorProto.Builder f = FieldDescriptorProto.newBuilder()
                .setName(name).setNumber(n).setType(type).setLabel(label);
        if (typeName != null) {
            f.setTypeName(typeName);
        }
        return f.build();
    }

    private static Descriptor ack() throws Exception {
        FileDescriptorProto file = FileDescriptorProto.newBuilder()
                .setName("ward-test.proto")
                .setPackage("t")
                .addEnumType(EnumDescriptorProto.newBuilder().setName("Code")
                        .addValue(EnumValueDescriptorProto.newBuilder().setName("Failure_DataError").setNumber(3)))
                .addMessageType(DescriptorProto.newBuilder().setName("Plain")
                        .addField(field("content", 1, Type.TYPE_BYTES, Label.LABEL_OPTIONAL, null)))
                .addMessageType(DescriptorProto.newBuilder().setName("Part")
                        .addField(field("encoding", 1, Type.TYPE_UINT32, Label.LABEL_OPTIONAL, null))
                        .addField(field("plaintext", 3, Type.TYPE_MESSAGE, Label.LABEL_OPTIONAL, ".t.Plain")))
                .addMessageType(DescriptorProto.newBuilder().setName("Ack")
                        .addField(field("content", 3, Type.TYPE_MESSAGE, Label.LABEL_OPTIONAL, ".t.Part"))
                        .addField(field("proof", 4, Type.TYPE_BYTES, Label.LABEL_REPEATED, null))
                        .addField(field("counter", 5, Type.TYPE_UINT32, Label.LABEL_OPTIONAL, null))
                        .addField(field("timestamp", 6, Type.TYPE_UINT64, Label.LABEL_OPTIONAL, null))
                        .addField(field("code", 7, Type.TYPE_ENUM, Label.LABEL_OPTIONAL, ".t.Code")))
                .build();
        return FileDescriptor.buildFrom(file, new FileDescriptor[0]).findMessageTypeByName("Ack");
    }

    @Test
    void roundTripsWithBytesAsHexEnumsByNameAndUnsignedIntegers() throws Exception {
        JsonNode body = JSON.readTree("{\"content\": {\"encoding\": 1, \"plaintext\": {\"content\": \"aabb\"}},"
                + " \"proof\": [\"00ff\", \"11\"], \"counter\": 4294967295,"
                + " \"timestamp\": 18446744073709551615, \"code\": \"Failure_DataError\"}");
        DynamicMessage message = ProtobufJson.fromJson(DynamicMessage.newBuilder(ack()), body).build();
        assertEquals(body, ProtobufJson.toJson(message));
        // and through the wire bytes, as a device reply would arrive
        DynamicMessage parsed = DynamicMessage.parseFrom(ack(), message.toByteArray());
        assertEquals(body, ProtobufJson.toJson(parsed));
    }

    @Test
    void absentFieldsAreOmittedAndBadInputRefused() throws Exception {
        assertEquals(JSON.readTree("{}"), ProtobufJson.toJson(DynamicMessage.getDefaultInstance(ack())));
        assertThrows(IllegalArgumentException.class,
                () -> ProtobufJson.fromJson(DynamicMessage.newBuilder(ack()), JSON.readTree("{\"nope\": 1}")));
        assertThrows(IllegalArgumentException.class,
                () -> ProtobufJson.fromJson(DynamicMessage.newBuilder(ack()), JSON.readTree("{\"proof\": [\"zz\"]}")));
        assertThrows(IllegalArgumentException.class,
                () -> ProtobufJson.fromJson(DynamicMessage.newBuilder(ack()), JSON.readTree("{\"code\": \"X\"}")));
    }
}
