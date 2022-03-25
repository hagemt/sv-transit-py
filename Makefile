DIRS := modes tests

auto:
	@echo '--- This project uses poetry and Python v3.10+'
	@echo '* Try: `make test` (will install dependencies in venv)'
	@echo '(please open an issue or pull request if necessary)'
.PHONY: auto

clean:
	@git clean -dix
.PHONY: clean

lint: sane
	poetry run black $(DIRS)
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
	poetry run pytest
	make lint
.PHONY: test
