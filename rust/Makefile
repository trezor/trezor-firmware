# trezor-client needs running emulator for test, handled in core.yml
CRATES_TEST = trezor-thp trezor-tjpgdec
CRATES = ${CRATES_TEST} trezor-client

check: clippy test

style:
	@for D in $(CRATES); do ( \
		echo "[STYLE $$D]"; \
		cd $$D; \
		cargo fmt \
	); done

style_check:
	@for D in $(CRATES); do ( \
		echo "[STYLE_CHECK $$D]"; \
		cd $$D; \
		cargo fmt -- --check \
	); done

clippy:
	@for D in $(CRATES); do ( \
		echo "[CLIPPY $$D]"; \
		cd $$D; \
		cargo clippy \
	); done

test:
	@for D in $(CRATES_TEST); do ( \
		echo "[TEST $$D]"; \
		cd $$D; \
		cargo test \
	); done
