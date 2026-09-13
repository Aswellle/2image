"""
tests/test_metrics.py — Provider request metrics tests
"""
from __future__ import annotations

from services.generation.metrics import (
    MetricsCollector,
    ProviderMetrics,
    get_metrics_collector,
)


class TestProviderMetrics:
    def test_initial_state(self):
        m = ProviderMetrics("test")
        assert m.total_requests == 0
        assert m.success_rate == 1.0

    def test_record_success(self):
        m = ProviderMetrics("test")
        m.record(True, latency_ms=100)
        assert m._successes == 1
        assert m.p50_latency == 100

    def test_record_failure(self):
        m = ProviderMetrics("test")
        m.record(False, error_code="rate_limited")
        assert m._failures == 1
        assert m._rate_limits == 1

    def test_p95_latency(self):
        m = ProviderMetrics("test")
        for i in range(100):
            m.record(True, latency_ms=float(i))
        assert m.p95_latency >= 94

    def test_to_dict(self):
        m = ProviderMetrics("test")
        m.record(True, latency_ms=50)
        d = m.to_dict()
        assert d["provider_id"] == "test"
        assert d["successes"] == 1


class TestMetricsCollector:
    def test_get_creates_on_demand(self):
        c = MetricsCollector()
        m = c.get("siliconflow")
        assert isinstance(m, ProviderMetrics)

    def test_record_and_summary(self):
        c = MetricsCollector()
        c.record("sf", True, latency_ms=100)
        c.record("sf", False, error_code="transient")
        summary = c.summary()
        assert summary["total_requests"] == 2

    def test_all_returns_dict(self):
        c = MetricsCollector()
        c.record("a", True)
        c.record("b", False)
        all_metrics = c.all()
        assert len(all_metrics) == 2
