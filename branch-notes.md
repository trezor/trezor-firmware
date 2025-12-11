This branch contains an experiment intended to accelerate the SLH-DSA algorithm
(the library located in /vendor/sphincsplus) using the hardware hash peripheral
on STM32. This is not production code, but it is a fully functional experiment.

To reproduce the test:

1) Modify the sphincsplus library to use the hardware-accelerated SHA-256 implementation:

```sh
cd vendor/sphincsplus
git checkout 129b72c80e122a22a61f71b5d2b042770890ccee
git apply ../../sphincsplus.patch
```

2) Build `prodtest` for T3W1:

```sh
make build_prodtest TREZOR_MODEL=T3W1 BOOTLOADER_DEVEL=1
```
3) Upload `prodtest` to the T3W1.

4) In `prodtest`, run the new command:

`test-slhdsa`

Expected output:

```
# crypto_sign_secretkeybytes() -> 64
# crypto_sign_publickeybytes() -> 32
# crypto_sign_bytes() -> 7856
# crypto_sign_seedbytes() -> 48
# Signing message using SLHDSA...
# Signed in 19.657 s
# SHA256 performance counters:
#   init calls:           5
#   inc blocks calls:     3
#   inc blocks processed: 3
#   finalize calls:       2186238
#   finalize bytes:       86001540
# Verifying signature using SLHDSA...
# Verified in 0.20 s
# SHA256 performance counters:
#   init calls:           3
#   inc blocks calls:     2
#   inc blocks processed: 2
#   finalize calls:       2100
#   finalize bytes:       87522
# Signature verification result: OK
OK
```

----------------------------------------------------------

To disable hardware acceleration, undefine the symbol `XSHA256_ACCELERATION` in
`/vendor/sphincsplus/ref/params.h`.

The result above was obtained with stack protector disabled. To enable stack
protection, open `SConscript.prodtest` and search for `stack-protector`.

-------------------------------------------------

The new `xsha_xxx()` functions were originally designed to store the SHA peripheral
context and allow multiple SHA computations to run in parallel.

Ultimately, this was not required (based on how the sphincsplus library uses the
SHA interface - see below). Consequently, support for saving and restoring the
hardware context was disabled. It can be re-enabled by setting
`XSHA256_CONTEXT_SAVING` to `1`.

--------------------------------------------------------------

The sphincsplus library uses xsha256 according to the following pattern:

```c
xhsa_init(&ctx)
xsha_update(&ctx, .., 64) // it always calls the function with 1 block (64 bytes)
memcpy(&saved_ctx, &ctx, sizeof(*ctx))
```

Then the saved context is reused many times (approximately 2.3 million):

```c
memcpy(&local_ctx, &save_ctx, sizeof(*ctx))
xsha_final(&ctx, ..., n) // where n < 64
```c

-----------------------------------------------------------

The STM32 HASH peripheral context is approximately 160 bytes. Saving and
restoring such a large context is relatively expensive. In this experiment,
it turned out to be significantly slower than recomputing the first block every
time sphincsplus calls `xsha_final()`.

It appears that the current signing time of roughly 20 seconds is not the lower
bound. Additional improvements are possible, but they would require modifications
to the sphincsplus library itself - for example, avoiding context copying
and instead referencing the first block directly.



