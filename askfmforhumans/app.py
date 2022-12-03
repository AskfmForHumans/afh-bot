from __future__ import annotations

from dataclasses import field
import datetime
import logging
import sched
import time
from typing import Any, Callable, Optional

from askfmforhumans.api import AskfmApiError
from askfmforhumans.errors import AppError


class AppModuleBase:
    def __init__(self, info, *, config_factory=dict):
        self.mod_info = info
        self.logger = info.logger
        self.config = config_factory(info.config)

    def add_job(self, job):
        job.name = f"{self.mod_info.name}.{job.name}"
        self.mod_info.app.add_job(job)


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

    def init_config(self):
        pass

    def start(self):
        self._active = True
        self._instance = self._impl(self)


class AppJob:
    def __init__(self, name, func, *, priority=0):
        self.name = name
        self.func = func
        self.priority = priority

    def first_time(self):
        raise NotImplementedError

    def next_time(self):
        raise NotImplementedError


class IntervalJob(AppJob):
    def __init__(self, name, func, interval_sec, **kwargs):
        super().__init__(name, func, **kwargs)
        self.interval_sec = interval_sec

    def first_time(self):
        return 0  # meaning "run ASAP"

    def next_time(self):
        return time.time() + self.interval_sec


class DailyJob(AppJob):
    def __init__(self, name, func, utc_time: str, **kwargs):
        super().__init__(name, func, **kwargs)
        self.utc_time = utc_time
        if utc_time != "now":
            hour, _, minute = utc_time.partition(":")
            self.utc_time = datetime.time(
                int(hour), int(minute), tzinfo=datetime.timezone.utc
            )

    def first_time(self):
        return self.next_time()

    def next_time(self):
        now = datetime.datetime.now(datetime.timezone.utc)

        if self.utc_time == "now":
            self.utc_time = now.timetz()

        nt = datetime.datetime.combine(now, self.utc_time)
        if nt < now:
            nt += datetime.timedelta(days=1)
        return nt.timestamp()


class App:
    def __init__(self):
        self.modules = {}
        self.jobs = {}
        self.scheduler = sched.scheduler(timefunc=time.time)

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

    def init_config(self, config):
        self.init_module("_app", self, config)
        for name, mod in self.modules.items():
            self.init_module(name, mod, config)
            mod.app = self
            mod.init_config()

    def init_module(self, name, mod, config):
        config = config.get(name, {})
        mod.config = config
        mod._enabled = config.get("_enabled")
        mod.logger = logging.getLogger(f"afh.{name}")
        mod.logger.setLevel(config.get("_log_level", logging.NOTSET))

    def start_modules(self):
        for name, mod in self.modules.items():
            if mod._enabled is True:
                self.require_module(name)

    def add_job(self, job):
        if job.name in self.jobs:
            raise ValueError(f"job name {job.name!r} is already in use")
        self.jobs[job.name] = job
        self.schedule_job(job, first_time=True)

    def schedule_job(self, job, *, first_time):
        time = job.first_time() if first_time else job.next_time()
        self.scheduler.enterabs(time, job.priority, self.run_job, (job,))

    def run_job(self, job):
        self.logger.debug(f"starting job {job.name!r}")
        start = time.monotonic()
        try:
            job.func()
        except (AppError, AskfmApiError):
            self.logger.exception("run_job:")
        delta = time.monotonic() - start
        self.logger.debug(f"finished job in {delta:.2f}s")
        self.schedule_job(job, first_time=False)

    def run(self):
        self.scheduler.run()
        self.logger.warning("No more jobs to run. Stopping the app.")
