from dataclasses import field
from enum import Enum

from askfmforhumans.models import UserProfile
from askfmforhumans.ui_strings import user_settings_map
from askfmforhumans.util import MyDataclass


class UserModel(MyDataclass):
    created_by: str = None
    ignored: bool = False
    greeted: bool = False
    device_id: str = None
    access_token: str = None
    password: str = None


class FilterSchedule(Enum):
    ON_DEMAND = 1
    DAILY = 2
    CONTINUOUS = 3


class UserSettings(MyDataclass):
    stop: bool = False
    rescue: bool = True
    delete_after: int = 0
    filters_str: list[str] = field(default_factory=list)
    filters_re: list[str] = field(default_factory=list)
    read_shoutouts: bool = True
    filter_shoutouts: bool = True
    filter_block_authors: bool = False
    filter_anon_only: bool = False
    filter_schedule: FilterSchedule = FilterSchedule.DAILY

    @staticmethod
    def from_raw(raw, /):
        schema = UserSettings.__annotations__
        res = UserSettings()
        for k, v in raw:
            k = k.lower()
            k = user_settings_map.get(k, k)
            vtype = schema.get(k)
            if vtype is bool:
                v = v.lower()
                v = user_settings_map.get(v, v or True)  # '' means True
                if isinstance(v, bool):
                    setattr(res, k, v)
            elif vtype is int:
                if v.isascii() and v.isdigit():
                    setattr(res, k, int(v))
            elif vtype == list[str]:
                if v:
                    getattr(res, k).append(v)
            elif isinstance(vtype, type) and issubclass(vtype, Enum):
                v = v.lower()
                v = user_settings_map.get(v, v)
                if v in vtype.__members__:
                    setattr(res, k, vtype[v])
        return res


class User:
    def __init__(self, uname, mgr):
        self.uname = uname
        self.mgr = mgr
        self.model = UserModel()
        self.settings = UserSettings()
        self.profile = None
        self.raw_settings = None
        self.api = mgr.api_manager.create_api(auto_refresh_session=False)

    @property
    def active(self):
        return self.allowed and self.api.logged_in

    @property
    def allowed(self):
        cfg = self.mgr.config
        if self.model.ignored:
            return False
        if not self.profile:
            return False
        if cfg.require_hashtag and cfg.hashtag not in self.profile.hashtags:
            return False
        if self.settings.stop:
            return False
        return True

    def pre_sync(self):
        self.model.access_token = self.api.access_token

    def try_auth(self):
        api = self.api
        if not api.logged_in:
            if api.access_token:
                self.mgr.logger.info(
                    f"User {self.uname}: has token, set logged_in = True"
                )
                api.logged_in = True
            elif api.auth:
                self.mgr.logger.info(f"User {self.uname}: has auth, refreshing session")
                api.refresh_session()
            else:
                return False
        return True

    def set_model(self, model):
        model = self.model = UserModel.from_dict(model)
        api = self.api
        api.device_id = model.device_id or api.device_id
        api.auth = (self.uname, model.password) if model.password else None
        api.access_token = model.access_token or api.access_token

    def set_profile(self, profile):
        old_allowed = self.allowed
        self.profile = UserProfile.from_api_obj(profile)
        raw_settings = self.extract_settings(self.profile.bio)
        if self.raw_settings != raw_settings:
            self.raw_settings = raw_settings
            self.settings = settings = UserSettings.from_raw(raw_settings)
            self.mgr.logger.info(f"User {self.uname}: {settings=} {raw_settings=}")
        allowed = self.allowed
        if allowed != old_allowed:
            self.mgr.logger.info(f"User {self.uname}: {allowed=}")

    def extract_settings(self, bio):
        header = self.mgr.config.settings_header
        bio = "\n" + bio
        lines = bio.partition(f"\n{header}\n")[2].splitlines()
        parts = [l.partition("=") for l in lines if l]
        return [(p[0].strip(), p[2].strip()) for p in parts]
