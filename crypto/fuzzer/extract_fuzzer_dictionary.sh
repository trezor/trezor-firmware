#!/usr/bin/env bash

# usage: script.sh target-dictionary-filename

# this script searches for interesting strings in the source code and converts
# them into a standard fuzzer dictionary file.

TARGETFILE=${1:-fuzzer_crypto_tests_strings_dictionary1.txt}

# collect strings with normal words from the tests
grep -r -P -o -h  "\"[\w ]+\"" ../tests | sort  | uniq > $TARGETFILE

# collect BIP39 and SLIP39 words
grep -r -P -o -h "\"\w+\""  ../slip39_wordlist.h ../bip39_english.h | sort | uniq >> $TARGETFILE

# hex string to quoted escaped hex conversion
# TODO add an inverted output variant with swapped endian order?
grep -r -P -o -h  "([0-9a-fA-F][0-9a-fA-F])+" ../tests  | sort | uniq | \
while read -r line ; do
  # double escape since it is going to be used in bash
  escaped_hex=`echo $line | sed -e 's/../\\\\x&/g'`
  echo "\"$escaped_hex\"" >> $TARGETFILE
done

# search and reassemble BIP39 seed mnemonics that span multiple lines from the tests
# valid words are 3 to 10 characters long and there are 12, 18 or 24 words in a valid mnemonic
grep -r -P -o -h  "\"(\w{3,10} ?)+\",?" ../tests  | grep -vP "[0-9A-Z]" | tr '"\n' ' ' | \
sed 's/  / /g' | sed 's/  / /g'| grep -Po "(\w{3,10} ){11,23}(\w{3,10})" | sort | uniq | \
while read -r line ; do
  echo "\"$line\"" >> $TARGETFILE
done
