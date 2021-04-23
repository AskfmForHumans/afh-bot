import logging

from pymongo.collection import ReturnDocument

from askfmforhumans.api import ExtendedApi
from askfmforhumans.api import requests as r
from askfmforhumans.user import User
from askfmforhumans.util import MyDataclass

DEFAULT_CREATED_BY = "app"


class UserManagerConfig(MyDataclass):
    settings_header: str
    test_mode: bool = False
    hashtag: str = None
    require_hashtag: bool = True
    tick_interval_sec: int = 30


class UserManager:
    MOD_NAME = "user_manager"

    def __init__(self, app, config):
        self.app = app
        self.config = UserManagerConfig.from_dict(config)
        if test_mode := self.config.test_mode:
            logging.warning(f"User manager: {test_mode=}")
        self.api_manager = app.require_module("api_manager")
        app.add_task(self.MOD_NAME, self.tick, self.config.tick_interval_sec)

        self.users = {}
        self._old_models = {}
        self.db = app.db_collection("users")

    # I can't quite figure out what the interface of this module should look like.
    # So let's just make things work.

    @property
    def active_users(self):
        return [u for u in self.users.values() if u.active]

    def get_or_create_user(self, uname, **kwargs):
        if uname in self.users:
            return self.users[uname]

        user = self.users[uname] = User(uname, self)
        model = {
            "created_by": DEFAULT_CREATED_BY,
            "device_id": ExtendedApi.random_device_id(),
            **kwargs,
        }
        user.set_model(model)
        logging.info(f"Created user {uname}: {model=}")

        remote_model = self.db.find_one({"uname": uname}) or {}
        self.sync_user(user, remote_model)
        return user

    def sync_user(self, user, remote_model):
        user.pre_sync()
        uname = user.uname
        old_model = self._old_models.get(uname, {})

        # remote -> local sync
        upd_remote = {k: v for k, v in remote_model.items() if old_model.get(k) != v}
        new_model = remote_model | user.model.as_dict() | upd_remote
        self._old_models[uname] = new_model
        user.set_model(new_model)

        # local -> remote sync
        upd_local = {k: v for k, v in new_model.items() if remote_model.get(k) != v}
        if upd_local:
            query = {"uname": uname}
            update = {"$set": upd_local, "$setOnInsert": query}
            self.db.update_one(query, update, upsert=True)

        if upd_remote or upd_local:
            logging.info(f"User sync: {uname=} {upd_remote=} {upd_local=}")

        if not user.model.ignored:
            user.set_profile(self.api_manager.anon_api.request(r.fetch_profile(uname)))
        user.post_sync()

    def tick(self):
        remote_models = {u["uname"]: u for u in self.db.find()}
        all_unames = set(remote_models) | set(self.users)
        for uname in all_unames:
            if uname not in self.users:
                self.users[uname] = User(uname, self)
            user = self.users[uname]
            self.sync_user(user, remote_models.get(uname, {}))
