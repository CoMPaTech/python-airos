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


class AirosDiscoveryError(AirOSException):
    """Base exception for Airos discovery issues."""


class AirosListenerError(AirosDiscoveryError):
    """Raised when the Airos listener encounters an error."""


class AirosEndpointError(AirosDiscoveryError):
    """Raised when there's an issue with the network endpoint."""
