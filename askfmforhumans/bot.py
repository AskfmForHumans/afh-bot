import logging

from askfmforhumans import ui_strings
from askfmforhumans.api import requests as r
from askfmforhumans.errors import AppError
from askfmforhumans.util import MyDataclass

CREATED_BY = "discovery_hashtag"


class BotConfig(MyDataclass):
    username: str
    password: str = None
    search_by_hashtag: bool = True
    greet_users: bool = True
    tick_interval_sec: int = 30


class Bot:
    MOD_NAME = "bot"

    def __init__(self, app, config):
        self.app = app
        self.config = BotConfig.from_dict(config)
        self.umgr = app.require_module("user_manager")
        app.add_task(self.MOD_NAME, self.tick, self.config.tick_interval_sec)

        self.user = self.umgr.get_or_create_user(
            self.config.username, password=self.config.password
        )
        self.api = self.user.api

    def tick(self):
        if not self.user.try_auth():
            raise AppError("Bot can't log in")
        if self.config.search_by_hashtag:
            self.discover_users()

    def discover_users(self):
        for user in self.api.request_iter(
            r.search_users_by_hashtag(self.umgr.config.hashtag)
        ):
            uname = user["uid"]
            if uname not in self.umgr.users:
                user = self.umgr.get_or_create_user(uname, created_by=CREATED_BY)
                if self.config.greet_users and user.allowed:
                    self.greet_user(user)

    def greet_user(self, user):
        uname = user.uname
        logging.info(f"Greeting {uname}")
        self.api.request(
            r.send_question(
                uname,
                ui_strings.greet_user.format(full_name=user.profile["fullName"]),
            )
        )
        user.model.greeted = True
