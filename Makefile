lint: format

format:
	pdm run isort .
	pdm run black .

export:
	pdm export --prod -o requirements.txt

outdated:
	pdm update --dry-run --unconstrained

update:
	pdm update
	$(MAKE) --no-print-directory export

.PHONY: lint format export outdated
