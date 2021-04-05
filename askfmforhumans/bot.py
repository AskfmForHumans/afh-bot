import logging

from askfm_api import requests as r

from askfmforhumans import messages
from askfmforhumans.util import prepare_config


class Bot:
    MOD_NAME = "bot"
    CONFIG_SCHEMA = {
        # "..." means the field has no default and is therefore required
        "username": ...,
        "password": ...,
        "search_by_hashtag": True,
        "greet_users": True,
        "tick_interval_sec": 30,
    }

    def __init__(self, app, config):
        self.app = app
        self.config = prepare_config(
            config, self.CONFIG_SCHEMA, schema_name=self.MOD_NAME
        )
        self.user_manager = app.require_module("user_manager")
        app.add_task(self.MOD_NAME, self.tick, self.config["tick_interval_sec"])

        self.api = self.user_manager.create_api()
        self.api.login(self.config["username"], self.config["password"])

    def tick(self):
        if self.config["search_by_hashtag"]:
            self.discover_users()
        if self.config["greet_users"]:
            self.greet_users()

    def discover_users(self):
        for user in self.api.request_iter(
            r.search_users_by_hashtag(self.user_manager.config["hashtag"])
        ):
            self.user_manager.user_discovered(user["uid"])

    def greet_users(self):
        for uname, user in self.user_manager.users.items():
            if (
                user.active
                and not user.model.get("greeted")
                and user.model.get("created_by") == "discovery_hashtag"
            ):
                logging.info(f"Greeting {uname}")
                self.api.request(
                    r.send_question(
                        uname,
                        messages.greet_user.format(full_name=user.profile["fullName"]),
                    )
                )
                self.user_manager.update_user_model(uname, {"greeted": True})
