import logging
import os

import askfmforhumans

logging.basicConfig(style="{", format="{levelname:4.4} {name}: {message}")
app = askfmforhumans.create_app(
    os.environ.get("AFH_CONFIG_FILE"), os.environ.get("AFH_DB_URL")
)
app.run()
