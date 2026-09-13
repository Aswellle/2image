"""
tests/test_job_queue.py — Job Queue V2 tests
────────────────────────────────────────────
Validates the job state machine, queue operations, pause/resume,
cancel, and metrics tracking.
"""
from __future__ import annotations

import time

from services.generation.job_queue import (
    Job,
    JobQueue,
    JobState,
    QueueMetrics,
    _TRANSITIONS,
)


class TestJobState:
    def test_valid_transitions(self):
        assert JobState.TRANSLATING in _TRANSITIONS[JobState.QUEUED]
        assert JobState.ROUTING in _TRANSITIONS[JobState.TRANSLATING]
        assert JobState.SUCCEEDED in _TRANSITIONS[JobState.PERSISTING]

    def test_terminal_states_have_no_exits(self):
        for state in (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED, JobState.DEADLINE_EXCEEDED):
            assert len(_TRANSITIONS[state]) == 0


class TestJob:
    def test_job_has_auto_id(self):
        job = Job()
        assert len(job.id) > 0

    def test_job_duration_none_initially(self):
        job = Job()
        assert job.duration_ms is None

    def test_job_is_terminal(self):
        job = Job(state=JobState.SUCCEEDED)
        assert job.is_terminal is True
        job2 = Job(state=JobState.QUEUED)
        assert job2.is_terminal is False


class TestQueueMetrics:
    def test_initial_metrics(self):
        m = QueueMetrics()
        assert m.total_submitted == 0

    def test_record_success(self):
        m = QueueMetrics()
        job = Job(state=JobState.SUCCEEDED, result_provider="test")
        job.started_at = time.time() - 0.1
        job.finished_at = time.time()
        m.record_completion(job)
        assert m.total_succeeded == 1
        assert m.avg_duration_ms > 0

    def test_provider_stats(self):
        m = QueueMetrics()
        job = Job(state=JobState.SUCCEEDED, result_provider="siliconflow")
        job.started_at = time.time() - 0.05
        job.finished_at = time.time()
        m.record_completion(job)
        assert m.provider_stats["siliconflow"]["success"] == 1


        job = Job(state=JobState.FAILED, provider_id="bad")
        m.record_completion(job)
        assert m.total_failed == 1

    def test_record_cancelled(self):
        m = QueueMetrics()
        job = Job(state=JobState.CANCELLED)
        m.record_completion(job)
        assert m.total_cancelled == 1

    def test_provider_stats(self):
        m = QueueMetrics()
        job = Job(state=JobState.SUCCEEDED, result_provider="siliconflow")
        job.started_at = time.time() - 0.05
        job.finished_at = time.time()
        m.record_completion(job)
        assert m.provider_stats["siliconflow"]["success"] == 1



class TestJobQueue:
    def test_submit_returns_id(self):
        q = JobQueue(max_workers=1)
        job_id = q.submit(prompt="test", provider_id="test")
        assert len(job_id) > 0
        job = q.get_job(job_id)
        assert job is not None
        assert job.prompt == "test"

    def test_cancel(self):
        q = JobQueue(max_workers=1)
        job_id = q.submit(prompt="test")
        result = q.cancel(job_id)
        assert result is True

    def test_cancel_nonexistent(self):
        q = JobQueue(max_workers=1)
        result = q.cancel("nonexistent")
        assert result is False

    def test_pause_resume(self):
        q = JobQueue(max_workers=1)
        q.pause()
        q.resume()
        # Should not raise

    def test_get_all_jobs(self):
        q = JobQueue(max_workers=1)
        q.submit(prompt="a")
        q.submit(prompt="b")
        jobs = q.get_all_jobs()
        assert len(jobs) == 2

    def test_job_processing(self):
        """Submit and verify job transitions through states."""
        q = JobQueue(max_workers=1)
        q.start()
        job_id = q.submit(prompt="test", provider_id="test")
        # Wait for processing
        time.sleep(0.5)
        job = q.get_job(job_id)
        assert job is not None
        assert job.state == JobState.SUCCEEDED
        assert job.is_terminal
        q.shutdown()

    def test_callback_fires(self):
        q = JobQueue(max_workers=1)
        updates = []
        q.on_job_update(lambda job: updates.append(job.state))
        q.start()
        job_id = q.submit(prompt="test", provider_id="test")
        time.sleep(0.5)
        assert len(updates) > 0
        q.shutdown()

    def test_cancel_all(self):
        q = JobQueue(max_workers=1)
        q.pause()
        for _ in range(5):
            q.submit(prompt="test")
        count = q.cancel_all()
        assert count == 5
        q.resume()
