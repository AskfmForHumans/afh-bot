# AskfmForHumans

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pdm-managed](https://img.shields.io/badge/pdm-managed-blueviolet)](https://pdm.fming.dev)

Multifunctional bot intended to mend some of [ASKfm](https://ask.fm)'s screwups.

## Features

- automatic user discovery (just for fun, huh)
  - find people with the configured hashtag
  - send them an inviting question
- question filtering
  - delete/mark-as-read all shoutouts
  - text/regex filtering
  - old question cleaning
  - optionally block authors of deleted questions
- "rescue" old (one year) questions subject to automatic removal
- user settings
  - stored in the user's profile bio in the form `key=value` under a configured header
  - the `stop` setting temporarily disables all interaction with the user
  - many other settings that affect filtering behavior
- `api_manager.dry_mode`: perform only `GET` requests to the ASKfm API (useful for testing)
- l10n: currently only hard-coded Russian

There's a more complete [guide in Russian](https://afh.snowwm.ml/bot/).

## Usage

For a minimal setup, you just need to clone the repo, run `pip install -r requirements.txt`, write a config file and start the app with `AFH_CONFIG_FILE=config.toml python -m askfmforhumans`.

### Config file

One way of providing configuration is via a TOML file.
The program reads the path to this file from the environment variable `AFH_CONFIG_FILE`.
Here's an example config:

```toml
[api_mgr]
signing_key = "8648...C417"

[user_mgr]
hashtag = "askfmforhumans"
settings_header = "=AskfmForHumans="

[user_mgr.users]
ask4humans = {password = "12345"}

[user_worker]
_enabled = true
_log_level = "DEBUG"

[bot]
_enabled = true
username = "ask4humans"
greet_users = true
```

Each section (known in TOML as *table*) defines settings for a different app module. You can find modules and their config schemas in the source files (start with the list of all modules in [\_\_init__.py](askfmforhumans/__init__.py)).

The app will start every module that has `_enabled = true` in the config along with all its dependencies.

### Database

A simple read-only config file may be sufficient for testing and simple one-user deploys, but not for long-term deploys serving many users.
Fortunately, the program can use MongoDB to store user data and config.
Connection info is read from the environment variable `AFH_DB_URL` which looks like `mongodb://user:pass@example.com/db-name`.

App configuration is stored as JSON in the database table `singletons` in the document with `_id` = `"config"`. Note that it won't get loaded if you also pass a config file path via `AFH_CONFIG_FILE` (though the database may still be used to store user information). An example config document is provided in this repo: [example-config.json](example-config.json).

You can get a cloud MongoDB instance for free on https://www.mongodb.com/cloud (there's a web UI and VS Code plugin for editing data).

### Cloud hosting

This bot is ready to run on [Deta](https://www.deta.sh/) (a nice cloud platform **free for everyone**)
or [Heroku](https://www.heroku.com/home) (used to be free, but no more). Create a database, prepare the config and then click one of the buttons and fill in your database access URL (of course, you will need to have an account on the hosting platform too). If you plan to deploy the app to these platforms manually, you may want to explore specific pre-configured branches in this repository.

[![Deploy to Deta](https://button.deta.dev/1/svg)](https://go.deta.dev/deploy?repo=https://github.com/AskfmForHumans/afh-bot/tree/deta)

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AskfmForHumans/afh-bot/tree/heroku)

### Real-world usage experience

See this [issue](https://github.com/AskfmForHumans/afh-bot/issues/3).

## Todo / Roadmap

There is a GitHub [project](https://github.com/orgs/AskfmForHumans/projects/1).
