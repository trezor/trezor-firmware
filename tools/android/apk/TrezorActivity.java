package io.trezor.emulator;

import android.os.Bundle;
import android.system.ErrnoException;
import android.system.Os;
import org.libsdl.app.SDLActivity;

/** Runs the emulator firmware from libmain.so in an SDL window. */
public class TrezorActivity extends SDLActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // The firmware reads its configuration from the environment, before
        // SDLActivity starts it on its own thread.
        int port = getIntent().getIntExtra("port", 31344);
        try {
            Os.setenv("TREZOR_PROFILE_DIR", getFilesDir().getPath(), true);
            Os.setenv("TREZOR_PROFILE_NAME", "android", true);
            Os.setenv("TREZOR_UDP_PORT", Integer.toString(port), true);
        } catch (ErrnoException e) {
            throw new RuntimeException(e);
        }
        super.onCreate(savedInstanceState);
    }

    @Override
    protected void main() {
        super.main();
        // The firmware's state is static, so a restart needs a new process.
        System.exit(0);
    }

    @Override
    protected String[] getLibraries() {
        return new String[] {"SDL3", "SDL3_image", "main"};
    }
}
