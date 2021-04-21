lint: format

format:
	pdm run isort .
	pdm run black .

export:
	pdm export --prod -o requirements.txt

.PHONY: lint format export
