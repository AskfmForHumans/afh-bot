import logging

from askfmforhumans.ui_strings import user_settings_map
from askfmforhumans.util import MyDataclass


class UserSettings(MyDataclass):
    stop: bool = False
    test: bool = False
    autoblock: bool = False


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
        if cfg.require_hashtag and cfg.hashtag not in self.profile["hashtags"]:
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
        self.profile = profile
        settings = UserSettings.from_dict(self.extract_settings(profile))
        if self.settings != settings:
            self.settings = settings
            logging.info(f"User {self.uname} {settings=} {self.allowed=}")

    def extract_settings(self, profile):
        header = self.mgr.config.settings_header
        settings = {}
        bio = "\n" + profile["bio"].replace("\r\n", "\n")
        lines = bio.partition(f"\n{header}\n")[2].splitlines()
        for line in lines:
            parts = line.partition("=")
            k, v = parts[0].strip(), parts[2].strip()
            if k:
                k = user_settings_map.get(k, k)
                v = v or True
                settings[k] = v
        return settings
