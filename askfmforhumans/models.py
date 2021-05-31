from typing import Optional

from askfmforhumans.util import MyDataclass


class UserProfile(MyDataclass):
    full_name: str
    bio: str
    hashtags: list[str]

    @classmethod
    def from_api_obj(cls, obj):
        return cls(
            full_name=obj["fullName"],
            bio=obj["bio"].replace("\r\n", "\n"),
            hashtags=obj["hashtags"],
        )


class Answer(MyDataclass):
    type: str
    author: str
    author_name: str
    body: str
    created_at: int

    @classmethod
    def from_api_obj(cls, obj):
        return cls(
            type=obj["type"],
            author=obj["author"],
            author_name=obj["authorName"],
            body=obj["body"],
            created_at=obj["createdAt"],
        )


class Question(MyDataclass):
    id: int
    type: str
    author: Optional[str]
    body: str
    created_at: int
    updated_at: int
    answer: Optional[Answer]

    @property
    def is_regular(self):
        # excludes "thread" and "daily"
        return self.type in ("anonymous", "user", "shoutout", "anonshoutout")

    @property
    def is_anon(self):
        # I suspect questions from a disabled account will not be anon in this sense,
        # but won't have an author (didn't check). Be aware.
        return self.type in ("anonymous", "anonshoutout")

    @property
    def is_shoutout(self):
        return self.type in ("shoutout", "anonshoutout")

    @classmethod
    def from_api_obj(cls, obj):
        ans = obj.get("answer")
        if ans:
            ans = Answer.from_api_obj(ans)
        return cls(
            id=obj["qid"],
            type=obj["type"],
            author=obj["author"],
            body=obj["body"],
            created_at=obj["createdAt"],
            updated_at=obj["updatedAt"],
            answer=ans,
        )
