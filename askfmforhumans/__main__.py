from askfmforhumans.app import App
from askfmforhumans.bot import Bot
from askfmforhumans.user_manager import UserManager

app = App()
app.use_module("user_manager", UserManager, enabled_default=True)
app.use_module("bot", Bot)
app.start()
