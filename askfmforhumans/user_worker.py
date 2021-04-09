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
    ignore: bool = False
    access_token: str = None
    greeted: bool = False


class UserWorker:
    def __init__(self, uname, mgr):
        self.uname = uname
        self.mgr = mgr
        self.model = UserModel()
        self.settings = UserSettings()
        self.api = None
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
        if not self.profile:
            return False
        if self.model.ignore:
            return False
        if (
            self.mgr.config.require_hashtag
            and self.mgr.config.hashtag not in self.profile["hashtags"]
        ):
            return False
        if self.mgr.config.test_mode and not self.settings.test:
            return False
        if self.settings.stop:
            return False
        return True

    def tick(self):
        if self.api is None and self.model.access_token:
            self.try_login(self.model.access_token)
        if self.api is not None:
            self.process_questions()

    def try_login(self, token):
        try:
            self.api = self.mgr.create_api(token)
            logging.info(f"Logged in as {self.uname}")
            return True
        except AskfmApiError as e:
            logging.warning(f"Failed logging in as {self.uname}: {e}")
            return False

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
