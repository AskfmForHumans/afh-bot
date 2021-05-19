import re
import time

from askfmforhumans.user import FilterSchedule

SEC_IN_DAY = 60 * 60 * 24
SEC_IN_YEAR = SEC_IN_DAY * 365


class Handler:
    def __init__(self, worker):
        self.worker = worker

    def job_matches_schedule(self, user):
        sch = user.settings.filter_schedule
        job = self.worker.current_job
        return (sch, job) in (
            (FilterSchedule.CONTINUOUS, "short"),
            (FilterSchedule.DAILY, "long"),
        )

    def enabled_for(self, user):
        raise NotImplementedError

    def handle_question(self, user, q):
        raise NotImplementedError


class ShoutoutHandler(Handler):
    def enabled_for(self, user):
        return user.settings.delete_shoutouts and self.job_matches_schedule(user)

    def handle_question(self, user, q):
        if not q.is_shoutout or (not q.is_anon and user.settings.filter_anon_only):
            return False
        # Logging shoutout bodies is ok since they aren't private by definition
        self.worker.logger.info(
            f"Got {q.type}:{q.id} for {user.uname}: {q.author=} {q.body=}"
        )
        block = user.settings.filter_block_authors
        self.worker.delete_question( user, q, block=block)
        self.worker.event().user(user).delete(q, block=block).done()
        return True


class TextFilterHandler(Handler):
    def enabled_for(self, user):
        return (
            user.settings.filters_str or user.settings.filters_re
        ) and self.job_matches_schedule(user)

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
            block = user.settings.filter_block_authors
            self.worker.delete_question( user, q, block=block)
            self.worker.event().user(user).delete(q, block=block).done()
            return True
        return False


class StaleFilterHandler(Handler):
    def enabled_for(self, user):
        return user.settings.delete_after != 0 and self.worker.current_job == "long"

    def handle_question(self, user, q):
        if not q.is_regular or (not q.is_anon and user.settings.filter_anon_only):
            return False
        threshold = user.settings.delete_after
        if time.time() - q.updated_at > threshold * SEC_IN_DAY:
            ts = time.asctime(time.gmtime(q.updated_at))
            self.worker.delete_question(user, q)
            self.worker.event().user(user).filter(ts=ts, threshold=threshold).delete(q, block=False).done()
            return True
        return False


class RescueHandler(Handler):
    def enabled_for(self, user):
        return user.settings.rescue and self.worker.current_job == "long"

    def handle_question(self, user, q):
        if not q.is_regular:
            return False
        if time.time() - q.updated_at > SEC_IN_YEAR:
            ts = time.asctime(time.gmtime(q.updated_at))
            self.worker.rescue_question(user, q)
            self.worker.event().user(user).rescue(q).done()
            return True
        return False
