import time
import uuid

from app.services.rate_limit import _requests, allow_request, reset_rate_limits


def test_allow_request_enforces_limit() -> None:
    reset_rate_limits()
    user_id = uuid.uuid4()

    for _ in range(3):
        assert allow_request(user_id, limit=3) is True
    assert allow_request(user_id, limit=3) is False


def test_allow_request_is_open_when_limit_disabled() -> None:
    reset_rate_limits()
    user_id = uuid.uuid4()

    assert allow_request(user_id, limit=0) is True
    assert user_id not in _requests


def test_window_slides_and_allows_again() -> None:
    reset_rate_limits()
    user_id = uuid.uuid4()
    window = 0.05

    assert allow_request(user_id, limit=1, window_seconds=window) is True
    assert allow_request(user_id, limit=1, window_seconds=window) is False

    time.sleep(window * 3)

    assert allow_request(user_id, limit=1, window_seconds=window) is True


def test_idle_users_are_evicted_from_store() -> None:
    reset_rate_limits()
    idle_user = uuid.uuid4()
    active_user = uuid.uuid4()
    window = 0.05

    assert allow_request(idle_user, limit=5, window_seconds=window) is True
    assert allow_request(active_user, limit=5, window_seconds=window) is True
    assert idle_user in _requests

    time.sleep(window * 3)

    assert allow_request(active_user, limit=5, window_seconds=window) is True

    assert idle_user not in _requests
    assert active_user in _requests
