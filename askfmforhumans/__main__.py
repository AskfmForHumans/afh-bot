import logging
import os

from askfmforhumans.api import ApiManager
from askfmforhumans.app import App
from askfmforhumans.bot import Bot
from askfmforhumans.data_manager import DataManager
from askfmforhumans.user_manager import UserManager
from askfmforhumans.user_worker import UserWorker

logging.basicConfig(level=logging.INFO)

dm = DataManager(
    config_file=os.environ.get("AFH_CONFIG_FILE"), db_url=os.environ.get("AFH_DB_URL")
)

app = App()
app.use_module(ApiManager.MOD_NAME, ApiManager)
app.use_module(Bot.MOD_NAME, Bot)
app.use_module(DataManager.MOD_NAME, dm.init_module)
app.use_module(UserManager.MOD_NAME, UserManager)
app.use_module(UserWorker.MOD_NAME, UserWorker)

app.init_config(dm.get_config())
app.init_modules()
app.run()
