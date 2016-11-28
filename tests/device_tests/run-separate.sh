#!/bin/bash
for i in test_*.py; do
  echo Starting: $i
  python $i > $i.out 2> $i.err
done
