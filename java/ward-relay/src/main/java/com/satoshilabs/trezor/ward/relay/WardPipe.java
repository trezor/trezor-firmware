package com.satoshilabs.trezor.ward.relay;

/**
 * The frame pipe: put one named message on the device and hand back what it said.
 *
 * <p>RETURN PULLS AS-IS. {@code WardEntryRequest} and {@code WardChainRequest} are wardd's
 * conversation; a pipe that answered them itself would be answering wardd's question behind its
 * back. Handle only what the user is part of -- button requests, PIN, passphrase -- the way the
 * host always does.
 *
 * <p>Lark implements this on its Trezor session, mapping {@code name} to its own message-type id
 * (see {@link ProtobufJson} for the body).
 */
@FunctionalInterface
public interface WardPipe {
    DeviceMessage call(DeviceMessage request) throws PipeException;
}
