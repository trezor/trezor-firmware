# reset sanitizer and optimization flags to avoid interfering with $CFLAGS
export SANFLAGS=""
export OPTFLAGS="-O3 -march=native -gline-tables-only"
FUZZER=1 VALGRIND=0 make -j$(nproc) fuzzer
mv fuzzer/fuzzer $OUT/
