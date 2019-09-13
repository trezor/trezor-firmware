#!/usr/bin/env bash
find ../mocks -name '*.py' | sort | while read module; do
    module=$(echo $module | sed 's:^\.\./mocks/::')
    base=$(basename $module)
    # skip __init__.py
    if [[ $base == "__init__.py" ]]; then
        continue
    fi
    # skip everything outside of trezor
    if [[ $module != trezor* ]]; then
        continue
    fi
    # skip classes (uppercase modules)
    if [[ $base == [ABCDEFGHIJKLMNOPQRSTUVWXYZ]* ]]; then
        continue
    fi
    module=$(echo $module | sed -e 's:\.py$::' -e 's:/:.:g')

    if [ -r test_$module.py ]; then
        echo "OK   $module"
    else
        echo "MISS $module"
        missing=$(expr $missing + 1)
    fi

done
