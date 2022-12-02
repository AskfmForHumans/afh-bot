from dataclasses import field

from askfmforhumans.api import ExtendedApi
from askfmforhumans.api import requests as r
from askfmforhumans.app import AppModuleBase, IntervalJob
from askfmforhumans.user import User
from askfmforhumans.util import MyDataclass

DEFAULT_CREATED_BY = "app"


class UserManagerConfig(MyDataclass):
    settings_header: str
    require_hashtag: bool = True
    hashtag: str = None
    sync_users: bool = True
    users: dict = field(default_factory=dict)
    tick_interval_sec: int = 30


class UserManager(AppModuleBase):
    def __init__(self, info):
        super().__init__(info, config_factory=UserManagerConfig.from_dict)

        if self.config.sync_users:
            self.db = info.app.require_module("data_mgr").db_collection("users")
            if self.db is None:
                raise AssertionError("User manager: no DB connection, can't sync")

        if self.config.require_hashtag and not self.config.hashtag:
            raise AssertionError("User manager: no hashtag provided")

        self.api_manager = info.app.require_module("api_mgr")
        self.users = {}
        self._old_models = {}

        for uname, model in self.config.users.items():
            self.get_or_create_user(uname, model)

        self.add_job(IntervalJob("tick", self.tick, self.config.tick_interval_sec))

    @property
    def active_users(self):
        return [u for u in self.users.values() if u.active]

    def get_or_create_user(self, uname, model):
        if uname in self.users:
            return self.users[uname]

        user = self.users[uname] = User(uname, self)
        model = {
            "created_by": DEFAULT_CREATED_BY,
            "device_id": ExtendedApi.random_device_id(),
            **model,
        }
        user.set_model(model)
        self.logger.info(f"Created user {uname}: {model=}")

        if self.config.sync_users:
            remote_model = self.db.find_one({"uname": uname}) or {}
            self.sync_user(user, remote_model)

        self.update_user(user)
        return user

    def tick(self):
        if self.config.sync_users:
            self.sync_users()
        for user in self.users.values():
            self.update_user(user)

    def sync_users(self):
        remote_models = {u["uname"]: u for u in self.db.find()}
        all_unames = set(remote_models) | set(self.users)
        for uname in all_unames:
            if uname not in self.users:
                self.users[uname] = User(uname, self)
            user = self.users[uname]
            self.sync_user(user, remote_models.get(uname, {}))

    def sync_user(self, user, remote_model):
        uname = user.uname
        old_model = self._old_models.get(uname, {})
        user.pre_sync()

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
            self.logger.info(f"User sync: {uname=} {upd_remote=} {upd_local=}")

    def update_user(self, user):
        if not user.model.ignored:
            user.set_profile(
                self.api_manager.anon_api.request(r.fetch_profile(user.uname))
            )
            if user.allowed:
                user.try_auth()
