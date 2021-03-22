import logging

from askfm_api import AskfmApiError
from askfm_api import requests as r


class User:
    def __init__(self, uname, app):
        self.uname = uname
        self.app = app
        self.api = None
        self.settings = {}
        self.active = False

    def update_profile(self, profile):
        header = self.app.cfg["user_settings_header"]
        new_settings = {}
        bio = "\n" + profile["bio"].replace("\r\n", "\n")
        lines = bio.partition(f"\n{header}\n")[2].split("\n")
        for line in lines:
            parts = line.partition("=")
            k, v = parts[0].strip(), parts[2].strip()
            if k:
                new_settings[k] = v
        if self.settings != new_settings:
            logging.info(f"User {self.uname} settings={new_settings}")
        self.settings = new_settings

        new_active = (
            self.app.cfg["hashtag"] in profile["hashtags"]
            and not (self.app.test_users_mode and "test" not in self.settings)
            and "stop" not in self.settings
        )
        if self.active != new_active:
            logging.info(f"User {self.uname} active={new_active}")
        self.active = new_active

    def tick(self):
        if self.api is not None and self.active:
            self.process_questions()

    def process_questions(self):
        for q in self.api.fetch_new_questions():
            if q["type"] in ("shoutout", "anonshoutout"):
                qtype, qid, qtext = q["type"], q["qid"], q["body"]
                qfrom = " from " + q["author"] if q["author"] else ""
                # Logging shoutout bodies is ok since they aren't private by definition
                logging.info(f"Got {qtype} {qid} for {self.uname}{qfrom}: {qtext}")

                if "autoblock" in self.settings:
                    logging.info(f"Deleting {qid} and blocking its author")
                    self.api.request(r.report_question(qid, should_block=True))
                else:
                    logging.info(f"Deleting {qid}")
                    self.api.request(r.delete_question(qtype, qid))

        self.api.request(r.mark_notifs_as_read("SHOUTOUT"))

    def try_login(self, token):
        try:
            self.api = self.app.create_user_api(token)
            logging.info(f"Logged in as {self.uname}")
            return True
        except AskfmApiError as e:
            logging.warning(f"Failed logging in as {self.uname}: {e}")
            return False
