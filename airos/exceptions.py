"""Ubiquiti AirOS Exceptions."""


class AirOSException(Exception):
    """Base error class for this AirOS library."""


class ConnectionFailedError(AirOSException):
    """Raised when unable to connect."""


class DataMissingError(AirOSException):
    """Raised when expected data is missing."""
