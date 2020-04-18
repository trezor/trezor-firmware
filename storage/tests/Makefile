.PHONY: tests

build:
	$(MAKE) -C c
	$(MAKE) -C c0

## tests commands:
tests:
	pytest --junitxml=../../tests/junit.xml -k "not hypothesis"

tests_all:
	pytest --junitxml=../../tests/junit.xml
