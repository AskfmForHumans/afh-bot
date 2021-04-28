# AskfmForHumans

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Project manager: pdm](https://img.shields.io/badge/project%20manager-pdm-blue.svg)](https://github.com/frostming/pdm)

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
- special modes for testing
  - `api_manager.dry_mode`: perform only `GET` requests to the ASKfm API
  - `user_manager.test_mode`: interact only with users with the `test` setting in profile
- l10n: currently only hard-coded Russian

## Usage

This code is ready to run on Heroku. Just click a button:  
[![Deploy to Heroku button](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AskfmForHumans/afh-bot/tree/production)

### Config file

One way of providing configuration is via a TOML file.
The program reads the path to this file from the environment variable `AFH_CONFIG_FILE`.
Here's an example config:

```toml
[api_manager]
signing_key = "8648...C417"

[user_manager]
test_mode = true
hashtag = "askfmforhumans"
settings_header = "=AskfmForHumans="

[user_manager.users]
ask4humans = {password = "12345"}

[user_worker]
_enabled = true

[bot]
_enabled = true
username = "ask4humans"
```

Config for each application module lives in a separate sub-object. You can find modules and their config schemas in the source files (start with the list of all modules in [\_\_main__.py](askfmforhumans/__main__.py)).

The app will start every module that has `_enabled = true` in the config and all its dependencies.

### Database

A simple read-only config file may be sufficient for testing and simple one-user deploys, but not for long-term deploys serving many users.
Fortunately, the program can use MongoDB to store user data and config.
Connection info is read from the environment variable `AFH_DB_URL` which looks like `mongodb://user:pass@example.com/db-name`.

App configuration is stored as JSON in the database table `singletons` in the document with `_id` = `"config"`. Note that it won't get loaded if you also pass a config file path via `AFH_CONFIG_FILE`.

You can get a cloud MongoDB instance for free on https://www.mongodb.com/cloud (there's a web UI and VS Code plugin for editing data).
> What a pity that there's no free Heroku addon for a decent NoSQL DB :cry:.

### Real-world usage experience

See this [issue](https://github.com/AskfmForHumans/afh-bot/issues/3).

## Todo / Roadmap

There is a GitHub [project](https://github.com/orgs/AskfmForHumans/projects/1).
