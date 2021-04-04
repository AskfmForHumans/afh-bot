# AskfmForHumans

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Project manager: pdm](https://img.shields.io/badge/project%20manager-pdm-blue.svg)](https://github.com/frostming/pdm)

Multifunctional bot intended to mend some of [ASKfm](https://ask.fm)'s screwups.

## Features

- automatic user discovery (just for fun, huh)
  - find people with the configured hashtag
  - send them an inviting question
- user settings
  - stored in the user's profile bio in the form `key=value` under a configured header
  - currently the app understands setting keys in Russian, though I use English here for consistency
  - the `stop` setting temporarily disables all interaction with the user
- remove all shoutouts for logged-in users
  - use the `autoblock` setting to block the authors of all shoutouts
- special modes for testing
  - `dry_mode`: perform only `GET` requests to the ASKfm API
  - `test_mode`: interact only with users with a `test` setting

## Usage

This code is ready to run on Heroku. Just click a button:  
[![Deploy to Heroku button](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AskfmForHumans/afh-bot/tree/production)

It also uses a MongoDB instance (you can get one for free on https://www.mongodb.com/cloud).
> What a pity that there's no free Heroku addon for a decent NoSQL DB :cry:.

### Config

The app needs one environment variable `MONGODB_URL` which looks like `mongodb+srv://user:pass@example.com/db-name`.
Further configuration is stored in the database table `singletons` in the document with `_id` = `"config"`.

### Real-world usage experience

See this [issue](https://github.com/AskfmForHumans/afh-bot/issues/3).

## Todo / Roadmap

There is a GitHub [project](https://github.com/orgs/AskfmForHumans/projects/1).
