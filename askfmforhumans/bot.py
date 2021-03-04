import logging

from askfm_api import requests as r

from askfmforhumans import messages
from askfmforhumans.commands import COMMANDS
from askfmforhumans.user import User


class Bot:
    def __init__(self, app):
        self.app = app
        self.api = app.create_bot_api()

    def tick(self):
        # Delay question processing until after updating users to avoid race condition.
        # E.g. a user first sends us a question, then adds our hashtag.
        qs = list(self.api.fetch_new_questions())
        self.api.request(r.mark_notifs_as_read("SHOUTOUT"))
        self.update_users()
        self.process_questions(qs)

    def update_users(self):
        for user in self.api.request_iter(
            r.search_users_by_hashtag(self.app.cfg["hashtag"])
        ):
            uname = user["uid"]
            profile = self.api.request(r.fetch_profile(uname))

            if uname not in self.app.users:
                user = self.register_user(uname, profile)
            else:
                user = self.app.users[uname]
                user.update_profile(profile)

            user.tick()

    def register_user(self, uname, profile):
        logging.info(f"Registering new user {uname}")
        user = User(uname, self.app)
        user.update_profile(profile)
        self.app.users[uname] = user

        # no need to greet someone who already knows about us (has some settings)
        if user.active and not user.settings:
            logging.info(f"Greeting {uname}")
            self.api.request(
                r.send_question(
                    uname, messages.greet_user.format(full_name=profile["fullName"])
                )
            )

        # self.app.stats["users_new"] += 1
        return user

    def process_questions(self, qs):
        # Never log question bodies as they may contain passwords!
        for q in qs:
            user = self.app.users.get(q["author"] or "")
            if user is not None and user.active:
                qtype, qid = q["type"], q["qid"]
                (cmd, *args) = q["body"].split()
                cmd = cmd.lower()

                if cmd in COMMANDS:
                    logging.info(f"Got command {cmd} (qid={qid}) from {user.uname}")
                    COMMANDS[cmd](self, user, args)
                    logging.info(f"Deleting executed command {qid}")
                    self.api.request(r.delete_question(qtype, qid))
                else:
                    logging.info(f"Got non-command (qid={qid}) from {user.uname}")
