import logging

from askfm_api import requests as r
from pymongo.collection import ReturnDocument

from askfmforhumans.api import ExtendedApi
from askfmforhumans.user_worker import UserWorker


class UserManager:
    def __init__(self, app, config):
        self.app = app
        self.config = config
        dry_mode, test_mode = config["dry_mode"], config["test_mode"]
        if dry_mode or test_mode:
            logging.warning(f"User manager: {dry_mode=} {test_mode=}")
        app.add_task(
            "user_manager", self.tick, self.config.get("tick_interval_sec", 30)
        )

        self.users = {}
        self.db = app.db_collection("users")
        self.anon_api = self.create_api()

    def create_api(self, token=None):
        return ExtendedApi(
            self.config["signing_key"],
            access_token=token,
            dry_mode=self.config["dry_mode"],
        )

    def user_discovered(self, uname):
        model = {"uname": uname, "created_by": "discovery_hashtag"}
        res = self.db.update_one({"uname": uname}, {"$setOnInsert": model}, upsert=True)
        if res.upserted_id:
            logging.info(f"Discovered new user {uname}")
            model["_id"] = res.upserted_id
            self.update_user(model)

    def update_user(self, model):
        uname = model["uname"]
        user = self.update_user_model(uname, model, local=True)
        profile = self.anon_api.request(r.fetch_profile(uname))
        user.update_profile(profile)
        return user

    def update_user_model(self, uname, model, *, local=False):
        if not local:
            model = self.db.find_one_and_update(
                {"uname": uname}, {"$set": model}, return_document=ReturnDocument.AFTER
            )
            if model is None:
                return None
        if uname not in self.users:
            self.users[uname] = UserWorker(uname, self)
        user = self.users[uname]
        user.update_model(model)
        return user

    def tick(self):
        new_users = {}
        for model in self.db.find({"ignore": {"$ne": True}}):
            user = self.update_user(model)
            if user:
                new_users[user.uname] = user
                if user.active:
                    user.tick()
        self.users = new_users
