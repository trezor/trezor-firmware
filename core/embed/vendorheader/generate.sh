BUILDVH=../../tools/build_vendorheader
BINCTL=../../tools/headertool.py

# construct all vendor headers
for fn in *.json; do
    name=$(echo $fn | sed 's/vendor_\(.*\)\.json/\1/')
    $BUILDVH vendor_${name}.json vendor_${name}.toif vendorheader_${name}_unsigned.bin
done

# sign dev and QA vendor header
for name in unsafe qa_DO_NOT_SIGN; do
    cp -a vendorheader_${name}_unsigned.bin vendorheader_${name}_signed_dev.bin
    $BINCTL -D vendorheader_${name}_signed_dev.bin
done
