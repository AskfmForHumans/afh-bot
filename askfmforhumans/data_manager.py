from pymongo import MongoClient
import toml


class DataManager:
    def __init__(self, *, config_file=None, db_url=None):
        if not config_file and not db_url:
            raise AssertionError("Data manager: no sources provided")
        self.config = self.db = None
        if config_file:
            self.config = toml.load(config_file)
        if db_url:
            self.db = MongoClient(db_url).get_default_database()

    def init_module(self, am):
        return self

    def get_config(self):
        if self.config is not None:
            return self.config
        return self.db_singleton("config")

    def db_collection(self, name):
        if self.db:
            return self.db.get_collection(name)
        return None

    def db_singleton(self, name):
        if self.db:
            return self.db_collection("singletons").find_one({"_id": name})
        return None
