.PHONY: tests

build:
	$(MAKE) -C c
	$(MAKE) -C c0

## tests commands:
tests:
	pytest -k "not hypothesis"

tests_all:
	pytest
