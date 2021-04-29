from functools import cached_property, lru_cache
from itertools import takewhile

from askfm_api import AskfmApi, AskfmApiError, requests

from askfmforhumans.util import MyDataclass

CACHE_SIZE = 32


class ApiManagerConfig(MyDataclass):
    signing_key: str
    dry_mode: bool = False


class ApiManager:
    def __init__(self, am):
        self.logger = am.logger
        self.config = ApiManagerConfig.from_dict(am.config)
        if dry_mode := self.config.dry_mode:
            self.logger.warning(f"{dry_mode=}")

    def create_api(self, **kwargs):
        return ExtendedApi(
            self.logger,
            self.config.signing_key,
            dry_mode=self.config.dry_mode,
            **kwargs,
        )

    @cached_property
    def anon_api(self):
        return self.create_api()


class ExtendedApi(AskfmApi):
    def __init__(self, logger, *args, dry_mode=False, **kwargs):
        # super().__init__() calls request(), so this should come before.
        self.logger = logger
        self.dry_mode = dry_mode
        super().__init__(*args, **kwargs)

        self._reqid = 0
        self._new_qs = 0
        # Returns id of the request when the given question was added to the cache.
        self._q_reqid = lru_cache(maxsize=CACHE_SIZE)(lambda qid, qts: self._reqid)

    def request(self, req, **kwargs):
        if not self.dry_mode or req.method == "GET" or req.name == "log_in":
            return super().request(req, **kwargs)
        self.logger.info(
            f"Dry mode: ignoring {req.method=} {req.path=} {req.params=}"
        )
        return {}

    def fetch_new_questions(self):
        """Return an iterator to all questions up to the first that was already seen.

        It counts as seen only questions retrieved in previous invocations of this method.
        The daily question is always included (if it exists).
        The cache is bounded, thus it may "forget" seen questions in rare occasions.
        """
        # Assume no two requests overlap.
        self._reqid += 1
        self._new_qs = 0
        yield from takewhile(
            self._not_seen_before, self.request_iter(requests.fetch_questions())
        )

        hits, misses, *_ = self._q_reqid.cache_info()
        self.logger.debug(
            f"fetch_new_questions(): {self._reqid=}, {self._new_qs=}, {hits=}, {misses=}"
        )

    def _not_seen_before(self, q):
        if q["type"] == "daily":
            return True

        if (
            self._new_qs >= CACHE_SIZE  # the cache is already filled with new questions
            or self._q_reqid(q["qid"], q["updatedAt"]) == self._reqid
        ):
            self._new_qs += 1
            return True

        return False
