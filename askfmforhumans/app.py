import json
import logging
import os
import re
import time

from askfm_api import AskfmApiError
import configly
import rsa

from askfmforhumans.api import ExtendedApi
from askfmforhumans.bot import Bot
from askfmforhumans.errors import AppError, CryptoError
from askfmforhumans.simple_bot import SimpleBot

MAIN_LOOP_SLEEP_SEC = 30
LETTERS = "abcdefghijklmnopqrstuvwxyzΐάέήίΰαβγδεζηθικλμνξοπρςστυφχψωϊϋόύώϳабвгдежзийклмнопрстуфхцчшщ\
ъыьэюяҋҍҏґғҕҗҙқҝҟҡңҥҧҩҫҭүұҳҵҷҹһҽҿӂӄӆӈӊӌӎӏӑӓӕӗәӛӝӟӡӣӥӧөӫӭӯӱӳӵӷӹաբգդեզէըթժիլխծկհձղճմյնշոչպջռսվտրցւփքօֆ\
ևაბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰⰰⰱⰲⰳⰴⰵⰶⰷⰸⰹⰺⰻⰼⰽⰾⰿⱀⱁⱂⱃⱄⱅⱆⱇⱈⱉⱊⱋⱌⱍⱎⱏⱐ"


class App:
    def __init__(self):
        self.configly = None
        self.cfg = {}
        self.api_key = None
        self.safe_mode = False
        self.test_users_mode = False
        self.setting_regex = None

        self.init_config()
        self.init_crypto()

    def init_config(self):
        loglevel = logging.DEBUG if "DEBUG" in os.environ else logging.INFO
        logging.basicConfig(level=loglevel)

        assert (
            "ASKFM_API_KEY" in os.environ
        ), "Required env variable ASKFM_API_KEY is missing"
        self.api_key = os.environ["ASKFM_API_KEY"]

        if "CONFIGLY_LOCAL_FILE" in os.environ:
            with open(os.environ["CONFIGLY_LOCAL_FILE"], "r") as f:
                self.configly = json.load(f)
        else:
            assert (
                "CONFIGLY_API_KEY" in os.environ
            ), "Required env variable CONFIGLY_API_KEY is missing"
            configly.access_token = os.environ["CONFIGLY_API_KEY"]
            self.configly = configly
        self.cfg = self.get_cfg("config")

        self.setting_regex = re.compile(
            re.escape(self.cfg["hashtag_prefix"])
            + r"([^9]+9?)(.*)"  # why not use 9 as delimiter ¯\_(ツ)_/¯
        )

        test_mode = self.cfg.get("test_mode", "off")
        if test_mode == "safe":
            self.safe_mode = True
            logging.warning("Running in safe mode")
        elif test_mode == "test-users":
            self.test_users_mode = True
            logging.warning("Running in test-users mode")
        else:
            assert test_mode == "off", f"Invalid test_mode: {test_mode}"

    def init_crypto(self):
        assert (
            "AFH_PRIVATE_KEY" in os.environ and "AFH_PUBLIC_KEY" in os.environ
        ), "Required env variable AFH_PRIVATE_KEY/AFH_PUBLIC_KEY is missing"

        keydata = os.environ["AFH_PRIVATE_KEY"].encode("ascii")
        self.rsa_priv = rsa.PrivateKey.load_pkcs1(keydata)

        keydata = os.environ["AFH_PUBLIC_KEY"].encode("ascii")
        self.rsa_pub = rsa.PublicKey.load_pkcs1(keydata)

        assert len(LETTERS) == 256

    def run(self):
        self.bot = SimpleBot(self) if self.cfg["bot_type"] == "simple" else Bot(self)

        while True:
            logging.info("Main loop: starting iteration")
            start = time.time()

            try:
                self.bot.tick()
                # self.update_stats()
            except (AppError, AskfmApiError):
                logging.exception("Main loop:")

            delta = time.time() - start
            logging.info(f"Main loop: finished iteration in {delta:.2f}s")
            time.sleep(MAIN_LOOP_SLEEP_SEC)

    def get_cfg(self, key):
        return self.configly.get(key)

    def create_bot_api(self, *, login=True):
        token = self.cfg.get("access_token")
        api = ExtendedApi(self.api_key, access_token=token, safe_mode=self.safe_mode)
        if token is None and login:
            api.login(self.cfg["bot_username"], self.cfg["bot_password"])
        return api

    def create_user_api(self, login, passwd):
        api = ExtendedApi(self.api_key, safe_mode=self.safe_mode)
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
