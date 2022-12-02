from functools import cached_property
from itertools import takewhile

from askfm_api import AskfmApi, AskfmApiError, requests

from askfmforhumans.app import AppModuleBase
from askfmforhumans.util import LRUCache, MyDataclass

CACHE_SIZE = 32


class ApiManagerConfig(MyDataclass):
    signing_key: str
    dry_mode: bool = False


class ApiManager(AppModuleBase):
    def __init__(self, info):
        super().__init__(info, config_factory=ApiManagerConfig.from_dict)
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

        self._new_qs = 0
        self.cache = LRUCache(CACHE_SIZE)

    def request(self, req, **kwargs):
        if not self.dry_mode or req.method == "GET" or req.name == "log_in":
            return super().request(req, **kwargs)
        self.logger.info(f"Dry mode: ignoring {req.method=} {req.path=} {req.params=}")
        return {}

    def fetch_new_questions(self):
        """Return an iterator to all questions up to the first that was already seen.

        It counts as seen only questions retrieved in previous invocations of this method.
        The daily question is always included (if it exists).
        The cache is bounded, thus it may not function properly
        when a lot of questions have been deleted.
        """
        new_qs = 0
        for q in self.request_iter(requests.fetch_questions()):
            if q["type"] != "daily":
                is_new = True
            elif new_qs >= CACHE_SIZE:
                # The cache is already filled with new questions
                # so there's no use to look at it.
                is_new = True
            else:
                # We need to consider `updatedAt` because when it changes
                # the question changes its position in the list.
                q_info = (q["qid"], q["updatedAt"])
                # Returns True if q is already in the cache.
                is_new = not self.cache.check_and_store(q_info)

            if is_new:
                new_qs += 1
                yield q
            else:
                break

        hits, misses, *_ = self.cache.cache_info()
        self.logger.debug(f"fetch_new_questions(): {new_qs=}, {hits=}, {misses=}")
