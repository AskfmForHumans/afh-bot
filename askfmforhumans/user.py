from collections import defaultdict
import logging

from askfmforhumans.ui_strings import user_settings_map
from askfmforhumans.util import MyDataclass


class UserProfile(MyDataclass):
    full_name: str
    bio: str
    hashtags: list[str]
    raw_settings: dict


class UserSettings(MyDataclass):
    stop: bool = False
    test: bool = False
    autoblock: bool = False
    delete_shoutouts: bool = True


class UserModel(MyDataclass):
    created_by: str = None
    ignored: bool = False
    greeted: bool = False
    device_id: str = None
    access_token: str = None
    password: str = None


class User:
    def __init__(self, uname, mgr):
        self.uname = uname
        self.mgr = mgr
        self.model = UserModel()
        self.settings = UserSettings()
        self.profile = None
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
        if cfg.test_mode and not self.settings.test:
            return False
        if self.settings.stop:
            return False
        return True

    def pre_sync(self):
        self.model.access_token = self.api.access_token

    def post_sync(self):
        api, model = self.api, self.model
        api.device_id = model.device_id or api.device_id
        api.auth = (self.uname, model.password) if model.password else None
        api.access_token = model.access_token or api.access_token
        if self.allowed:
            self.try_auth()

    def try_auth(self):
        api = self.api
        if not api.logged_in:
            if api.access_token:
                logging.info(f"User {self.uname}: has token, set logged_in = True")
                api.logged_in = True
            elif api.auth:
                logging.info(f"User {self.uname}: has auth, refreshing session")
                api.refresh_session()
            else:
                return False
        return True

    def set_model(self, model):
        self.model = UserModel.from_dict(model)

    def set_profile(self, profile):
        bio = profile["bio"].replace("\r\n", "\n")
        raw_settings = self.extract_settings(bio)
        profile = UserProfile(
            full_name=profile["fullName"],
            bio=bio,
            hashtags=profile["hashtags"],
            raw_settings=raw_settings,
        )
        if self.profile == profile:
            return

        self.profile = profile
        settings = UserSettings.from_dict(self.normalize_settings(raw_settings))
        self.settings = settings
        allowed = self.allowed
        logging.info(f"User {self.uname}: {allowed=} {settings=} {raw_settings=}")

    def extract_settings(self, bio):
        header = self.mgr.config.settings_header
        settings = defaultdict(list)
        bio = "\n" + bio
        lines = bio.partition(f"\n{header}\n")[2].splitlines()
        for line in lines:
            parts = line.partition("=")
            k, v = parts[0].strip(), parts[2].strip()
            settings[k].append(v)
        return dict(**settings)  # to avoid issues with e.g. printing

    def normalize_settings(self, raw_settings):
        schema = UserSettings.__annotations__
        settings = {}
        for k, v in raw_settings.items():
            k = user_settings_map.get(k, k)
            vtype = schema.get(k)
            if vtype is bool:
                v = v[-1]  # last seen wins
                v = user_settings_map.get(v, v or True)  # '' means True
                if isinstance(v, bool):
                    settings[k] = v
            # TBC
        return settings
