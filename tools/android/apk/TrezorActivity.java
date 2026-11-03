package io.trezor.emulator;

import android.os.Bundle;
import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;
import java.io.File;
import java.io.FileDescriptor;
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
            // Device tests need animations disabled, like emu.py --headless.
            if (getIntent().getBooleanExtra("disable_animation", false)) {
                Os.setenv("TREZOR_DISABLE_ANIMATION", "1", true);
            }
            // An app's native output is discarded, so keep the firmware's log.
            FileDescriptor log = Os.open(
                    new File(getFilesDir(), "firmware.log").getPath(),
                    OsConstants.O_WRONLY | OsConstants.O_CREAT | OsConstants.O_TRUNC,
                    0600);
            Os.dup2(log, 1);
            Os.dup2(log, 2);
            Os.close(log);
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
