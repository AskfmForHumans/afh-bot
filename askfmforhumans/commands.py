import logging

from askfm_api import requests as r

from askfmforhumans import messages

COMMANDS = {}


def command(cmd_text):
    def decorator(func):
        COMMANDS[cmd_text] = func
        return func

    return decorator


@command("пароль")
def login(bot, user, args):
    ok = False
    if len(args) == 1:
        passwd = args[0]
        if 6 <= len(passwd) <= 20:
            ok = user.try_write_password(passwd)
        else:
            logging.warning(f"Got password with length {len(passwd)}")
    else:
        logging.warning("Wrong number of arguments")

    if ok:
        logging.info(f"Notifying {user.uname} about completed login")
        bot.api.request(r.send_question(user.uname, messages.login_ok))
    else:
        logging.info(f"Notifying {user.uname} about failed login")
        bot.api.request(r.send_question(user.uname, messages.login_failed))
