"""Worker entry point — ejecutar con: python -m jarvis.jobs.worker"""

from jarvis.jobs.engine import huey  # noqa: F401 — Huey necesita el import
from jarvis.jobs.tasks import *  # noqa: F401, F403 — Registrar tareas

if __name__ == "__main__":
    from huey.consumer import Consumer

    consumer = Consumer(huey, workers=1, worker_type="thread")
    consumer.run()
