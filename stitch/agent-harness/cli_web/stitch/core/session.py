"""Session state for request ID tracking."""


class SessionState:
    def __init__(self):
        self._req_id = 100000

    def next_req_id(self) -> int:
        self._req_id += 100000
        return self._req_id


_session = None


def get_session() -> SessionState:
    global _session
    if _session is None:
        _session = SessionState()
    return _session
