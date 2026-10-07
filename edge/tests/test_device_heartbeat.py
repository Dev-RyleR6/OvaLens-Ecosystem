"""Edge liveness is independent of network replay and never changes local scans."""
import sys
import threading
from pathlib import Path
from unittest.mock import Mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.sync.sync_worker import BackgroundSyncWorker


def response(code=200):
    result = Mock(status_code=code)
    if code >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(str(code))
    return result


def worker():
    return BackgroundSyncWorker(Mock(), api_key="test-key", device_id="STATION-TEST")


def test_existing_station_heartbeat_preserves_calibration(monkeypatch):
    post = Mock(return_value=response())
    monkeypatch.setattr(requests, "post", post)
    sync = worker()
    sync.device_status = "SCANNING"
    sync._send_heartbeat()
    assert post.call_count == 1
    assert post.call_args.args[0].endswith('/STATION-TEST/heartbeat')
    assert post.call_args.kwargs['json'] == {'status': 'SCANNING'}
    assert post.call_args.kwargs['timeout'] == 3.0
    assert sync.heartbeat_error is None
    sync.db.mark_scans_synced.assert_not_called()


def test_unknown_station_registers_then_reports_online(monkeypatch):
    post = Mock(side_effect=[response(404), response(), response()])
    monkeypatch.setattr(requests, "post", post)
    sync = worker()
    sync._send_heartbeat()
    assert post.call_count == 3
    assert post.call_args_list[1].args[0].endswith('/devices/register')
    assert post.call_args_list[1].kwargs['json']['device_id'] == 'STATION-TEST'
    assert post.call_args_list[2].kwargs['json'] == {'status': 'ONLINE'}


def test_heartbeat_failure_retains_scans_and_recovers(monkeypatch):
    post = Mock(side_effect=[requests.Timeout(), response()])
    monkeypatch.setattr(requests, "post", post)
    sync = worker()
    sync._send_heartbeat()
    assert 'Timeout' in sync.heartbeat_error
    sync.db.mark_scans_synced.assert_not_called()
    sync._send_heartbeat()
    assert sync.heartbeat_error is None


def test_missing_credentials_never_send_heartbeat(monkeypatch):
    post = Mock()
    monkeypatch.setattr(requests, "post", post)
    sync = worker()
    sync.api_key = ""
    sync._send_heartbeat()
    post.assert_not_called()
    assert 'API_KEY' in sync.heartbeat_error


def test_scan_replay_cannot_starve_heartbeat(monkeypatch):
    syncing = threading.Event()
    release = threading.Event()
    heartbeat = threading.Event()
    sync = worker()

    def stalled_sync():
        syncing.set()
        release.wait(2)

    monkeypatch.setattr(sync, '_perform_sync', stalled_sync)
    monkeypatch.setattr(sync, '_send_heartbeat', heartbeat.set)
    sync.start()
    try:
        assert syncing.wait(1)
        assert heartbeat.wait(1)
    finally:
        release.set()
        sync.stop()
    assert not sync._heartbeat_thread.is_alive()
