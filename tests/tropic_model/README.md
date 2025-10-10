This directory contains files needed to launch the "Tropic model" - [ts-tvl](https://github.com/tropicsquare/ts-tvl/) - which is used to simulate the presence of the TROPIC01 chip during tests.

The Tropic model requires:
 * (I) a keypair and a certificate it will use to communicate to the host (`tropic01_ese_*`) - these are simply copied from [example_config](https://github.com/tropicsquare/ts-tvl/tree/master/model_configs/example_config)
 * (II) a certificate chain and a keypair that will be used during Trezor's authenticity check

The root key, certificate chain and keypair are generated using these commands:

```
# generate root keypair
openssl genpkey -algorithm Ed25519 -out root_key.pem
openssl pkey -in root_key.pem -pubout -out root_pubkey.pem

# see the root pubkey - to be used in test
openssl pkey -in root_pubkey.pem -pubin -outform DER | tail -c 32 | xxd -p -c 256

# generate root certificate (signed by the root key)
openssl req -new -x509 -key root_key.pem -out root_cert.pem -days 36500

# generate device key pair
openssl genpkey -algorithm Ed25519 -out tropic_key.pem
openssl pkey -in tropic_key.pem -pubout -out tropic_pubkey.pem

# generate certificate signing request
openssl req -new -key tropic_key.pem -out tropic.csr -subj "/CN=T3W1"

# use the signing request to generate a device certificate signed by the authority
openssl x509 -req -in tropic.csr -CA root_cert.pem -CAkey root_key.pem -CAcreateserial -out tropic_cert.pem -days 36500
```

`ts-tvl` then uses a YAML config file to load the above keys and certificates.
 * (I) go into: `s_t_priv`, `s_t_pub` and `x509_certificate` as required by [`ts-tvl`](https://github.com/tropicsquare/ts-tvl/blob/master/model_configs/example_config/example_config.yml)
 * (II) go into: `r_ecc_keys` and `r_user_data` as required by [Trezor's authenticity check](https://github.com/trezor/trezor-firmware/blob/main/core/src/apps/management/authenticate_device.py)

The config file itself is generated using `core/tools/generate_tropic_model_config.py`.
