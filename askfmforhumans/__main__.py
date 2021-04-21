from askfmforhumans.api import ApiManager
from askfmforhumans.app import App
from askfmforhumans.bot import Bot
from askfmforhumans.user_manager import UserManager
from askfmforhumans.user_worker import UserWorker

app = App()
app.use_module(ApiManager.MOD_NAME, ApiManager)
app.use_module(Bot.MOD_NAME, Bot)
app.use_module(UserManager.MOD_NAME, UserManager)
app.use_module(UserWorker.MOD_NAME, UserWorker)
app.start()
