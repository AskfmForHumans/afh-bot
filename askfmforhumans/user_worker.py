from askfmforhumans import handlers, ui_strings
from askfmforhumans.api import requests as r
from askfmforhumans.app import AppModuleBase, DailyJob, IntervalJob
from askfmforhumans.models import Question
from askfmforhumans.util import MyDataclass

# Note: ASKfm threads are complex, so this module ignores them for now


class UserWorkerConfig(MyDataclass):
    job_interval_sec: int = 30
    daily_job_time_utc: str = "00:00"


class UserWorker(AppModuleBase):
    def __init__(self, info):
        super().__init__(info, config_factory=UserWorkerConfig.from_dict)
        self.umgr = info.app.require_module("user_mgr")
        self.handlers = [
            handlers.ShoutoutHandler(self),
            handlers.TextFilterHandler(self),
            handlers.StaleFilterHandler(self),
            handlers.RescueHandler(self),
        ]
        self.add_job(IntervalJob("short", self.short_job, self.config.job_interval_sec))
        self.add_job(DailyJob("long", self.long_job, self.config.daily_job_time_utc))
        self.current_job = None

    def short_job(self):
        self.current_job = "short"
        for user in self.umgr.active_users:
            self.run_handlers(user)
            if user.settings.read_shoutouts:
                user.api.request(r.mark_notifs_as_read("SHOUTOUT"))

    def long_job(self):
        self.current_job = "long"
        for user in self.umgr.active_users:
            self.run_handlers(user)

    def run_handlers(self, user):
        handlers = [h for h in self.handlers if h.enabled_for(user)]
        if not handlers:
            return

        if self.current_job == "short":
            qs = user.api.fetch_new_questions()
        else:
            qs = user.api.request_iter(r.fetch_questions())
            qs = reversed(list(qs))  # rescue questions in the right order

        for q in qs:
            q = Question.from_api_obj(q)
            for h in handlers:
                if h.handle_question(user, q):
                    break

    def delete_question(self, user, q, *, block=False):
        if block:
            self.logger.info(f"Deleting {q.id} and blocking {q.author}")
            user.api.request(r.report_question(q.id, should_block=True))
        else:
            self.logger.info(f"Deleting {q.id}")
            user.api.request(r.delete_question(q.type, q.id))

    def rescue_question(self, user, q):
        self.logger.info(f"Rescuing {q.id}")
        user.api.request(r.post_answer(q.type, q.id, ui_strings.rescuing_answer))
        user.api.request(r.delete_answer(q.id))
