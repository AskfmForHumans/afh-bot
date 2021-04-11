import logging

from askfm_api import AskfmApiError
from askfm_api import requests as r

from askfmforhumans.ui_strings import user_settings_map
from askfmforhumans.util import MyDataclass


class UserSettings(MyDataclass):
    stop: bool = False
    test: bool = False
    autoblock: bool = False


class UserModel(MyDataclass):
    created_by: str = None
    greeted: bool = False
    device_id: str = None
    access_token: str = None
    password: str = None


class UserWorker:
    def __init__(self, uname, mgr):
        self.uname = uname
        self.mgr = mgr
        self.model = UserModel()
        self.settings = UserSettings()
        self.api = mgr.create_api(auto_refresh_session=False)
        self.profile = None
        self.active = False

    def update_model(self, model):
        model = UserModel.from_dict(model)
        if self.model != model:
            logging.info(f"User {self.uname} {model=}")
        self.model = model
        self.check_active()

    def update_profile(self, profile):
        self.profile = profile
        settings = UserSettings.from_dict(self.extract_settings(profile))
        if self.settings != settings:
            logging.info(f"User {self.uname} {settings=}")
        self.settings = settings
        self.check_active()

    def extract_settings(self, profile):
        header = self.mgr.config.settings_header
        settings = {}
        bio = "\n" + profile["bio"].replace("\r\n", "\n")
        lines = bio.partition(f"\n{header}\n")[2].split("\n")
        for line in lines:
            parts = line.partition("=")
            k, v = parts[0].strip(), parts[2].strip()
            if k:
                k = user_settings_map.get(k, k)
                v = v or True
                settings[k] = v
        return settings

    def check_active(self):
        active = self.is_active()
        if self.active != active:
            logging.info(f"User {self.uname} {active=}")
        self.active = active

    def is_active(self):
        cfg = self.mgr.config

        if not self.profile:
            return False
        if cfg.require_hashtag and cfg.hashtag not in self.profile["hashtags"]:
            return False
        if cfg.test_mode and not self.settings.test:
            return False
        if self.settings.stop:
            return False
        return True

    def tick(self):
        self.update_auth()
        if self.api.logged_in:
            try:
                self.process_questions()
            except AskfmApiError:
                self.save_auth()
                raise
            else:
                self.save_auth()

    def update_auth(self):
        api, model = self.api, self.model
        api.device_id = model.device_id or api.device_id
        api.auth = (self.uname, model.password) if model.password else None
        api.access_token = model.access_token or api.access_token

        if not api.logged_in:
            if api.access_token:
                api.logged_in = True
            elif api.auth:
                api.refresh_session()

    def save_auth(self):
        if self.api.access_token != self.model.access_token:
            self.mgr.update_user(self.uname, {"access_token": self.api.access_token})

    def process_questions(self):
        for q in self.api.fetch_new_questions():
            if q["type"] in ("shoutout", "anonshoutout"):
                qtype, qid, qtext = q["type"], q["qid"], q["body"]
                qfrom = " from " + q["author"] if q["author"] else ""
                # Logging shoutout bodies is ok since they aren't private by definition
                logging.info(f"Got {qtype} {qid} for {self.uname}{qfrom}: {qtext}")

                if self.settings.autoblock:
                    logging.info(f"Deleting {qid} and blocking its author")
                    self.api.request(r.report_question(qid, should_block=True))
                else:
                    logging.info(f"Deleting {qid}")
                    self.api.request(r.delete_question(qtype, qid))

        self.api.request(r.mark_notifs_as_read("SHOUTOUT"))
