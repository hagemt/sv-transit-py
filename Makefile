ARGS :=
DIRS := modes scripts tests
TEST := bart.cli caltrain.cli

auto:
	@echo '--- This project uses poetry and modern Python 3+ tooling'
	@echo '* Try: `make test` (will install dependencies in venv)'
	@echo '(please open an issue or pull request if necessary)'
.PHONY: auto

bart:
	@poetry run python modes/bart.py $(ARGS) $(BART_ARGS)
.PHONY: bart

check: sane
	make fmt
	poetry run bandit -r modes
	poetry run mypy --check-untyped-defs $(DIRS)
	poetry run pylint $(DIRS)
	make test
.PHONY: check

clean:
	@git clean -dix
.PHONY: clean

fmt:
	poetry run black $(DIRS)
	poetry run isort $(DIRS)
.PHONY: fmt

sane:
	poetry install
	poetry show --outdated
.PHONY: sane

test:
	env "TRANSIT_TESTS=$(TEST)" poetry run pytest -rs
.PHONY: test
