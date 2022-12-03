import logging
import os
import sys
import time

import askfmforhumans
from deta import app


@app.lib.cron()
def run(_):
    # Set up logging inside this function, because Deta does some redirection for `sys.stdout`.
    # For some reason, logs are incomplete when viewed via `deta logs`, but in Deta Visor everything is fine.
    logging.basicConfig(
        style="{",
        format="{levelname:4.4} {name}: {message}",
        stream=sys.stdout,
        force=True,
    )

    app = askfmforhumans.create_app(
        os.environ.get("AFH_CONFIG_FILE"), os.environ.get("AFH_DB_URL")
    )

    # Deta runs our micro every minute with a 10s timeout.
    # So run only the most urgent jobs, but immediately.
    limit = time.time() + 60
    for job in app.scheduler.queue:
        if job.time > limit:
            break
        app.run_job(*job.argument)
