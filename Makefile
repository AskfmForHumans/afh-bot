pre-commit: format export

format:
	pdm run isort .
	pdm run black .

export:
	pdm export --prod -o requirements.txt
	pdm export --prod -o deta/requirements.txt --without-hashes

release: release-deta release-heroku

release-deta:
	[ -z "$$(git status --porcelain=v1)" ] || { echo "Unclean git worktree!"; exit 1; }
	
	git checkout deta
	git restore -SWs main .

	cp -f deta/* .
	git add .
	git rm -rfq --ignore-unmatch heroku deta
	git commit -m "New release"

release-heroku:
	[ -z "$$(git status --porcelain=v1)" ] || { echo "Unclean git worktree!"; exit 1; }
	
	git checkout heroku
	git restore -SWs main .

	cp -f heroku/* .
	git add .
	git rm -rfq --ignore-unmatch heroku deta
	git commit -m "New release"

.PHONY: pre-commit format export release release-deta release-heroku
