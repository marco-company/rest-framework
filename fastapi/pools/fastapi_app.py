# Copyright 2025 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).

import queue
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

    def __get_app(self, env: Environment, root_path: str) -> FastAPI:
        db_name = env.cr.dbname
        try:
            return self._queue_by_db_by_root_path[db_name][root_path].get_nowait()
        except queue.Empty:
            env["fastapi.endpoint"].sudo()
            return env["fastapi.endpoint"].sudo().get_app(root_path)

    def __return_app(self, env: Environment, app: FastAPI, root_path: str) -> None:
        db_name = env.cr.dbname
        self._queue_by_db_by_root_path[db_name][root_path].put(app)

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
        db_name = env.cr.dbname
        self._queue_by_db_by_root_path[db_name][root_path] = queue.Queue()
