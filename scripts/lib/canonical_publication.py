from __future__ import annotations

from typing import Any, Mapping, Protocol

from scripts.ingest_phase3_run_metadata import insert_manifest_into_postgres
from scripts.lib.live_verification import (
    ExistingCanonicalPublication,
    inspect_completed_publication_with_cursor,
    update_live_run_publication_with_cursor,
    verify_canonical_publication_with_cursor,
)


class CanonicalVerificationError(RuntimeError):
    def __init__(self, verification: Mapping[str, Any]) -> None:
        super().__init__("canonical publication verification failed")
        self.verification = dict(verification)


class IneligiblePublicationError(RuntimeError):
    pass


class CanonicalDatabaseAdapter(Protocol):
    def lock_publication_identity(
        self,
        manifest: Mapping[str, Any],
    ) -> None: ...

    def insert_manifest(self, manifest: dict[str, Any]) -> dict[str, str]: ...

    def transition_live_run(
        self,
        *,
        live_run_id: str,
        status: str,
        canonical_arm_run_id: str | None = None,
        latest_message: str | None = None,
        explicit_retry: bool = False,
        publication_fingerprint: str | None = None,
    ) -> str: ...

    def inspect_completed(
        self,
        *,
        manifest: Mapping[str, Any],
        live_run_id: str | None,
        publication_fingerprint: str,
        require_r2: bool,
        r2_integrity_verified: bool,
    ) -> ExistingCanonicalPublication | None: ...

    def verify(
        self,
        *,
        manifest: Mapping[str, Any],
        run_id: str,
        arm_run_id: str,
        live_run_id: str | None,
        require_r2: bool,
        r2_integrity_verified: bool,
    ) -> dict[str, Any]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class PsycopgCanonicalDatabaseAdapter:
    """Own one connection for canonical insertion, linking, and verification."""

    def __init__(self, db_url: str) -> None:
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - CLI installs dependency
            raise RuntimeError(
                "psycopg is required for canonical database publication"
            ) from exc
        self.connection = psycopg.connect(db_url)

    def insert_manifest(self, manifest: dict[str, Any]) -> dict[str, str]:
        return insert_manifest_into_postgres(
            manifest,
            connection=self.connection,
        )

    def lock_publication_identity(
        self,
        manifest: Mapping[str, Any],
    ) -> None:
        run = manifest["run"]
        identity = "|".join(
            str(run.get(field) or "")
            for field in (
                "phase",
                "storage_mode",
                "run_label",
                "arm_id",
                "github_run_id",
                "github_run_attempt",
            )
        )
        with self.connection.cursor() as cursor:
            cursor.execute(
                "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (identity,),
            )

    def transition_live_run(
        self,
        *,
        live_run_id: str,
        status: str,
        canonical_arm_run_id: str | None = None,
        latest_message: str | None = None,
        explicit_retry: bool = False,
        publication_fingerprint: str | None = None,
    ) -> str:
        with self.connection.cursor() as cursor:
            return update_live_run_publication_with_cursor(
                cursor,
                live_run_id=live_run_id,
                status=status,
                canonical_arm_run_id=canonical_arm_run_id,
                latest_message=latest_message,
                explicit_retry=explicit_retry,
                publication_fingerprint=publication_fingerprint,
            )

    def inspect_completed(
        self,
        *,
        manifest: Mapping[str, Any],
        live_run_id: str | None,
        publication_fingerprint: str,
        require_r2: bool,
        r2_integrity_verified: bool,
    ) -> ExistingCanonicalPublication | None:
        with self.connection.cursor() as cursor:
            return inspect_completed_publication_with_cursor(
                cursor,
                manifest=manifest,
                live_run_id=live_run_id,
                publication_fingerprint=publication_fingerprint,
                require_r2=require_r2,
                r2_integrity_verified=r2_integrity_verified,
            )

    def verify(
        self,
        *,
        manifest: Mapping[str, Any],
        run_id: str,
        arm_run_id: str,
        live_run_id: str | None,
        require_r2: bool,
        r2_integrity_verified: bool,
    ) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            return verify_canonical_publication_with_cursor(
                cursor,
                manifest=manifest,
                run_id=run_id,
                arm_run_id=arm_run_id,
                live_run_id=live_run_id,
                require_r2=require_r2,
                r2_integrity_verified=r2_integrity_verified,
            )

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()


def publish_manifest_transactionally(
    adapter: CanonicalDatabaseAdapter,
    *,
    manifest: dict[str, Any],
    live_run_id: str | None,
    verify: bool,
    require_r2: bool,
    r2_integrity_verified: bool,
    publication_fingerprint: str,
) -> tuple[dict[str, str], dict[str, Any] | None, str]:
    """Commit canonical rows only after in-transaction verification succeeds."""
    try:
        if live_run_id is None:
            adapter.lock_publication_identity(manifest)
        if live_run_id:
            transition = adapter.transition_live_run(
                live_run_id=live_run_id,
                status="publishing",
                latest_message="Canonical publication is running",
                explicit_retry=True,
            )
            if transition == "completed":
                existing = adapter.inspect_completed(
                    manifest=manifest,
                    live_run_id=live_run_id,
                    publication_fingerprint=publication_fingerprint,
                    require_r2=require_r2,
                    r2_integrity_verified=r2_integrity_verified,
                )
                if existing is None:
                    raise RuntimeError(
                        "completed publication could not be verified"
                    )
                adapter.commit()
                return (
                    {
                        "run_id": existing.run_id,
                        "arm_run_id": existing.arm_run_id,
                    },
                    existing.verification,
                    "already_completed",
                )
            if transition == "ineligible":
                raise IneligiblePublicationError(
                    "ineligible publication cannot be reopened"
                )
        else:
            existing = adapter.inspect_completed(
                manifest=manifest,
                live_run_id=None,
                publication_fingerprint=publication_fingerprint,
                require_r2=require_r2,
                r2_integrity_verified=r2_integrity_verified,
            )
            if existing is not None:
                adapter.commit()
                return (
                    {
                        "run_id": existing.run_id,
                        "arm_run_id": existing.arm_run_id,
                    },
                    existing.verification,
                    "already_completed",
                )

        ids = adapter.insert_manifest(manifest)
        if live_run_id:
            adapter.transition_live_run(
                live_run_id=live_run_id,
                status="verifying" if verify else "completed",
                canonical_arm_run_id=ids["arm_run_id"],
                latest_message="Canonical data was inserted",
                publication_fingerprint=(
                    publication_fingerprint if not verify else None
                ),
            )

        verification: dict[str, Any] | None = None
        if verify:
            verification = adapter.verify(
                manifest=manifest,
                run_id=ids["run_id"],
                arm_run_id=ids["arm_run_id"],
                live_run_id=live_run_id,
                require_r2=require_r2,
                r2_integrity_verified=r2_integrity_verified,
            )
            if not verification["ok"]:
                raise CanonicalVerificationError(verification)
            if live_run_id:
                adapter.transition_live_run(
                    live_run_id=live_run_id,
                    status="completed",
                    canonical_arm_run_id=ids["arm_run_id"],
                    latest_message=(
                        "Canonical publication and verification completed"
                    ),
                    publication_fingerprint=publication_fingerprint,
                )

        adapter.commit()
        return ids, verification, "completed"
    except BaseException:
        adapter.rollback()
        raise
    finally:
        adapter.close()
