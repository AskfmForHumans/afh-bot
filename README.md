# AskfmForHumans

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Project manager: pdm](https://img.shields.io/badge/project%20manager-pdm-blue.svg)](https://github.com/frostming/pdm)

### Features

- automatic user discovery
  - find people with the configured hashtag
  - send them an inviting question
- user settings
  - stored in the user's hashtags in the form `#<`*`hashtag_prefix`*`><`*`setting_name`*`>[9<`*`value`*`>]`
  - RSA-encrypted password is split into 3 parts (ASKfm's hashtag length limit is 50 characters)
- remove all shoutouts for logged-in users
  - use the `stop` setting to disable
- special *safe* modes for testing

### Config

Documented in [.env.example](.env.example).

## Todo

### In-progress
- Fix `fetch_new_questions()`
- Extract logging & stats to a dedicated module (EventManager?)

### Docs
- Add roadmap to the bot's profile?
- Discuss encryption & config in issues

### Features
- Stats in profile description & logs
- Status command
- Cleaning modes: continuous, daily, on-demand
- Question filter
- Old (~1 year) question refreshing

### Other
- Migrate from hashtags to user description for storing settings?
- Lazy string formatting in log messages?
- Remove stale users?
- Retry failed operations with backoff?
