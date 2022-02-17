test:
	[ -x "$(shell command -v poetry)" ]
	poetry install
	poetry run pytest
.PHONY: test
