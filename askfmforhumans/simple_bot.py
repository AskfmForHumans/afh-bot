from askfm_api import requests as r

from askfmforhumans.user import User


class SimpleBot:
    def __init__(self, app):
        self.app = app
        self.api = app.create_bot_api(login=False)
        self.users = {}

    def tick(self):
        for user_doc in self.app.db.users.find():
            uname, token = user_doc["uname"], user_doc["access_token"]
            if uname not in self.users:
                self.users[uname] = User(uname, self.app)

            user = self.users[uname]
            profile = self.api.request(r.fetch_profile(uname))
            user.update_profile(profile)
            if user.api is None:
                user.try_login(token)
            user.tick()
