import logging

from askfmforhumans.api import requests as r
from askfmforhumans.util import MyDataclass


class UserWorkerConfig(MyDataclass):
    tick_interval_sec: int = 30


class UserWorker:
    MOD_NAME = "user_worker"

    def __init__(self, app, config):
        self.app = app
        self.config = UserWorkerConfig.from_dict(config)
        self.umgr = app.require_module("user_manager")
        app.add_task(
            "delete_shoutouts", self.shoutout_task, self.config.tick_interval_sec
        )

    def shoutout_task(self):
        for user in self.umgr.users.values():
            if user.active and user.settings.delete_shoutouts:
                self.delete_shoutouts(user)

    def delete_shoutouts(self, user):
        for q in user.api.fetch_new_questions():
            if q["type"] in ("shoutout", "anonshoutout"):
                qtype, qid, qtext = q["type"], q["qid"], q["body"]
                qfrom = " from " + q["author"] if q["author"] else ""
                # Logging shoutout bodies is ok since they aren't private by definition
                logging.info(f"Got {qtype} {qid} for {user.uname}{qfrom}: {qtext}")

                if user.settings.autoblock:
                    logging.info(f"Deleting {qid} and blocking its author")
                    user.api.request(r.report_question(qid, should_block=True))
                else:
                    logging.info(f"Deleting {qid}")
                    user.api.request(r.delete_question(qtype, qid))

        user.api.request(r.mark_notifs_as_read("SHOUTOUT"))
