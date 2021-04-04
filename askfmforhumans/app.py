import logging
import os
import time

from askfm_api import AskfmApiError
from pymongo import MongoClient

from askfmforhumans.errors import AppError

MAIN_LOOP_SLEEP_SEC = 30


class App:
    def __init__(self):
        self.config = None
        self.db = None
        self.modules = {}
        self.active_modules = set()

        logging.basicConfig(level=logging.INFO)

    def use_module(self, name, cls, *, enabled_default=None):
        if name in self.modules:
            raise ValueError(f"Module name {name:r} is already in use")
        self.modules[name] = {
            "class": cls,
            "instance": None,
            "config": {"_enabled": enabled_default},
        }

    def require_module(self, name):
        if name in self.active_modules:
            # returns None for circular dependencies
            return self.modules[name]["instance"]
        if name not in self.modules:
            raise ValueError(f"Module {name:r} is missing")
        if self.modules[name]["config"]["_enabled"] is False:
            raise ValueError(f"Module {name:r} is disabled")
        self.active_modules.add(name)
        mod = self.modules[name]
        cfg = self.config.get(name, {})
        inst = mod["instance"] = mod["class"](self, cfg)
        return inst

    def start(self):
        self.init_db()
        self.init_config()
        self.start_modules()
        self.run_loop()

    def init_db(self):
        assert (
            "MONGODB_URL" in os.environ
        ), "Required env variable MONGODB_URL is missing"
        client = MongoClient(os.environ["MONGODB_URL"])
        self.db = client.get_default_database()

    def db_collection(self, name):
        return self.db.get_collection(name)

    def db_singleton(self, name):
        return self.db_collection("singletons").find_one({"_id": name})

    def init_config(self):
        cfg = self.config = self.db_singleton("config")
        for name, mod in self.modules.items():
            if name in cfg:
                mod["config"] |= cfg[name]

    def start_modules(self):
        for name, mod in self.modules.items():
            if mod["config"]["_enabled"] is True:
                self.require_module(name)

    def run_loop(self):
        while True:
            logging.info("Main loop: starting iteration")
            start = time.time()
            for name in self.active_modules:
                try:
                    self.modules[name]["instance"].tick()
                except (AppError, AskfmApiError):
                    logging.exception("Main loop:")
            delta = time.time() - start
            logging.info(f"Main loop: finished iteration in {delta:.2f}s")
            time.sleep(MAIN_LOOP_SLEEP_SEC)
