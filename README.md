# AskfmForHumans

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Project manager: pdm](https://img.shields.io/badge/project%20manager-pdm-blue.svg)](https://github.com/frostming/pdm)

Multifunctional bot intended to mend some of [ASKfm](https://ask.fm)'s screwups.

## Features

- automatic user discovery
  - find people with the configured hashtag
  - send them an inviting question
- user settings
  - stored in the user's profile bio in the form `key=value` under a configured header
  - the `stop` setting temporarily disables all interaction with the user
- remove all shoutouts for logged-in users
  - use the `autoblock` setting to block the authors of all shoutouts
- *simple* mode that requires no account for bot and only performs user-related tasks
- special *safe* modes for testing

## Usage

This code is ready to run on Heroku. Just click a button:  
[![Deploy to Heroku button](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AskfmForHumans/afh-bot/tree/production)

It also uses a MongoDB instance (you can get one for free on https://www.mongodb.com/cloud).
> What a pity that there's no free Heroku addon for a NoSQL DB :cry:.

### Config

Basic config is described in [.env.example](.env.example).
More config will be documented later.

### Real-world usage experience

See this [issue](https://github.com/AskfmForHumans/afh-bot/issues/3).

## Todo & Roadmap

There is a GitHub [project](https://github.com/orgs/AskfmForHumans/projects/1).
