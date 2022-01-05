.PHONY: tests

export ASAN_OPTIONS=verify_asan_link_order=0

build:
	$(MAKE) -C c
	$(MAKE) -C c0

clean:
	$(MAKE) -C c clean
	$(MAKE) -C c0 clean

## tests commands:
tests:
	pytest --junitxml=../../tests/junit.xml -k "not hypothesis"

tests_all:
	pytest --junitxml=../../tests/junit.xml
