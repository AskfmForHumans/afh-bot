import logging
import os

from askfmforhumans.api import ApiManager
from askfmforhumans.app import App, AppModule
from askfmforhumans.bot import Bot
from askfmforhumans.data_manager import DataManager
from askfmforhumans.user_manager import UserManager
from askfmforhumans.user_worker import UserWorker

logging.basicConfig(style="{", format="{levelname:4.4} {name}: {message}")

dm = DataManager(
    config_file=os.environ.get("AFH_CONFIG_FILE"), db_url=os.environ.get("AFH_DB_URL")
)

app = App()
app.use_module(AppModule("api_mgr", ApiManager))
app.use_module(AppModule("bot", Bot))
app.use_module(AppModule("data_mgr", dm.init_module))
app.use_module(AppModule("user_mgr", UserManager))
app.use_module(AppModule("user_worker", UserWorker))

app.init_config(dm.get_config())
app.init_modules()
app.run()
