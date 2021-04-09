import logging

from askfm_api import requests as r

from askfmforhumans import messages
from askfmforhumans.util import MyDataclass


class BotConfig(MyDataclass):
    username: str
    password: str
    search_by_hashtag: bool = True
    greet_users: bool = True
    tick_interval_sec: int = 30


class Bot:
    MOD_NAME = "bot"

    def __init__(self, app, config):
        self.app = app
        self.config = BotConfig.from_dict(config)
        self.user_manager = app.require_module("user_manager")
        app.add_task(self.MOD_NAME, self.tick, self.config.tick_interval_sec)

        self.api = self.user_manager.create_api()
        self.api.login(self.config.username, self.config.password)

    def tick(self):
        if self.config.search_by_hashtag:
            self.discover_users()
        if self.config.greet_users:
            self.greet_users()

    def discover_users(self):
        for user in self.api.request_iter(
            r.search_users_by_hashtag(self.user_manager.config.hashtag)
        ):
            self.user_manager.user_discovered(user["uid"])

    def greet_users(self):
        for uname, user in self.user_manager.users.items():
            if (
                user.active
                and not user.model.greeted
                and user.model.created_by == "discovery_hashtag"
            ):
                logging.info(f"Greeting {uname}")
                self.api.request(
                    r.send_question(
                        uname,
                        messages.greet_user.format(full_name=user.profile["fullName"]),
                    )
                )
                self.user_manager.update_user_model(uname, {"greeted": True})
