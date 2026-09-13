"""
tests/test_adapter.py — Provider adapter interface tests
"""
from __future__ import annotations

import pytest

from services.providers.adapter import ImageProvider, map_http_error
from services.generation.errors import (
    ProviderAuthError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderTransientError,
)


class TestMapHttpError:
    def test_401_maps_to_auth(self):
        err = map_http_error(401)
        assert isinstance(err, ProviderAuthError)

    def test_429_maps_to_rate_limit(self):
        err = map_http_error(429)
        assert isinstance(err, ProviderRateLimitError)

    def test_500_maps_to_transient(self):
        err = map_http_error(500)
        assert isinstance(err, ProviderTransientError)

    def test_400_maps_to_invalid_request(self):
        err = map_http_error(400)
        assert isinstance(err, ProviderInvalidRequestError)


class TestImageProviderProtocol:
    def test_protocol_exists(self):
        # Verify protocol can be referenced
        assert hasattr(ImageProvider, 'generate')
        assert hasattr(ImageProvider, 'provider_id')
        assert hasattr(ImageProvider, 'display_name')
        assert hasattr(ImageProvider, 'supports_img2img')

    def test_protocol_not_instantiable(self):
        # Protocol classes cannot be instantiated directly
        with pytest.raises(TypeError):
            ImageProvider()
