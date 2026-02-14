"""
Session Persistence for Gonka.ai agent inference.

Stores conversation history server-side, keyed by session ID.
Agents send X-Gonka-Session-ID header; the gateway injects prior
messages before forwarding to vLLM, so agents don't re-send context.

Sessions auto-expire after a configurable TTL.
"""

import json
import time
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Session:
    session_id: str
    api_key: str
    messages: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def touch(self):
        self.last_accessed = time.time()

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_accessed


class SessionManager:
    """Manages server-side conversation sessions for agent inference."""

    def __init__(self, ttl_seconds: int = 3600, max_history: int = 100):
        self._sessions: dict[str, Session] = {}
        self._ttl = ttl_seconds
        self._max_history = max_history
        self._lock = threading.Lock()
        self._cleanup_running = False

    def get_or_create(self, session_id: str, api_key: str) -> Session:
        """Get existing session or create new one."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = Session(session_id=session_id, api_key=api_key)
                self._sessions[session_id] = session
            session.touch()
            return session

    def get(self, session_id: str) -> Optional[Session]:
        """Get a session by ID, or None if not found/expired."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.idle_seconds < self._ttl:
                session.touch()
                return session
            elif session:
                # Expired
                del self._sessions[session_id]
            return None

    def append_messages(self, session_id: str, messages: list[dict]):
        """Append messages to a session's history."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return

            session.messages.extend(messages)
            session.touch()

            # Trim to max history (keep system message + last N)
            if len(session.messages) > self._max_history:
                system_msgs = [m for m in session.messages if m.get("role") == "system"]
                non_system = [m for m in session.messages if m.get("role") != "system"]
                keep = self._max_history - len(system_msgs)
                session.messages = system_msgs + non_system[-keep:]

    def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
                return list(session.messages)
            return []

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        removed = 0
        with self._lock:
            expired_ids = [
                sid for sid, s in self._sessions.items()
                if s.idle_seconds >= self._ttl
            ]
            for sid in expired_ids:
                del self._sessions[sid]
                removed += 1
        return removed

    def list_sessions(self, api_key: Optional[str] = None) -> list[dict]:
        """List active sessions, optionally filtered by API key."""
        with self._lock:
            sessions = self._sessions.values()
            if api_key:
                sessions = [s for s in sessions if s.api_key == api_key]

            return [
                {
                    "session_id": s.session_id,
                    "message_count": s.message_count,
                    "created_at": s.created_at,
                    "last_accessed": s.last_accessed,
                    "idle_seconds": round(s.idle_seconds, 1),
                    "metadata": s.metadata,
                }
                for s in sessions
                if s.idle_seconds < self._ttl
            ]

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(
                1 for s in self._sessions.values()
                if s.idle_seconds < self._ttl
            )

    def inject_history(self, session_id: str, request_messages: list[dict]) -> list[dict]:
        """
        Merge session history with incoming request messages.

        Strategy:
        - If request contains system message, use it (might be updated)
        - Prepend session history (without system messages) before new user message
        - This lets agents send just the new user message while keeping context
        """
        history = self.get_history(session_id)
        if not history:
            return request_messages

        # Separate system messages from the request
        system_msgs = [m for m in request_messages if m.get("role") == "system"]
        new_msgs = [m for m in request_messages if m.get("role") != "system"]

        # Get history without system messages
        history_msgs = [m for m in history if m.get("role") != "system"]

        # Combine: system + history + new
        return system_msgs + history_msgs + new_msgs
