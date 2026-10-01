package com.satoshilabs.trezor.ward.relay;

/**
 * Why a pipe could not produce the device's reply: the device answered {@code Failure} (part of the
 * conversation), or the pipe itself broke. Either way wardd is told with a {@code Failure}, so the
 * conversation ends and the wallet is released rather than waited on.
 */
public class PipeException extends Exception {
    private static final long serialVersionUID = 1L;

    private final boolean failure;
    private final String code;

    private PipeException(String message, boolean failure, String code) {
        super(message);
        this.failure = failure;
        this.code = code;
    }

    /** The device answered {@code Failure} with this code (may be null) and message. */
    public static PipeException failure(String code, String message) {
        return new PipeException(message, true, code);
    }

    /** The pipe broke: transport, encoding, a device that went away. */
    public static PipeException broken(String message) {
        return new PipeException(message, false, null);
    }

    public boolean isDeviceFailure() {
        return failure;
    }

    public String code() {
        return code;
    }
}
