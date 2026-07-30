from __future__ import annotations

from typing import Any, Mapping

import pytest

from scripts.lib.canonical_publication import (
    CanonicalVerificationError,
    IneligiblePublicationError,
    publish_manifest_transactionally,
)
from scripts.lib.live_verification import ExistingCanonicalPublication


class FakeCanonicalAdapter:
    def __init__(
        self,
        *,
        verification_ok: bool = True,
        completed: ExistingCanonicalPublication | None = None,
        transition_status: str | None = None,
    ) -> None:
        self.verification_ok = verification_ok
        self.completed = completed
        self.transition_status = transition_status
        self.calls: list[tuple[str, Any]] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def lock_publication_identity(
        self,
        manifest: Mapping[str, Any],
    ) -> None:
        self.calls.append(("lock", manifest))

    def insert_manifest(self, manifest: dict[str, Any]) -> dict[str, str]:
        self.calls.append(("insert", manifest))
        return {"run_id": "run-uuid", "arm_run_id": "arm-run-uuid"}

    def transition_live_run(self, **kwargs: Any) -> str:
        self.calls.append(("transition", kwargs))
        if self.completed is not None and kwargs["status"] == "publishing":
            return "completed"
        if self.transition_status is not None:
            return self.transition_status
        return str(kwargs["status"])

    def inspect_completed(
        self,
        **kwargs: Any,
    ) -> ExistingCanonicalPublication | None:
        self.calls.append(("inspect_completed", kwargs))
        return self.completed

    def verify(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("verify", kwargs))
        return {
            "ok": self.verification_ok,
            "errors": [] if self.verification_ok else ["trial count mismatch"],
        }

    def commit(self) -> None:
        self.committed = True
        self.calls.append(("commit", None))

    def rollback(self) -> None:
        self.rolled_back = True
        self.calls.append(("rollback", None))

    def close(self) -> None:
        self.closed = True
        self.calls.append(("close", None))


def manifest() -> dict[str, Any]:
    return {"run": {"arm_id": "router-test"}, "trials": [], "artifacts": []}


def completed_publication() -> ExistingCanonicalPublication:
    return ExistingCanonicalPublication(
        run_id="run-uuid",
        arm_run_id="arm-run-uuid",
        publication_fingerprint="fingerprint",
        artifacts=(),
        verification={"ok": True, "errors": []},
    )


def test_successful_canonical_verification_commits_once() -> None:
    adapter = FakeCanonicalAdapter()

    ids, verification, status = publish_manifest_transactionally(
        adapter,
        manifest=manifest(),
        live_run_id="live-test",
        verify=True,
        require_r2=True,
        r2_integrity_verified=True,
        publication_fingerprint="fingerprint",
    )

    assert ids["arm_run_id"] == "arm-run-uuid"
    assert verification == {"ok": True, "errors": []}
    assert status == "completed"
    assert adapter.committed is True
    assert adapter.rolled_back is False
    assert adapter.closed is True
    transitions = [
        details["status"]
        for operation, details in adapter.calls
        if operation == "transition"
    ]
    assert transitions == ["publishing", "verifying", "completed"]
    retry = next(
        details
        for operation, details in adapter.calls
        if operation == "transition"
    )
    assert retry["explicit_retry"] is True


def test_failed_canonical_verification_rolls_back_without_commit() -> None:
    adapter = FakeCanonicalAdapter(verification_ok=False)

    with pytest.raises(CanonicalVerificationError) as raised:
        publish_manifest_transactionally(
            adapter,
            manifest=manifest(),
            live_run_id="live-test",
            verify=True,
            require_r2=False,
            r2_integrity_verified=False,
            publication_fingerprint="fingerprint",
        )

    assert raised.value.verification["errors"] == ["trial count mismatch"]
    assert adapter.rolled_back is True
    assert adapter.committed is False
    assert adapter.closed is True
    assert ("commit", None) not in adapter.calls


def test_unsupervised_publication_skips_live_link_transitions() -> None:
    adapter = FakeCanonicalAdapter()

    publish_manifest_transactionally(
        adapter,
        manifest=manifest(),
        live_run_id=None,
        verify=True,
        require_r2=False,
        r2_integrity_verified=False,
        publication_fingerprint="fingerprint",
    )

    assert all(operation != "transition" for operation, _details in adapter.calls)
    verify_call = next(
        details for operation, details in adapter.calls if operation == "verify"
    )
    assert verify_call["live_run_id"] is None
    assert adapter.committed is True


def test_completed_supervised_replay_is_transactional_noop() -> None:
    adapter = FakeCanonicalAdapter(completed=completed_publication())

    ids, verification, status = publish_manifest_transactionally(
        adapter,
        manifest=manifest(),
        live_run_id="live-test",
        verify=True,
        require_r2=True,
        r2_integrity_verified=True,
        publication_fingerprint="fingerprint",
    )

    assert status == "already_completed"
    assert ids == {"run_id": "run-uuid", "arm_run_id": "arm-run-uuid"}
    assert verification == {"ok": True, "errors": []}
    assert all(operation != "insert" for operation, _details in adapter.calls)
    assert all(operation != "verify" for operation, _details in adapter.calls)
    assert adapter.committed is True
    assert adapter.rolled_back is False


def test_completed_unsupervised_replay_is_transactional_noop() -> None:
    adapter = FakeCanonicalAdapter(completed=completed_publication())

    _ids, _verification, status = publish_manifest_transactionally(
        adapter,
        manifest=manifest(),
        live_run_id=None,
        verify=True,
        require_r2=True,
        r2_integrity_verified=True,
        publication_fingerprint="fingerprint",
    )

    assert status == "already_completed"
    assert adapter.calls[0][0] == "lock"
    assert all(operation != "insert" for operation, _details in adapter.calls)


def test_repeated_completed_publication_calls_never_insert_children() -> None:
    adapters = [
        FakeCanonicalAdapter(completed=completed_publication()),
        FakeCanonicalAdapter(completed=completed_publication()),
    ]

    for adapter in adapters:
        result = publish_manifest_transactionally(
            adapter,
            manifest=manifest(),
            live_run_id="live-test",
            verify=True,
            require_r2=True,
            r2_integrity_verified=True,
            publication_fingerprint="fingerprint",
        )
        assert result[2] == "already_completed"
        assert all(operation != "insert" for operation, _details in adapter.calls)


def test_ineligible_publication_cannot_enter_canonical_insertion() -> None:
    adapter = FakeCanonicalAdapter(transition_status="ineligible")

    with pytest.raises(IneligiblePublicationError):
        publish_manifest_transactionally(
            adapter,
            manifest=manifest(),
            live_run_id="live-test",
            verify=True,
            require_r2=False,
            r2_integrity_verified=False,
            publication_fingerprint="fingerprint",
        )

    assert all(operation != "insert" for operation, _details in adapter.calls)
    assert adapter.rolled_back is True
    assert adapter.committed is False
