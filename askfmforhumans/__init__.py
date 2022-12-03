from askfmforhumans.api import ApiManager
from askfmforhumans.app import App, AppModuleInfo
from askfmforhumans.bot import Bot
from askfmforhumans.data_manager import DataManager
from askfmforhumans.user_manager import UserManager
from askfmforhumans.user_worker import UserWorker


def create_app(config_file, db_url):
    data_manager = DataManager(config_file=config_file, db_url=db_url)

    app = App()
    app.use_module(AppModuleInfo("api_mgr", ApiManager))
    app.use_module(AppModuleInfo("bot", Bot))
    app.use_module(AppModuleInfo("data_mgr", data_manager.init_module))
    app.use_module(AppModuleInfo("user_mgr", UserManager))
    app.use_module(AppModuleInfo("user_worker", UserWorker))

    app.init_config(data_manager.get_config())
    app.start_modules()
    return app
