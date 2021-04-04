from functools import lru_cache
from itertools import takewhile
import logging

from askfm_api import AskfmApi
from askfm_api import requests as r

CACHE_SIZE = 32


class ExtendedApi(AskfmApi):
    def __init__(self, *args, dry_mode=False, **kwargs):
        # super().__init__() calls request(), so this should come before.
        self.dry_mode = dry_mode
        super().__init__(*args, **kwargs)

        self._reqid = 0
        self._new_qs = 0
        # Decorate here to create separate caches per class instance.
        self._seen_reqid = lru_cache(maxsize=CACHE_SIZE)(self._seen_reqid)

    def request(self, req, **kwargs):
        if not self.dry_mode or req.method == "GET" or req.name == "login":
            return super().request(req, **kwargs)
        logging.info(f"Dry mode: ignoring {req.method} to {req.path}")
        return {}

    def fetch_new_questions(self):
        """Return an iterator to all questions up to the first that was already seen.

        It counts as seen only questions retrieved in previous invocations of this method.
        The daily question is always included (if it exists).
        The cache is bounded, thus it may "forget" seen questions in rare occasions.
        """
        hits, misses, *_ = self._seen_reqid.cache_info()
        logging.debug(
            f"fetch_new_questions(): {self._reqid=}, {self._new_qs=}, {hits=}, {misses=}"
        )

        self._reqid += 1
        # -1 because there will be an extra increment in the last filter invocation
        self._new_qs = -1
        return takewhile(self._not_seen_before, self.request_iter(r.fetch_questions()))

    def _not_seen_before(self, q):
        if q["type"] == "daily":
            return True

        self._new_qs += 1
        # It's useless to query the cache when it's filled with new questions.
        if self._new_qs >= CACHE_SIZE:
            return True

        # If the question is in the cache, a lower reqid will be returned,
        # thus allowing us to distinguish already seen questions.
        # updatedAt is needed for threads and deleted answers.
        return self._seen_reqid(q["qid"], q["updatedAt"]) == self._reqid

    # Decorated with lru_cache in __init__() above
    def _seen_reqid(self, qid, qts):
        return self._reqid
