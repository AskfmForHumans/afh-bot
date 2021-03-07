import logging

from askfm_api import AskfmApiError
from askfm_api import requests as r

from askfmforhumans.errors import AppError, CryptoError


class User:
    def __init__(self, uname, app):
        self.uname = uname
        self.app = app
        self.api = None
        self.raw_hashtags = []
        self.settings = {}
        self.active = False

    def update_profile(self, profile):
        self.raw_hashtags = profile["hashtags"]

        matches = map(self.app.setting_regex.fullmatch, profile["hashtags"])
        self.settings = {m.group(1): m.group(2) for m in matches if m}
        logging.debug(f"Parsed settings for {self.uname}: {self.settings}")

        new_active = (
            self.app.cfg["hashtag"] in self.raw_hashtags
            and not (self.app.test_users_mode and "test" not in self.settings)
            and "stop" not in self.settings
        )
        if self.active != new_active:
            logging.info(f"User {self.uname} active={new_active}")
        self.active = new_active

        if self.active and self.api is None:
            self.try_read_password()

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

    def try_read_password(self):
        # TODO warn user about failed attempts?
        if not (
            "p09" in self.settings and "p19" in self.settings and "p29" in self.settings
        ):
            return False

        passwd = self.settings["p09"] + self.settings["p19"] + self.settings["p29"]
        logging.info(f"Trying to log in as {self.uname} (found passwd={passwd})")

        try:
            passwd = self.app.decrypt_password(passwd)
        except CryptoError as e:
            logging.warning(f"Login failed: {repr(e)}")
            return False

        return self.try_login(passwd)

    def try_write_password(self, passwd):
        if not self.try_login(passwd):
            return False

        try:
            passwd = self.app.encrypt_password(passwd)
        except CryptoError as e:
            logging.warning(e)
            return False

        logging.info(f"Writing encrypted password {passwd} for {self.uname}")
        groups = passwd[0:43], passwd[43:86], passwd[86:]
        for i, pw in enumerate(groups):
            self.save_setting(f"p{i}9", pw)
        return True

    def try_login(self, passwd):
        try:
            self.api = self.app.create_user_api(self.uname, passwd)
            logging.info(f"Logged in as {self.uname}")
            return True
        except AskfmApiError as e:
            logging.warning(f"Failed logging in as {self.uname}: {e}")
            return False

    def save_setting(self, tag, value="", *, delete_existing=True):
        tag_start = self.app.cfg["hashtag_prefix"] + tag
        tag_full = tag_start + value

        if delete_existing:
            found = False
            for t in self.raw_hashtags:
                if t == tag_full:
                    found = True
                elif t.startswith(tag_start):
                    logging.warning(f"Deleting hashtag {t} for {self.uname})")
                    self.api.request(r.delete_hashtag(t))
            if found:
                return

        logging.info(f"Setting hashtag {tag_full} for {self.uname}")
        tag_added = self.api.request(r.add_hashtag(tag_full))["name"]

        if not self.app.safe_mode and tag_added != tag_full:
            raise AppError(f"Failed to add hashtag: mutated {tag_full} -> {tag_added}")

        self.settings[tag] = value
