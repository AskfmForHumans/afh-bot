from __future__ import annotations

from dataclasses import field
import datetime
import logging
import sched
import time
from typing import Any, Callable, Optional

from askfmforhumans.api import AskfmApiError
from askfmforhumans.errors import AppError


class AppModuleInfo:
    name: str
    config: dict[str, Any]
    logger: logging.Logger
    app: App
    _impl: Callable[[AppModuleInfo], Any]
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


class AppJob:
    def __init__(self, name, func):
        self.name = name
        self.func = func

    def first_time(self):
        raise NotImplementedError

    def next_time(self):
        raise NotImplementedError


class IntervalJob(AppJob):
    def __init__(self, name, func, interval_sec):
        super().__init__(name, func)
        self.interval_sec = interval_sec

    def first_time(self):
        return 0  # meaning "run ASAP"

    def next_time(self):
        return time.time() + self.interval_sec


class DailyJob(AppJob):
    def __init__(self, name, func, utc_time: str):
        super().__init__(name, func)
        hour, _, minute = utc_time.partition(":")
        self.utc_time = datetime.time(int(hour), int(minute))

    def first_time(self):
        return self.next_time()

    def next_time(self):
        now = datetime.datetime.utcnow()
        nt = datetime.datetime.combine(now, self.utc_time)
        if nt <= now:
            nt += datetime.timedelta(days=1)
        return nt.replace(tzinfo=datetime.timezone.utc).timestamp()


class App:
    def __init__(self):
        self.modules = {}
        self.jobs = {}
        self.scheduler = sched.scheduler(timefunc=time.time)
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

    def add_job(self, job):
        if job.name in self.jobs:
            raise ValueError(f"job name {job.name!r} is already in use")
        self.jobs[job.name] = job
        self.scheduler.enterabs(job.first_time(), 0, self.run_job, (job,))

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

    def run_job(self, job):
        self.logger.debug(f"starting job {job.name!r}")
        start = time.monotonic()
        try:
            job.func()
        except (AppError, AskfmApiError):
            self.logger.exception("run_job:")
        delta = time.monotonic() - start
        self.logger.debug(f"finished job in {delta:.2f}s")
        self.scheduler.enterabs(job.next_time(), 0, self.run_job, (job,))
