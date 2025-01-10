# Copyright 2025 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).

import queue
import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import Generator

from odoo.api import Environment

from fastapi import FastAPI


class FastApiAppPool:
    def __init__(self):
        self._queue_by_db_by_root_path: dict[
            str, dict[str, queue.Queue[FastAPI]]
        ] = defaultdict(lambda: defaultdict(queue.Queue))
        self._lock = threading.Lock()

    def __get_pool(self, env: Environment, root_path: str) -> queue.Queue[FastAPI]:
        db_name = env.cr.dbname
        with self._lock:
            # default dict is not thread safe but the use
            return self._queue_by_db_by_root_path[db_name][root_path]

    def __get_app(self, env: Environment, root_path: str) -> FastAPI:
        pool = self.__get_pool(env, root_path)
        try:
            return pool.get_nowait()
        except queue.Empty:
            env["fastapi.endpoint"].sudo()
            return env["fastapi.endpoint"].sudo().get_app(root_path)

    def __return_app(self, env: Environment, app: FastAPI, root_path: str) -> None:
        pool = self.__get_pool(env, root_path)
        pool.put(app)

    @contextmanager
    def get_app(
        self, root_path: str, env: Environment
    ) -> Generator[FastAPI, None, None]:
        """Return a  FastAPI app to be used in a context manager.

        The app is retrieved from the pool if available, otherwise a new one is created.
        The app is returned to the pool after the context manager exits.

        When used into the FastApiDispatcher class this ensures that the app is reused
        across multiple requests but only one request at a time uses an app.
        """
        app = self.__get_app(env, root_path)
        try:
            yield app
        finally:
            self.__return_app(env, app, root_path)

    def invalidate(self, root_path: str, env: Environment) -> None:
        with self._lock:
            db_name = env.cr.dbname
            self._queue_by_db_by_root_path[db_name][root_path] = queue.Queue()
