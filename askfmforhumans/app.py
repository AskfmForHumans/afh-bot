from __future__ import annotations

from dataclasses import field
import logging
import sched
import time
from typing import Any, Callable, Optional

from askfmforhumans.api import AskfmApiError
from askfmforhumans.errors import AppError


class AppModule:
    name: str
    config: dict[str, Any]
    logger: logging.Logger
    app: App
    _impl: Callable[[AppModule], Any]
    _instance: Any
    _active: bool = False
    _enabled: Optional[bool] = None

    def __init__(self, name, impl):
        self.name = name
        self._impl = impl

    def init_config(self, app, config):
        self.app = app
        self.config = config
        self._enabled = config.get("_enabled")

    def start(self):
        self._active = True
        self.logger = logging.getLogger(f"afh.{self.name}")
        self.logger.setLevel(self.config.get("_log_level", logging.NOTSET))
        self._instance = self._impl(self)

    def require_module(self, name):
        return self.app.require_module(name)

    def add_job(self, name, func, interval_sec):
        name = f"{self.name}.{name}"
        return self.app.add_job(name, func, interval_sec)


class App:
    def __init__(self):
        self.modules = {}
        self.jobs = {}
        self.scheduler = sched.scheduler()
        self.logger = logging.getLogger(f"afh.app")

    def use_module(self, module):
        if module.name in self.modules:
            raise ValueError(f"Module name {module.name!r} is already in use")
        self.modules[module.name] = module

    def require_module(self, name):
        if name not in self.modules:
            raise ValueError(f"Module {name!r} is missing")
        mod = self.modules[name]
        if mod._active:
            return mod._instance  # returns None for circular dependencies
        if mod._enabled is False:
            raise ValueError(f"Module {name!r} is disabled")
        self.logger.info(f"starting module {name!r}")
        mod.start()
        return mod._instance

    def add_job(self, name, func, interval_sec):
        if name in self.jobs:
            raise ValueError(f"job name {name!r} is already in use")
        self.jobs[name] = func, interval_sec
        self.scheduler.enter(0, 0, self.run_job, (name,))

    def init_config(self, config):
        app_cfg = config.get("_app", {})
        self.logger.setLevel(app_cfg.get("_log_level", logging.NOTSET))
        for name, mod in self.modules.items():
            mod.init_config(self, config.get(name, {}))

    def init_modules(self):
        for name, mod in self.modules.items():
            if mod._enabled is True:
                self.require_module(name)

    def run(self):
        self.scheduler.run()
        self.logger.warning("No jobs to run. Stopping the app.")

    def run_job(self, name):
        func, delay = self.jobs[name]
        self.logger.info(f"starting job {name!r}")
        start = time.monotonic()
        try:
            func()
        except (AppError, AskfmApiError):
            self.logger.exception("run_job:")
        delta = time.monotonic() - start
        self.logger.info(f"finished job in {delta:.2f}s")
        self.scheduler.enter(delay, 0, self.run_job, (name,))
