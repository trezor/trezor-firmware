PYTHON=python3
UV=uv

EXCLUDES=.vscode
STYLE_TARGETS=src tests tools helper-scripts

dist: doc clean
	$(UV) build

doc:
	$(PYTHON) helper-scripts/make-options-rst.py

doc_check:
	$(PYTHON) helper-scripts/make-options-rst.py --check

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

git-clean:
	git clean -dfx -e $(EXCLUDES)

style:
	ruff check --fix $(STYLE_TARGETS)
	ruff format $(STYLE_TARGETS)
	flake8
	make pyright

style_check:
	ruff check $(STYLE_TARGETS)
	ruff format --check $(STYLE_TARGETS)
	flake8
	make pyright

style_quick_check:
	ruff format --check $(STYLE_TARGETS)
	ruff check --select I $(STYLE_TARGETS)

.PHONY: all build install clean doc doc_check style style_check git-clean clean-build clean-pyc clean-test

test:
	pytest tests

pyright:
	python ./../tools/pyright_tool.py
