"""Session state management for cli-web-notebooklm."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionState:
    """Holds runtime session context across commands."""

    # Currently selected notebook (for REPL mode context)
    current_notebook_id: Optional[str] = None
    current_notebook_title: Optional[str] = None

    # Output format preference
    json_output: bool = False

    # Incrementing request ID counter
    _req_id: int = 100000

    # Undo/redo stacks — list of (description, undo_fn) tuples
    _undo_stack: list = field(default_factory=list)
    _redo_stack: list = field(default_factory=list)

    def next_req_id(self) -> int:
        """Get and increment the request ID counter."""
        req_id = self._req_id
        self._req_id += 1
        return req_id

    def push_undo(self, description: str, undo_fn):
        """Record an undoable action."""
        self._undo_stack.append((description, undo_fn))
        self._redo_stack.clear()  # Redo stack cleared on new action

    def undo(self) -> Optional[str]:
        """Undo the last action. Returns description or None if nothing to undo."""
        if not self._undo_stack:
            return None
        description, undo_fn = self._undo_stack.pop()
        undo_fn()
        return description

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def set_notebook(self, notebook_id: str, title: str):
        """Set the current notebook context."""
        self.current_notebook_id = notebook_id
        self.current_notebook_title = title

    def clear_notebook(self):
        """Clear the current notebook context."""
        self.current_notebook_id = None
        self.current_notebook_title = None


# Global session singleton for Click pass_context pattern
_session = SessionState()


def get_session() -> SessionState:
    return _session
