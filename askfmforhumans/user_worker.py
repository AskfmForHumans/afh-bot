import re
import time

from askfmforhumans import ui_strings
from askfmforhumans.api import requests as r
from askfmforhumans.models import Question
from askfmforhumans.user import FilterSchedule
from askfmforhumans.util import MyDataclass

SEC_IN_DAY = 60 * 60 * 24
SEC_IN_YEAR = SEC_IN_DAY * 365

# Note: ASKfm threads are complex, so this module ignores them for now


class UserWorkerConfig(MyDataclass):
    short_interval: int = 30
    long_interval: int = SEC_IN_DAY


class Handler:
    def __init__(self, worker):
        self.worker = worker

    def task_matches_schedule(self, user):
        sch = user.settings.filter_schedule
        tt = self.worker.current_task
        return (sch, tt) in (
            (FilterSchedule.CONTINUOUS, "short"),
            (FilterSchedule.DAILY, "long"),
        )

    def enabled_for(self, user):
        raise NotImplementedError

    def handle_question(self, user, q):
        raise NotImplementedError


class ShoutoutHandler(Handler):
    def enabled_for(self, user):
        return user.settings.delete_shoutouts and self.task_matches_schedule(user)

    def handle_question(self, user, q):
        if not q.is_shoutout or (not q.is_anon and user.settings.filter_anon_only):
            return False
        # Logging shoutout bodies is ok since they aren't private by definition
        self.worker.logger.info(
            f"Got {q.type}:{q.id} for {user.uname}: {q.author=} {q.body=}"
        )
        self.worker.delete_question(user, q, block=user.settings.filter_block_authors)
        return True


class TextFilterHandler(Handler):
    def enabled_for(self, user):
        return (
            user.settings.filters_str or user.settings.filters_re
        ) and self.task_matches_schedule(user)

    def handle_question(self, user, q):
        if not q.is_regular or (not q.is_anon and user.settings.filter_anon_only):
            return False
        matched_filter = None
        lower_body = q.body.lower()
        for s in user.settings.filters_str:
            if s.lower() in lower_body:
                matched_filter = s
                break
        else:
            for p in user.settings.filters_re:
                if re.search(p, q.body):
                    matched_filter = p
                    break
        if matched_filter:
            self.worker.logger.info(
                f"Got {q.type}:{q.id} for {user.uname}: {q.author=} {matched_filter=}"
            )
            self.worker.delete_question(
                user, q, block=user.settings.filter_block_authors
            )
            return True
        return False


class StaleFilterHandler(Handler):
    def enabled_for(self, user):
        return user.settings.delete_after != 0 and self.worker.current_task == "long"

    def handle_question(self, user, q):
        if not q.is_regular or (not q.is_anon and user.settings.filter_anon_only):
            return False
        threshold = user.settings.delete_after
        if time.time() - q.updated_at > threshold * SEC_IN_DAY:
            ts = time.asctime(time.gmtime(q.updated_at))
            self.worker.logger.info(
                f"Got {q.type}:{q.id} for {user.uname}: {ts=} {threshold=}"
            )
            self.worker.delete_question(user, q)
            return True
        return False


class RescueHandler(Handler):
    def enabled_for(self, user):
        return user.settings.rescue and self.worker.current_task == "long"

    def handle_question(self, user, q):
        if not q.is_regular:
            return False
        if time.time() - q.updated_at > SEC_IN_YEAR:
            ts = time.asctime(time.gmtime(q.updated_at))
            self.worker.logger.info(f"Got {q.type}:{q.id} for {user.uname}: {ts=}")
            self.worker.rescue_question(user, q)
            return True
        return False


class UserWorker:
    def __init__(self, am):
        self.logger = am.logger
        self.config = UserWorkerConfig.from_dict(am.config)
        self.umgr = am.require_module("user_mgr")
        am.add_job("short", self.short_task, self.config.short_interval)
        am.add_job("long", self.long_task, self.config.long_interval)
        self.handlers = [
            ShoutoutHandler(self),
            TextFilterHandler(self),
            StaleFilterHandler(self),
            RescueHandler(self),
        ]
        self.current_task = None

    def short_task(self):
        self.current_task = "short"
        for user in self.umgr.active_users:
            self.run_handlers(user)
            if user.settings.read_shoutouts:
                user.api.request(r.mark_notifs_as_read("SHOUTOUT"))

    def long_task(self):
        self.current_task = "long"
        for user in self.umgr.active_users:
            self.run_handlers(user)

    def run_handlers(self, user):
        handlers = [h for h in self.handlers if h.enabled_for(user)]
        if not handlers:
            return

        if self.current_task == "short":
            qs = user.api.fetch_new_questions()
        else:
            qs = user.api.request_iter(r.fetch_questions())

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
