package com.satoshilabs.trezor.ward.relay;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.protobuf.ByteString;
import com.google.protobuf.Descriptors.EnumValueDescriptor;
import com.google.protobuf.Descriptors.FieldDescriptor;
import com.google.protobuf.Message;
import com.google.protobuf.MessageOrBuilder;
import java.math.BigInteger;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.Map;

/**
 * Protobuf messages to and from the relay's JSON -- bytes as lowercase hex, enums by name, absent
 * fields omitted: the shape {@code trezorlib.protobuf.to_dict} and Connect's codec produce.
 *
 * <p>NOT protobuf-java-util's {@code JsonFormat}, which writes bytes as base64 and field names in
 * camelCase; the relay uses the proto's own field names.
 *
 * <p>Works on any message with descriptors -- Lark's generated classes on a desktop JVM, or a
 * {@code DynamicMessage}. Needs full protobuf-java: protobuf-javalite carries no descriptors, so an
 * Android host maps its messages itself.
 */
public final class ProtobufJson {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final HexFormat HEX = HexFormat.of();
    private static final BigInteger TWO_64 = BigInteger.ONE.shiftLeft(64);

    private ProtobufJson() {}

    public static ObjectNode toJson(MessageOrBuilder message) {
        ObjectNode out = JSON.createObjectNode();
        for (FieldDescriptor field : message.getDescriptorForType().getFields()) {
            if (field.isRepeated()) {
                int n = message.getRepeatedFieldCount(field);
                if (n == 0) {
                    continue;
                }
                ArrayNode list = out.putArray(field.getName());
                for (int i = 0; i < n; i++) {
                    list.add(valueJson(field, message.getRepeatedField(field, i)));
                }
            } else if (message.hasField(field)) {
                out.set(field.getName(), valueJson(field, message.getField(field)));
            }
        }
        return out;
    }

    /** Fill {@code builder} from {@code json}; unknown field names and malformed values throw. */
    public static <B extends Message.Builder> B fromJson(B builder, JsonNode json) {
        if (!json.isObject()) {
            throw new IllegalArgumentException(builder.getDescriptorForType().getName() + " must be a JSON object");
        }
        Iterator<Map.Entry<String, JsonNode>> fields = json.fields();
        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            if (entry.getValue().isNull()) {
                continue;
            }
            FieldDescriptor field = builder.getDescriptorForType().findFieldByName(entry.getKey());
            if (field == null) {
                throw new IllegalArgumentException(
                        builder.getDescriptorForType().getName() + " has no field " + entry.getKey());
            }
            if (field.isRepeated()) {
                if (!entry.getValue().isArray()) {
                    throw new IllegalArgumentException(entry.getKey() + " must be a list");
                }
                for (JsonNode item : entry.getValue()) {
                    builder.addRepeatedField(field, valueProto(builder, field, item));
                }
            } else {
                builder.setField(field, valueProto(builder, field, entry.getValue()));
            }
        }
        return builder;
    }

    private static JsonNode valueJson(FieldDescriptor field, Object value) {
        switch (field.getJavaType()) {
            case INT:
                int i = (Integer) value;
                return number(isUnsigned(field) ? Integer.toUnsignedLong(i) : i);
            case LONG:
                long l = (Long) value;
                return isUnsigned(field) && l < 0
                        ? JSON.getNodeFactory().numberNode(BigInteger.valueOf(l).add(TWO_64))
                        : number(l);
            case FLOAT:
                return JSON.getNodeFactory().numberNode((Float) value);
            case DOUBLE:
                return JSON.getNodeFactory().numberNode((Double) value);
            case BOOLEAN:
                return JSON.getNodeFactory().booleanNode((Boolean) value);
            case STRING:
                return JSON.getNodeFactory().textNode((String) value);
            case BYTE_STRING:
                return JSON.getNodeFactory().textNode(HEX.formatHex(((ByteString) value).toByteArray()));
            case ENUM:
                return JSON.getNodeFactory().textNode(((EnumValueDescriptor) value).getName());
            case MESSAGE:
                return toJson((MessageOrBuilder) value);
            default:
                throw new IllegalStateException("unhandled field type " + field.getJavaType());
        }
    }

    /** The narrowest node, as Jackson's parser builds one: JSON that round-trips compares equal. */
    private static JsonNode number(long n) {
        return n == (int) n ? JSON.getNodeFactory().numberNode((int) n) : JSON.getNodeFactory().numberNode(n);
    }

    private static Object valueProto(Message.Builder builder, FieldDescriptor field, JsonNode v) {
        String bad = field.getName() + ": unexpected value " + v;
        switch (field.getJavaType()) {
            case INT:
                if (!v.canConvertToLong()) {
                    throw new IllegalArgumentException(bad);
                }
                return (int) v.asLong();
            case LONG:
                if (!v.isIntegralNumber()) {
                    throw new IllegalArgumentException(bad);
                }
                return v.bigIntegerValue().longValue();
            case FLOAT:
                return (float) v.asDouble();
            case DOUBLE:
                return v.asDouble();
            case BOOLEAN:
                if (!v.isBoolean()) {
                    throw new IllegalArgumentException(bad);
                }
                return v.asBoolean();
            case STRING:
                if (!v.isTextual()) {
                    throw new IllegalArgumentException(bad);
                }
                return v.asText();
            case BYTE_STRING:
                try {
                    return ByteString.copyFrom(HEX.parseHex(v.asText()));
                } catch (IllegalArgumentException e) {
                    throw new IllegalArgumentException(bad, e);
                }
            case ENUM:
                EnumValueDescriptor value = v.isTextual()
                        ? field.getEnumType().findValueByName(v.asText())
                        : field.getEnumType().findValueByNumber(v.asInt());
                if (value == null) {
                    throw new IllegalArgumentException(bad);
                }
                return value;
            case MESSAGE:
                return fromJson(builder.newBuilderForField(field), v).build();
            default:
                throw new IllegalStateException("unhandled field type " + field.getJavaType());
        }
    }

    private static boolean isUnsigned(FieldDescriptor field) {
        switch (field.getType()) {
            case UINT32:
            case UINT64:
            case FIXED32:
            case FIXED64:
                return true;
            default:
                return false;
        }
    }
}
