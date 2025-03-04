#!/bin/sh

# Convert `-Z print-type-sizes` output into tab-separated values
sed -nr '/print-type-size/s/.*type: (`.*?`): ([0-9]+) bytes.* ([0-9]+) bytes/\2\t\3\t\1/p' $1
