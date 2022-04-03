ARGS :=
DIRS := modes tests
TEST := bart.cli caltrain.cli

auto:
	@echo '--- This project uses poetry and Python v3.10+'
	@echo '* Try: `make test` (will install dependencies in venv)'
	@echo '(please open an issue or pull request if necessary)'
.PHONY: auto

bart:
	@poetry run python modes/bart.py $(ARGS) $(BART_ARGS)
.PHONY: bart

calt:
	@poetry run python modes/caltrain.py $(ARGS) $(CALT_ARGS)
.PHONY: calt

clean:
	@git clean -dix
.PHONY: clean

lint: sane
	poetry run bandit -r modes
	poetry run black $(DIRS)
	poetry run mypy $(DIRS)
	poetry run pylint $(DIRS)
.PHONY: lint

sane:
	@#[ -x "$(shell command -v poetry)" ] ## brew install poetry ### nodejs yarn
	poetry install
	poetry show --outdated
	#[ -x "$(shell command -v snyk)" ] && snyk # yarn global add snyk # optional
.PHONY: sane

test: sane
	poetry install
	env "TRANSIT_TESTS=$(TEST)" poetry run pytest -rs
	make lint
.PHONY: test
