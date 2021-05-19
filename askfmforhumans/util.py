import dataclasses
import inspect
from typing import Any


class AppModuleBase:
    def __init__(self, info, *, config_factory=dict, use_events=True):
        self.mod_info = info
        self.logger = info.logger
        self.config = config_factory(info.config)
        if use_events:
            self.event_mgr = info.app.require_module("event_mgr")
        else:
            self.event_mgr = None

    def add_job(self, job):
        job.name = f"{self.mod_info.name}.{job.name}"
        self.mod_info.app.add_job(job)

    def event(self):
        if not self.event_mgr:
            raise NotImplementedError
        return self.event_mgr.event(self.mod_info.name)


class MyDataclass:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        dataclasses.dataclass(cls)

    @classmethod
    def from_dict(
        cls,
        src: dict[str, Any],
        /,
        *,
        allow_extra: bool = True,
        raise_errors: bool = True,
    ):
        schema = inspect.signature(cls).parameters
        schema_name = cls.__name__

        # check extra keys
        if not allow_extra:
            for key in src:
                if key in schema:
                    continue
                elif raise_errors:
                    raise AssertionError(
                        f"Key {key!r} not allowed in schema {schema_name!r}"
                    )
                else:
                    return None

        # check required keys
        res = {}
        for key, param in schema.items():
            if key in src:
                res[key] = src[key]
            elif param.default is not inspect.Parameter.empty:
                continue
            elif raise_errors:
                raise AssertionError(f"Key {key!r} required in schema {schema_name!r}")
            else:
                return None

        return cls(**res)

    def as_dict(self):
        return dataclasses.asdict(self)
