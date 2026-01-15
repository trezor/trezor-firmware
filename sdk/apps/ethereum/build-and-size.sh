cargo build --release --target thumbv7em-none-eabihf
cargo size --release --target thumbv7em-none-eabihf --bin ethereum_rust -- -A
cargo size --release --target thumbv7em-none-eabihf --bin ethereum_rust -- -B
# cargo readobj --release --target thumbv7em-none-eabihf --bin ethereum_rust -- -C -sW

# NM_OUT="$(mktemp)"
# cargo nm --release --target thumbv7em-none-eabihf --bin ethereum_rust -- --size-sort --print-size | tee "$NM_OUT"
# python3 ./tools/group_nm.py < "$NM_OUT"
# rm -f "$NM_OUT"
