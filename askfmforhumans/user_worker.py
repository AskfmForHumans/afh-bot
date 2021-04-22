import logging
import time

from askfmforhumans import ui_strings
from askfmforhumans.api import requests as r
from askfmforhumans.util import MyDataclass

SEC_IN_DAY = 60 * 60 * 24
SEC_IN_YEAR = SEC_IN_DAY * 365


class UserWorkerConfig(MyDataclass):
    cleaning_interval: int = 30
    rescuing_interval: int = SEC_IN_DAY


class UserWorker:
    MOD_NAME = "user_worker"

    def __init__(self, app, config):
        self.app = app
        self.config = UserWorkerConfig.from_dict(config)
        self.umgr = app.require_module("user_manager")
        app.add_task(
            f"{self.MOD_NAME}:cleaning",
            self.cleaning_task,
            self.config.cleaning_interval,
        )
        app.add_task(
            f"{self.MOD_NAME}:rescuing",
            self.rescuing_task,
            self.config.rescuing_interval,
        )

    def cleaning_task(self):
        for user in self.umgr.users.values():
            if user.active and user.settings.delete_shoutouts:
                self.delete_shoutouts(user)

    def rescuing_task(self):
        for user in self.umgr.users.values():
            if user.active and user.settings.rescuing:
                self.rescue_questions(user)

    def delete_shoutouts(self, user):
        for q in user.api.fetch_new_questions():
            if q["type"] in ("shoutout", "anonshoutout"):
                qtype, qid, qtext = q["type"], q["qid"], q["body"]
                qfrom = " from " + q["author"] if q["author"] else ""
                # Logging shoutout bodies is ok since they aren't private by definition
                logging.info(f"Got {qtype}:{qid} for {user.uname}{qfrom}: {qtext}")

                if user.settings.autoblock:
                    logging.info(f"Deleting {qid} and blocking its author")
                    user.api.request(r.report_question(qid, should_block=True))
                else:
                    logging.info(f"Deleting {qid}")
                    user.api.request(r.delete_question(qtype, qid))

        user.api.request(r.mark_notifs_as_read("SHOUTOUT"))

    def rescue_questions(self, user):
        for q in user.api.request_iter(r.fetch_questions()):
            qid, qtype, qts = q["qid"], q["type"], q["updatedAt"]
            # threads are more complex, ignore them for now
            if qtype != "thread" and time.time() - qts > SEC_IN_YEAR:
                qts = time.asctime(time.gmtime(qts))
                logging.info(
                    f"Rescuing {qtype}:{qid} for {user.uname} updated at {qts}"
                )
                user.api.request(r.post_answer(qtype, qid, ui_strings.rescuing_answer))
                user.api.request(r.delete_answer(qid))
