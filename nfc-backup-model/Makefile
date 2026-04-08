SOURCES = $(wildcard *.py)

all: style_check test

style:
	black --target-version py313 $(SOURCES)
	isort $(SOURCES)

style_check:
	black --target-version py313 --check $(SOURCES)
	isort --check $(SOURCES)
	flake8 $(SOURCES)
	mypy $(SOURCES)

test:
	pytest
