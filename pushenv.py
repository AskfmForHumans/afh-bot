"""Push .env to heroku"""

import subprocess

from dotenv import dotenv_values

config = dotenv_values(".env")
pairs = [f"{k}={v}" for k, v in config.items()]
cmd = ["heroku", "config:set", *pairs]
subprocess.run(cmd)
