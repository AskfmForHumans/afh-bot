from askfmforhumans.app import App
from askfmforhumans.bot import Bot
from askfmforhumans.user_manager import UserManager

app = App()
app.use_module(UserManager.MOD_NAME, UserManager, enabled_default=True)
app.use_module(Bot.MOD_NAME, Bot)
app.start()
