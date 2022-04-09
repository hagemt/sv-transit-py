ARGS :=
DIRS := modes scripts tests
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

HTML ?= tests/test_caltrain_html.py
html: install
	@poetry run python $(HTML)
	@poetry run pytest $(HTML)
	@env "TRANSIT_TESTS=$(TEST)" poetry run \
		pytest -ra --cov=modes --cov-report=html tests/
.PHONY: html

install:
	@#[ -x "$(shell command -v poetry)" ] ## brew install poetry ### nodejs yarn
	poetry install
.PHONY: install

lights:
	@poetry run python -m lights
.PHONY: lights

lint: sane
	poetry run bandit -r modes
	poetry run black $(DIRS)
	poetry run mypy $(DIRS)
	-poetry run pylint $(DIRS)
.PHONY: lint

sane: install
	poetry show --outdated
	#[ -x "$(shell command -v snyk)" ] && snyk # yarn global add snyk # optional
.PHONY: sane

services:
	make -C ui node_modules
	docker-compose up -d
.PHONY: services

stop:
	docker-compose down
.PHONY: stop

test: install
	env "TRANSIT_TESTS=$(TEST)" poetry run pytest -ra --cov=modes tests/
	make lint
.PHONY: test
