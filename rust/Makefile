# trezor-client needs running emulator for test, handled in core.yml
CRATES_TEST = trezor-thp trezor-tjpgdec trezor-ward
CRATES = ${CRATES_TEST} trezor-client
# crates that have to work in WebAssembly too
CRATES_WASM = trezor-ward

.PHONY: check audit

check: clippy test audit

style:
	@for D in $(CRATES); do ( \
		echo "[STYLE $$D]"; \
		cd $$D; \
		cargo fmt \
	); done

style_check:
	@set -e; for D in $(CRATES); do ( \
		echo "[STYLE_CHECK $$D]"; \
		cd $$D; \
		cargo fmt -- --check \
	); done

clippy:
	@set -e; for D in $(CRATES); do ( \
		echo "[CLIPPY $$D]"; \
		cd $$D; \
		cargo clippy \
	); done

test:
	@set -e; for D in $(CRATES_TEST); do ( \
		echo "[TEST $$D]"; \
		cd $$D; \
		cargo test \
	); done

# Needs the wasm shell (`nix-shell --arg wasm true`), so it is not part of `check`.
# The tests run on wasm32-wasip1 under wasmtime. A panic aborts in WebAssembly and takes
# the captured output with it: --nocapture keeps the message of a failing test. Doctests
# are left to the host run.
# For wasm32-unknown-unknown, which a browser loads and which has no way to report a
# result, the tests are compiled and linked but not run.
test_wasm:
	@set -e; for D in $(CRATES_WASM); do ( \
		echo "[TEST_WASM $$D]"; \
		cd $$D; \
		CARGO_TARGET_WASM32_WASIP1_RUNNER=wasmtime \
			cargo test --target wasm32-wasip1 --lib --tests -- --nocapture; \
		cargo test --target wasm32-unknown-unknown --no-run \
	); done

audit:
	@set -e; for D in $(CRATES); do ( \
		echo "[AUDIT $$D]"; \
		cd $$D; \
		cargo audit --deny warnings \
	); done
