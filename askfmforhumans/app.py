import logging
import os
import re
import time

from askfm_api import AskfmApiError
import rsa

from askfmforhumans.api import ExtendedApi
from askfmforhumans.bot import Bot
from askfmforhumans.errors import AppError, CryptoError

MAIN_LOOP_SLEEP_SEC = 30
ENV_VAR_PREFIX = "AFH_"
DEFAULT_CONFIG = {  # ... means "required"
    "api_key": ...,
    "hashtag": ...,
    "hashtag_prefix": ...,
    "bot_username": ...,
    "bot_password": ...,
    "private_key": ...,
    "access_token": None,
    "test_mode": "off",  # off/safe/test-users
}
LETTERS = "abcdefghijklmnopqrstuvwxyzΐάέήίΰαβγδεζηθικλμνξοπρςστυφχψωϊϋόύώϳабвгдежзийклмнопрстуфхцчшщ\
ъыьэюяҋҍҏґғҕҗҙқҝҟҡңҥҧҩҫҭүұҳҵҷҹһҽҿӂӄӆӈӊӌӎӏӑӓӕӗәӛӝӟӡӣӥӧөӫӭӯӱӳӵӷӹաբգդեզէըթժիլխծկհձղճմյնշոչպջռսվտրցւփքօֆ\
ևაბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰⰰⰱⰲⰳⰴⰵⰶⰷⰸⰹⰺⰻⰼⰽⰾⰿⱀⱁⱂⱃⱄⱅⱆⱇⱈⱉⱊⱋⱌⱍⱎⱏⱐ"


class App:
    def __init__(self):
        self.cfg = {}
        self.users = {}
        self.safe_mode = False
        self.test_users_mode = False
        self.setting_regex = None

        self.init_config()
        self.init_crypto()

    def init_config(self):
        loglevel = logging.DEBUG if "DEBUG" in os.environ else logging.INFO
        logging.basicConfig(level=loglevel)

        for key, val in DEFAULT_CONFIG.items():
            var_name = ENV_VAR_PREFIX + key.upper()
            assert (
                val is not ... or var_name in os.environ
            ), f"Required env variable {var_name} is missing"
            self.cfg[key] = os.environ.get(var_name, val)

        assert (
            len(self.cfg["hashtag_prefix"]) <= 4
        ), "Hashtag prefix must be up to 4 characters long"  # len(prefix) + len('p19') + 128/3 <= 50

        self.setting_regex = re.compile(
            re.escape(self.cfg["hashtag_prefix"])
            + r"([^9]+9?)(.*)"  # why not use 9 as delimiter ¯\_(ツ)_/¯
        )

        test_mode = self.cfg["test_mode"]
        if test_mode == "safe":
            self.safe_mode = True
            logging.warning("Running in safe mode")
        elif test_mode == "test-users":
            self.test_users_mode = True
            logging.warning("Running in test-users mode")
        else:
            assert test_mode == "off", f"Invalid test_mode: {test_mode}"

    def init_crypto(self):
        keydata = self.cfg["private_key"].encode("ascii")
        self.rsa_priv = rsa.PrivateKey.load_pkcs1(keydata)

        with open("rsa_public_key.pem", mode="rb") as f:
            keydata = f.read()
            self.rsa_pub = rsa.PublicKey.load_pkcs1(keydata)

        assert len(LETTERS) == 256

    def run(self):
        self.bot = Bot(self)
        while True:
            logging.info("Main loop: starting iteration")
            start = time.time()

            try:
                self.bot.tick()
                # self.update_stats()
            except (AppError, AskfmApiError):
                logging.exception("Main loop:")

            delta = time.time() - start
            logging.info("Main loop: finished iteration in {:.2f}s".format(delta))
            time.sleep(MAIN_LOOP_SLEEP_SEC)

    def create_bot_api(self):
        token = self.cfg["access_token"]
        api = ExtendedApi(
            self.cfg["api_key"], access_token=token, safe_mode=self.safe_mode
        )
        if token is None:
            api.login(self.cfg["bot_username"], self.cfg["bot_password"])
        return api

    def create_user_api(self, login, passwd):
        api = ExtendedApi(self.cfg["api_key"], safe_mode=self.safe_mode)
        api.login(login, passwd)
        return api

    def encrypt_password(self, passwd):
        pw_bytes = passwd.encode()
        try:
            pw_rsa = rsa.encrypt(pw_bytes, self.rsa_pub)
        except rsa.pkcs1.CryptoError as e:
            raise CryptoError("Cannot encrypt password") from e
        assert len(pw_rsa) == 128
        pw_letters = [LETTERS[i] for i in pw_rsa]
        return "".join(pw_letters)

    def decrypt_password(self, passwd):
        try:
            pw_rsa = bytes([LETTERS.index(l) for l in passwd])
            pw_bytes = rsa.decrypt(pw_rsa, self.rsa_priv)
        except (
            ValueError,  # raised by LETTERS.index()
            rsa.pkcs1.CryptoError,
        ) as e:
            raise CryptoError("Cannot decrypt password") from e
        return pw_bytes.decode()
