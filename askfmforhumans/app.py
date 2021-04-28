from dataclasses import field
import logging
import sched
import time
from typing import Any, Callable, Optional

from askfmforhumans.api import AskfmApiError
from askfmforhumans.errors import AppError
from askfmforhumans.util import MyDataclass


class AppModule(MyDataclass):
    factory: Callable
    active: bool = False
    enabled: Optional[bool] = None
    instance: Any = None
    config: dict = field(default_factory=dict)


class App:
    def __init__(self):
        self.modules = {}
        self.tasks = {}
        self.scheduler = sched.scheduler()

    def use_module(self, name, factory):
        if name in self.modules:
            raise ValueError(f"Module name {name!r} is already in use")
        self.modules[name] = AppModule(factory)

    def require_module(self, name):
        if name not in self.modules:
            raise ValueError(f"Module {name!r} is missing")
        mod = self.modules[name]
        if mod.active:
            return mod.instance  # returns None for circular dependencies
        if mod.enabled is False:
            raise ValueError(f"Module {name!r} is disabled")
        logging.info(f"App: starting module {name}")
        mod.active = True
        mod.instance = mod.factory(self, mod.config)
        return mod.instance

    def add_task(self, name, func, interval_sec):
        if name in self.tasks:
            raise ValueError(f"Task name {name!r} is already in use")
        self.tasks[name] = func, interval_sec
        self.scheduler.enter(0, 0, self.run_task, (name,))

    def init_config(self, config):
        for name, mod in self.modules.items():
            if name in config:
                mod.config |= config[name]
                mod.enabled = mod.config.get("_enabled")

    def init_modules(self):
        for name, mod in self.modules.items():
            if mod.enabled is True:
                self.require_module(name)

    def run(self):
        self.scheduler.run()
        logging.warning("No tasks to run. Stopping the app.")

    def run_task(self, name):
        func, delay = self.tasks[name]
        logging.info(f"App: starting task {name!r}")
        start = time.monotonic()
        try:
            func()
        except (AppError, AskfmApiError):
            logging.exception("run_task:")
        delta = time.monotonic() - start
        logging.info(f"App: finished task in {delta:.2f}s")
        self.scheduler.enter(delay, 0, self.run_task, (name,))
