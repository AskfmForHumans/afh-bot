import logging

from askfm_api import requests as r
from pymongo.collection import ReturnDocument

from askfmforhumans.api import ExtendedApi
from askfmforhumans.user_worker import UserWorker
from askfmforhumans.util import MyDataclass

USERS_QUERY = {"ignore": {"$ne": True}}


class UserManagerConfig(MyDataclass):
    signing_key: str
    settings_header: str
    dry_mode: bool = False
    test_mode: bool = False
    hashtag: str = None
    require_hashtag: bool = True
    tick_interval_sec: int = 30


class UserManager:
    MOD_NAME = "user_manager"

    def __init__(self, app, config):
        self.app = app
        self.config = UserManagerConfig.from_dict(config)
        dry_mode, test_mode = self.config.dry_mode, self.config.test_mode
        if dry_mode or test_mode:
            logging.warning(f"User manager: {dry_mode=} {test_mode=}")
        app.add_task(self.MOD_NAME, self.tick, self.config.tick_interval_sec)

        self.users = {}
        self.db = app.db_collection("users")
        self.anon_api = self.create_api()

    def create_api(self, **kwargs):
        return ExtendedApi(
            self.config.signing_key,
            dry_mode=self.config.dry_mode,
            **kwargs,
        )

    def create_user(self, uname, created_by):
        model = {
            "uname": uname,
            "created_by": created_by,
            "device_id": ExtendedApi.random_device_id(),
        }
        res = self.db.update_one({"uname": uname}, {"$setOnInsert": model}, upsert=True)
        if res.upserted_id:
            logging.info(f"Created user {uname}: {created_by=}")
            self.update_user_local(uname, model)

    def update_user_local(self, uname, model, *, fetch_profile=True):
        if model is None or model.get("ignore"):
            return None

        if uname not in self.users:
            self.users[uname] = UserWorker(uname, self)
        user = self.users[uname]

        user.update_model(model)

        if fetch_profile:
            profile = self.anon_api.request(r.fetch_profile(uname))
            user.update_profile(profile)

        return user

    def update_user(self, uname, model):
        query = {"uname": uname, **USERS_QUERY}
        model = self.db.find_one_and_update(
            query, {"$set": model}, return_document=ReturnDocument.AFTER
        )
        return self.update_user_local(uname, model, fetch_profile=False)

    def tick(self):
        new_users = {}
        for model in self.db.find(USERS_QUERY):
            uname = model["uname"]
            if user := self.update_user_local(uname, model):
                new_users[user.uname] = user
                if user.active:
                    user.tick()
        self.users = new_users
