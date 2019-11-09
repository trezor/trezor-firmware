DEVICE=$(fido2-token -L | cut -d : -f 1)

if [ -z "$DEVICE" ] ; then
  echo "No FIDO2 token found"
  exit 1
fi

# taken from fido2-cred manpage

echo credential challenge | openssl sha256 -binary | base64 > cred_param
echo relying party >> cred_param
echo user name >> cred_param
dd if=/dev/urandom bs=1 count=32 | base64 >> cred_param
fido2-cred -M -i cred_param "$DEVICE" | fido2-cred -V -o cred

# taken from fido2-assert manpage

echo assertion challenge | openssl sha256 -binary | base64 > assert_param
echo relying party >> assert_param
head -1 cred >> assert_param
tail -n +2 cred > pubkey
fido2-assert -G -i assert_param "$DEVICE" | fido2-assert -V pubkey es256
