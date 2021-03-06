# AskfmForHumans

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Project manager: pdm](https://img.shields.io/badge/project%20manager-pdm-blue.svg)](https://github.com/frostming/pdm)

Multifunctional bot intended to mend some of [ASKfm](https://ask.fm)'s screwups.

## Features

- automatic user discovery
  - find people with the configured hashtag
  - send them an inviting question
- user settings
  - stored in the user's hashtags in the form `#`*`<hashtag_prefix><setting_name>`*`[9`*`<value>`*`]`
  - RSA-encrypted password is split into 3 parts (ASKfm's hashtag length limit is 50 characters)
- remove all shoutouts for logged-in users
  - use the `stop` setting to disable
- *simple* mode that requires no account for bot and only performs user-related tasks
- special *safe* modes for testing

## Usage

This code is ready to run on Heroku. Just click a button:  
[![Deploy to Heroku button](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AskfmForHumans/afh-bot/tree/production)

### Config

Documented in [.env.example](.env.example).

### Real-world usage experience

I've been running this code for ~1 week with 3-4 active users before the bot's account was blocked by ASKfm without any warning.
Don't know if it's because it asks users for their passwords or for other reasons.

## Todo

### FIXME
- Fix `fetch_new_questions()`
- Detect failed auth, retry with backoff or give up

### Docs
-

### Features
- Stats in profile description & logs (updated hourly?)
- Status command (for user to verify their settings)
- Cleaning modes: continuous, daily, on-demand
- Inbox filter (remove questions with specific words)
- Old (~1 year) question refreshing (answer and immediately delete)

### Implementation
- Resolve [#1](https://github.com/AskfmForHumans/afh-bot/issues/1) & [#2](https://github.com/AskfmForHumans/afh-bot/issues/2)
- Improve config validation
- Extract logging & stats to a dedicated module (EventManager?)
- Lazy string formatting in log messages?
- Remove stale users?
