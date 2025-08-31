"""Ubiquiti AirOS 8."""

from __future__ import annotations

from aiohttp import ClientSession

from .base import AirOS
from .data import AirOS8Data


class AirOS8(AirOS[AirOS8Data]):
    """AirOS 8 connection class."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: ClientSession,
        use_ssl: bool = True,
    ) -> None:
        """Initialize AirOS8 class."""
        super().__init__(
            data_model=AirOS8Data,
            host=host,
            username=username,
            password=password,
            session=session,
            use_ssl=use_ssl,
        )
