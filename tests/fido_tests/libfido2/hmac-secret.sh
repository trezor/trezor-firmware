DEVICE=$(fido2-token -L | cut -d : -f 1)

if [ -z "$DEVICE" ] ; then
  echo "No FIDO2 token found"
  exit 1
fi

# taken from https://github.com/Yubico/libfido2/issues/58

echo credential challenge | openssl sha256 -binary | base64 > cred_param
echo relying party >> cred_param
echo user name >> cred_param
dd if=/dev/urandom bs=1 count=32 | base64 >> cred_param
fido2-cred -M -h -i cred_param "$DEVICE" | fido2-cred -V -h -o cred

# taken from https://github.com/Yubico/libfido2/issues/58

echo assertion challenge | openssl sha256 -binary | base64 > assert_param
echo relying party >> assert_param
head -1 cred >> assert_param
tail -n +2 cred > pubkey
dd if=/dev/urandom bs=1 count=64 | base64 -w0 >> assert_param  # hmac salt
fido2-assert -G -h -i assert_param "$DEVICE" > hmac_assert
fido2-assert -V -h -i hmac_assert pubkey es256
tail -1 hmac_assert | base64 -d | xxd  # hmac secret
