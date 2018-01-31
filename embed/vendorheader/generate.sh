BINCTL=../../tools/binctl
KEYCTL=../../tools/keyctl
BUILDVH=../../tools/build_vendorheader

# construct the default unsafe vendor header
$BUILDVH e28a8970753332bd72fef413e6b0b2ef1b4aadda7aa2c141f233712a6876b351:d4eec1869fb1b8a4e817516ad5a931557cb56805c3eb16e8f3a803d647df7869:772c8a442b7db06e166cfbc1ccbcbcde6f3eba76a4e98ef3ffc519502237d6ef 2 0.0 xxx...x "UNSAFE, DO NOT USE!" vendor_unsafe.toif vendorheader_unsafe_unsigned.bin

# sign the default unsafe vendor header using development keys
cp -a vendorheader_unsafe_unsigned.bin vendorheader_unsafe_signed_dev.bin
$BINCTL vendorheader_unsafe_signed_dev.bin -s 1:2 `$KEYCTL sign vendorheader vendorheader_unsafe_signed_dev.bin 4444444444444444444444444444444444444444444444444444444444444444 4545454545454545454545454545454545454545454545454545454545454545`

# construct SatoshiLabs vendor header
$BUILDVH 47fbdc84d8abef44fe6abde8f87b6ead821b7082ec63b9f7cc33dc53bf6c708d:9af22a52ab47a93091403612b3d6731a2dfef8a33383048ed7556a20e8b03c81:2218c25f8ba70c82eba8ed6a321df209c0a7643d014f33bf9317846f62923830 2 0.0 ....... SatoshiLabs vendor_satoshilabs.toif vendorheader_satoshilabs_unsigned.bin
