from askfm_api import requests as r

from askfmforhumans.user import User


class SimpleBot:
    def __init__(self, app):
        self.app = app
        self.api = app.create_bot_api(login=False)

        unames = app.cfg["user_whitelist"].split(",")
        self.users = [User(uname, self.app) for uname in unames]

    def tick(self):
        for user in self.users:
            profile = self.api.request(r.fetch_profile(user.uname))
            user.update_profile(profile)
            user.tick()
