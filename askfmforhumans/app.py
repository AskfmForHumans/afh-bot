import json
import logging
import os
import time

from askfm_api import AskfmApiError
from pymongo import MongoClient

from askfmforhumans.api import ExtendedApi
from askfmforhumans.bot import Bot
from askfmforhumans.errors import AppError
from askfmforhumans.simple_bot import SimpleBot

MAIN_LOOP_SLEEP_SEC = 30


class App:
    def __init__(self):
        self.db = None
        self.cfg = {}
        self.api_key = None
        self.safe_mode = False
        self.test_users_mode = False

        loglevel = logging.DEBUG if "DEBUG" in os.environ else logging.INFO
        logging.basicConfig(level=loglevel)

        self.init_db()
        self.init_config()

    def init_db(self):
        assert (
            "MONGODB_URL" in os.environ
        ), "Required env variable MONGODB_URL is missing"
        client = MongoClient(os.environ["MONGODB_URL"])
        self.db = client.get_default_database()

    def init_config(self):
        assert (
            "ASKFM_API_KEY" in os.environ
        ), "Required env variable ASKFM_API_KEY is missing"
        self.api_key = os.environ["ASKFM_API_KEY"]

        self.cfg = self.db.config.find_one()

        test_mode = self.cfg.get("test_mode", "off")
        if test_mode == "safe":
            self.safe_mode = True
            logging.warning("Running in safe mode")
        elif test_mode == "test-users":
            self.test_users_mode = True
            logging.warning("Running in test-users mode")
        else:
            assert test_mode == "off", f"Invalid test_mode: {test_mode}"

    def run(self):
        self.bot = SimpleBot(self) if self.cfg["bot_type"] == "simple" else Bot(self)

        while True:
            logging.info("Main loop: starting iteration")
            start = time.time()

            try:
                self.bot.tick()
                # self.update_stats()
            except (AppError, AskfmApiError):
                logging.exception("Main loop:")

            delta = time.time() - start
            logging.info(f"Main loop: finished iteration in {delta:.2f}s")
            time.sleep(MAIN_LOOP_SLEEP_SEC)

    def create_bot_api(self, *, login=True):
        token = self.cfg.get("access_token")
        api = ExtendedApi(self.api_key, access_token=token, safe_mode=self.safe_mode)
        if token is None and login:
            api.login(self.cfg["bot_username"], self.cfg["bot_password"])
        return api

    def create_user_api(self, token):
        return ExtendedApi(self.api_key, access_token=token, safe_mode=self.safe_mode)
