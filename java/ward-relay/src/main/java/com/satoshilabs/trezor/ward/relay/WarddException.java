package com.satoshilabs.trezor.ward.relay;

/**
 * wardd refused, or could not be reached. {@link #code()} is the contract's error code
 * ({@code wm_conflict}, {@code needs_rejoin}, ...) or one of {@code unreachable}, {@code closed},
 * {@code timeout}, {@code protocol} for the connection itself.
 */
public class WarddException extends Exception {
    private static final long serialVersionUID = 1L;

    private final String code;

    public WarddException(String code, String message) {
        super(code + ": " + message);
        this.code = code;
    }

    public WarddException(String code, String message, Throwable cause) {
        super(code + ": " + message, cause);
        this.code = code;
    }

    public String code() {
        return code;
    }
}
