from itertools import takewhile
import logging

from askfm_api import AskfmApi
from askfm_api import requests as r


class ExtendedApi(AskfmApi):
    def __init__(self, *args, safe_mode=False, **kwargs):
        self.safe_mode = (
            safe_mode  # super().__init__() calls request(), so this should come before
        )
        self.last_question = None
        super().__init__(*args, **kwargs)

    def request(self, req, **kwargs):
        if not self.safe_mode or req.method == "GET" or req.name == "login":
            return super().request(req, **kwargs)

        logging.info(f"Dry: ignoring {req.method} to {req.path}")
        return {}

    def fetch_new_questions(self):
        # FIXME this is broken

        # return takewhile(self._takewhile, self.request_iter(r.fetch_questions()))
        return self.request(r.fetch_questions())

    def set_last_question(self, q):
        # when a user deletes an answer, qid remains the same, so we need also updatedAt
        self.last_question = q["qid"], q["updatedAt"]
        logging.debug(f"Set last question {self.last_question}")

    def _takewhile(self, q):
        return (q["qid"], q["updatedAt"]) != self.last_question
