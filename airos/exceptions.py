"""Ubiquiti AirOS Exceptions."""


class AirOSException(Exception):
    """Base error class for this AirOS library."""


class ConnectionSetupError(AirOSException):
    """Raised when unable to prepare authentication."""


class ConnectionAuthenticationError(AirOSException):
    """Raised when unable to authenticate."""


class DataMissingError(AirOSException):
    """Raised when expected data is missing."""


class KeyDataMissingError(AirOSException):
    """Raised when return data is missing critical keys."""


class DeviceConnectionError(AirOSException):
    """Raised when unable to connect."""
