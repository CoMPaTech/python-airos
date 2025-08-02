"""Ubiquiti AirOS Exceptions."""


class AirOSException(Exception):
    """Base error class for this AirOS library."""


class AirOSConnectionSetupError(AirOSException):
    """Raised when unable to prepare authentication."""


class AirOSConnectionAuthenticationError(AirOSException):
    """Raised when unable to authenticate."""


class AirOSDataMissingError(AirOSException):
    """Raised when expected data is missing."""


class AirOSKeyDataMissingError(AirOSException):
    """Raised when return data is missing critical keys."""


class AirOSDeviceConnectionError(AirOSException):
    """Raised when unable to connect."""


class AirOSDiscoveryError(AirOSException):
    """Base exception for AirOS discovery issues."""


class AirOSListenerError(AirOSDiscoveryError):
    """Raised when the AirOS listener encounters an error."""


class AirOSEndpointError(AirOSDiscoveryError):
    """Raised when there's an issue with the network endpoint."""
