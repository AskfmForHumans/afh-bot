import logging
import os
import sched
import time

from askfm_api import AskfmApiError
from pymongo import MongoClient

from askfmforhumans.errors import AppError


class App:
    def __init__(self):
        self.config = None
        self.db = None
        self.modules = {}
        self.active_modules = set()
        self.tasks = {}
        self.scheduler = sched.scheduler()

        logging.basicConfig(level=logging.INFO)

    def use_module(self, name, cls, *, enabled_default=None):
        if name in self.modules:
            raise ValueError(f"Module name {name!r} is already in use")
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
            raise ValueError(f"Module {name!r} is missing")
        if self.modules[name]["config"]["_enabled"] is False:
            raise ValueError(f"Module {name!r} is disabled")
        self.active_modules.add(name)
        mod = self.modules[name]
        cfg = self.config.get(name, {})
        inst = mod["instance"] = mod["class"](self, cfg)
        return inst

    def add_task(self, name, func, interval_sec):
        if name in self.tasks:
            raise ValueError(f"Task name {name!r} is already in use")
        self.tasks[name] = func, interval_sec
        self.scheduler.enter(0, 0, self.run_task, (name,))

    def start(self):
        self.init_db()
        self.init_config()
        self.start_modules()
        self.scheduler.run()

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

    def run_task(self, name):
        func, delay = self.tasks[name]
        logging.info(f"Starting task {name!r}")
        start = time.monotonic()
        try:
            func()
        except (AppError, AskfmApiError):
            logging.exception("run_task:")
        delta = time.monotonic() - start
        logging.info(f"Finished task in {delta:.2f}s")
        self.scheduler.enter(delay, 0, self.run_task, (name,))
