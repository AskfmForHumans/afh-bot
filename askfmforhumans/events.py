import logging

from askfmforhumans.util import MyDataclass, AppModuleBase


class EventManagerConfig(MyDataclass):
    greet_users: bool = True
    tick_interval_sec: int = 30


class EventBuilder:
    def __init__(self, mgr):
        self.fields = {}

    def user(self, u):
        self.fields["u.uname"] = u.uname

    def question(self, q):
        self.fields["q.id"] = q.id
        self.fields["q.type"] = q.type
        self.fields["q.author"] = q.author
        self.fields["q.body"] = q.body
        self.fields["q.created_at"] = q.created_at
        self.fields["q.updated_at"] = q.updated_at

    def action(self, q):
        self.fields["a.type"] = q.id
        self.fields["a.block"] = q.id

    def resque(self, *, u, q, a):
        {
            "event": "resque",
            "u.name": u.uname,
            "q.meta": f"{q.type}:{q.id}",
            "q.author": q.author,
        }
        return self

    def user_sync(self, q):
        return self


class EventManager(AppModuleBase):
    def __init__(self, info):
        super().__init__(info, config_factory=EventManagerConfig.from_dict, use_events=False)

    def register_event(self, log_event, db_event):
        self.logger.a
