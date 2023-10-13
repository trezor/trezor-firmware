include(FetchContent)

FetchContent_Declare(
    Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.4 # Optionally specify a commit hash, version tag or branch here
)

FetchContent_MakeAvailable(Corrosion)

corrosion_import_crate(
    MANIFEST_PATH Cargo.toml 
    NO_DEFAULT_FEATURES 
    FEATURES model_tt ui bootloader bitcoin_only touch micropython protobuf model_tt dma2d
    FLAGS -Z build-std=core -Z build-std-features=panic_immediate_abort
)

# input", "rgb_led", "consumption_mask", "usb", "optiga"