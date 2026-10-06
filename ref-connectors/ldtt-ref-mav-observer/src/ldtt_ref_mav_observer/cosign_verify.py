"""In-process signature verify for revocation list + stamp (Phase 2 draft, A1).

Corrector A1: never trust an unsigned list. Prefer in-process verify
(cryptography for local-key cosign bundles; sigstore-python for Fulcio
keyless Bundle JSON) so missing cosign CLI is not a waiver. Optional
cosign CLI remains as a fallback only.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CosignResult:
    ok: bool
    mode: str  # verified | verified_local_key | verified_sigstore | cosign_cli |
    #            cosign_missing | verify_failed | bundle_missing | key_missing
    detail: str = ""


def find_cosign(explicit: Optional[str] = None) -> Optional[str]:
    """Locate cosign binary: explicit path, PATH, then connector tools/cosign."""
    if explicit:
        p = Path(explicit)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    which = shutil.which("cosign")
    if which:
        return which
    root = Path(__file__).resolve().parents[2]
    candidate = root / "tools" / "cosign"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return None


def sibling_bundle(path: Path) -> Path:
    return Path(str(path) + ".sigstore.json")


def _verify_local_key(blob: bytes, bundle_bytes: bytes, key_path: Path) -> CosignResult:
    """Verify cosign sign-blob local-key bundle (base64Signature + optional rekor)."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.exceptions import InvalidSignature
    except ImportError as exc:
        return CosignResult(ok=False, mode="verify_failed", detail=f"cryptography missing: {exc}")

    if not key_path.is_file():
        return CosignResult(ok=False, mode="key_missing", detail=f"key missing: {key_path}")

    try:
        bundle = json.loads(bundle_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return CosignResult(ok=False, mode="verify_failed", detail=f"bundle JSON: {exc}")

    sig_b64 = bundle.get("base64Signature")
    if not sig_b64:
        return CosignResult(
            ok=False,
            mode="verify_failed",
            detail="bundle has no base64Signature (need keyless Bundle path or cosign CLI)",
        )

    try:
        sig = base64.b64decode(sig_b64)
        pub = serialization.load_pem_public_key(key_path.read_bytes())
        pub.verify(sig, blob, ec.ECDSA(hashes.SHA256()))  # type: ignore[union-attr]
    except InvalidSignature:
        return CosignResult(ok=False, mode="verify_failed", detail="ECDSA signature mismatch")
    except Exception as exc:  # noqa: BLE001
        return CosignResult(ok=False, mode="verify_failed", detail=str(exc)[:500])

    return CosignResult(ok=True, mode="verified_local_key", detail="cryptography ECDSA SHA256")


def _verify_sigstore_bundle(blob: bytes, bundle_bytes: bytes) -> CosignResult:
    """Verify Fulcio/keyless Sigstore Bundle JSON via sigstore-python (in-process)."""
    try:
        from sigstore.models import Bundle
        from sigstore.verify import Verifier
        from sigstore.verify.policy import Identity
    except ImportError as exc:
        return CosignResult(ok=False, mode="verify_failed", detail=f"sigstore missing: {exc}")

    try:
        bundle = Bundle.from_json(bundle_bytes)
    except Exception as exc:  # noqa: BLE001
        return CosignResult(
            ok=False,
            mode="verify_failed",
            detail=f"not a sigstore Bundle JSON: {exc}"[:500],
        )

    identity_re = os.environ.get(
        "LDTT_COSIGN_IDENTITY_REGEXP",
        "https://github.com/.*/\\.github/workflows/.*",
    )
    issuer_re = os.environ.get(
        "LDTT_COSIGN_ISSUER_REGEXP",
        "https://token\\.actions\\.githubusercontent\\.com",
    )
    # Identity policy needs concrete identity; for regexp-style CI we use
    # UnsafeIgnorePolicies only when LDTT_SIGSTORE_UNSAFE_IGNORE=1 (tests).
    # Production CI should set LDTT_COSIGN_IDENTITY to the exact workflow identity.
    identity = os.environ.get("LDTT_COSIGN_IDENTITY")
    issuer = os.environ.get(
        "LDTT_COSIGN_ISSUER",
        "https://token.actions.githubusercontent.com",
    )
    try:
        verifier = Verifier.production()
        if identity:
            policy = Identity(identity=identity, issuer=issuer)
            verifier.verify_artifact(blob, bundle, policy)
        else:
            # Without concrete identity, attempt verify with OfflineMaterials-style
            # is unavailable — report that keyless needs LDTT_COSIGN_IDENTITY or
            # fall through to cosign CLI regexp verify.
            return CosignResult(
                ok=False,
                mode="verify_failed",
                detail=(
                    "sigstore Bundle present but LDTT_COSIGN_IDENTITY unset; "
                    f"set identity (issuer={issuer}; identity_re={identity_re})"
                ),
            )
    except Exception as exc:  # noqa: BLE001
        return CosignResult(ok=False, mode="verify_failed", detail=str(exc)[:500])

    return CosignResult(ok=True, mode="verified_sigstore", detail="sigstore-python verify_artifact")


def _verify_cosign_cli(
    blob_path: Path,
    bundle_path: Path,
    *,
    key_path: Optional[Path],
    cosign_path: Optional[str],
    timeout_s: float,
) -> CosignResult:
    cosign = find_cosign(cosign_path)
    if cosign is None:
        return CosignResult(ok=False, mode="cosign_missing", detail="cosign binary not found")

    cmd = [cosign, "verify-blob", "--bundle", str(bundle_path)]
    if key_path:
        cmd.extend(["--key", str(key_path)])
    else:
        identity = os.environ.get(
            "LDTT_COSIGN_IDENTITY_REGEXP",
            "https://github.com/.*/\\.github/workflows/.*",
        )
        issuer = os.environ.get(
            "LDTT_COSIGN_ISSUER_REGEXP",
            "https://token\\.actions\\.githubusercontent\\.com",
        )
        cmd.extend(
            [
                "--certificate-identity-regexp",
                identity,
                "--certificate-oidc-issuer-regexp",
                issuer,
            ]
        )
    cmd.append(str(blob_path))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CosignResult(ok=False, mode="verify_failed", detail=str(exc))

    if proc.returncode == 0:
        return CosignResult(ok=True, mode="cosign_cli", detail=(proc.stdout or "").strip())
    err = (proc.stderr or proc.stdout or "").strip()
    return CosignResult(ok=False, mode="verify_failed", detail=err[:500])


def verify_blob(
    blob_path: Path | str,
    *,
    bundle_path: Path | str | None = None,
    key_path: Path | str | None = None,
    cosign_path: Optional[str] = None,
    certificate_identity_regexp: Optional[str] = None,
    certificate_oidc_issuer_regexp: Optional[str] = None,
    timeout_s: float = 30.0,
) -> CosignResult:
    """Verify blob + Sigstore/cosign bundle in-process first, CLI fallback.

    Local placeholders: pass key_path (placeholders/keys/ldtt-placeholder.pub).
    CI keyless Bundle: omit key; set LDTT_COSIGN_IDENTITY (sigstore-python) or
    use cosign CLI regexp env vars.
    """
    del certificate_identity_regexp, certificate_oidc_issuer_regexp  # env-driven
    blob_p = Path(blob_path)
    bundle_p = Path(bundle_path) if bundle_path else sibling_bundle(blob_p)
    if not blob_p.is_file():
        return CosignResult(ok=False, mode="verify_failed", detail=f"blob missing: {blob_p}")
    if not bundle_p.is_file():
        return CosignResult(ok=False, mode="bundle_missing", detail=f"bundle missing: {bundle_p}")

    blob = blob_p.read_bytes()
    bundle_bytes = bundle_p.read_bytes()
    key_p = Path(key_path) if key_path else None

    local_result: CosignResult | None = None
    # 1) Local-key cosign simple bundle → cryptography (no CLI)
    if key_p is not None:
        local_result = _verify_local_key(blob, bundle_bytes, key_p)
        if local_result.ok:
            return local_result
        # Signature present but bad → do not accept via other paths
        if "ECDSA signature mismatch" in local_result.detail:
            return local_result

    # 2) Sigstore Bundle JSON → sigstore-python
    sigstore_result = _verify_sigstore_bundle(blob, bundle_bytes)
    if sigstore_result.ok:
        return sigstore_result

    # 3) Optional cosign CLI fallback (still never fail-open)
    cli = _verify_cosign_cli(
        blob_p,
        bundle_p,
        key_path=key_p,
        cosign_path=cosign_path,
        timeout_s=timeout_s,
    )
    if cli.ok:
        return cli

    # Prefer actionable failure: local-key expected, else sigstore, else CLI
    if local_result is not None and local_result.detail:
        return local_result
    if "not a sigstore Bundle" not in sigstore_result.detail:
        return sigstore_result
    if cli.mode == "cosign_missing":
        return CosignResult(
            ok=False,
            mode="cosign_missing",
            detail=(
                f"in-process verify failed ({sigstore_result.detail[:200]}); "
                "cosign CLI also missing — list NOT verified"
            ),
        )
    return cli if cli.detail else sigstore_result



def make_verify_fn(
    *,
    bundle_path: Path | str | None = None,
    key_path: Path | str | None = None,
    cosign_path: Optional[str] = None,
    level: str = "observe",
):
    """Return a VerifyFn(body, sig_bundle_bytes) for RevocationChecker.

    A1: never returns True for an unverified body. ``level`` retained for
    call-site compatibility; Observe no longer fail-opens.
    """
    del level  # A1: same verify rules at all levels

    def _verify(body: bytes, sig_bundle: Optional[bytes]) -> bool:
        with tempfile.TemporaryDirectory(prefix="ldtt-cosign-") as tmp:
            blob = Path(tmp) / "revocations.json"
            blob.write_bytes(body)
            bpath = Path(tmp) / "revocations.json.sigstore.json"
            if sig_bundle is not None:
                bpath.write_bytes(sig_bundle)
            elif bundle_path and Path(bundle_path).is_file():
                bpath.write_bytes(Path(bundle_path).read_bytes())
            else:
                return False
            result = verify_blob(
                blob,
                bundle_path=bpath,
                key_path=key_path,
                cosign_path=cosign_path,
            )
            return result.ok

    return _verify
