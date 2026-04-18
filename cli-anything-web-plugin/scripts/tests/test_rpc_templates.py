"""Tests for the batchexecute RPC templates.

Renders a scaffolded CLI, imports the generated rpc/ modules, and verifies
their behavior against realistic batchexecute inputs. This catches drift
between the templates and production notebooklm/stitch implementations.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCAFFOLD = SCRIPTS_DIR / "scaffold-cli.py"


@pytest.fixture(scope="module")
def rpc_modules(tmp_path_factory):
    """Scaffold a batchexecute CLI once and load its rpc/ modules."""
    out_dir = tmp_path_factory.mktemp("rpc_scaffold") / "gen"
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(out_dir),
            "--app-name", "rpctest",
            "--protocol", "batchexecute",
            "--http-client", "httpx",
            "--auth-type", "google-sso",
            "--resources", "items",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    pkg_root = out_dir / "cli_web" / "rpctest"

    # Make the generated package importable from this test process.
    sys.path.insert(0, str(out_dir))

    # Load the rpc submodules (skipping auth.py which requires playwright/httpx
    # at import-time via fetch_tokens).
    def _load(modname: str, path: Path):
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
        return mod

    # Load exceptions first — decoder imports it.
    _load("cli_web.rpctest", pkg_root / "__init__.py")
    _load("cli_web.rpctest.core", pkg_root / "core" / "__init__.py")
    _load("cli_web.rpctest.core.exceptions", pkg_root / "core" / "exceptions.py")
    _load("cli_web.rpctest.core.rpc", pkg_root / "core" / "rpc" / "__init__.py")
    types_mod = _load("cli_web.rpctest.core.rpc.types", pkg_root / "core" / "rpc" / "types.py")
    encoder = _load("cli_web.rpctest.core.rpc.encoder", pkg_root / "core" / "rpc" / "encoder.py")
    decoder = _load("cli_web.rpctest.core.rpc.decoder", pkg_root / "core" / "rpc" / "decoder.py")
    return types_mod, encoder, decoder


# --- Encoder ---

def test_encode_request_returns_url_encoded_string(rpc_modules):
    _, encoder, _ = rpc_modules
    out = encoder.encode_request("wXbhsf", [None, 10], csrf_token="tok123")
    # Must be URL-encoded form body (not a dict)
    assert isinstance(out, str)
    assert "f.req=" in out
    assert "at=tok123" in out


def test_build_url_includes_required_params(rpc_modules):
    _, encoder, _ = rpc_modules
    url = encoder.build_url(
        "wXbhsf",
        session_id="-123456",
        build_label="boq_labstailwinduiserver_20250101.00_p0",
        source_path="/notebook/abc",
        req_id=200000,
    )
    assert "rpcids=wXbhsf" in url
    assert "f.sid=-123456" in url
    assert "bl=boq_labstailwinduiserver" in url
    assert "_reqid=200000" in url


def test_build_url_omits_build_label_when_empty(rpc_modules):
    _, encoder, _ = rpc_modules
    url = encoder.build_url("wXbhsf", session_id="1", build_label="", source_path="/")
    assert "bl=" not in url


# --- Decoder ---

def test_strip_prefix_removes_anti_xssi(rpc_modules):
    _, _, decoder = rpc_modules
    assert decoder.strip_prefix(")]}'\n[[1,2]]") == "[[1,2]]"
    assert decoder.strip_prefix("[[1,2]]") == "[[1,2]]"


def test_strip_prefix_handles_bytes(rpc_modules):
    _, _, decoder = rpc_modules
    assert decoder.strip_prefix(b")]}'\n[1]") == "[1]"


def test_parse_chunks_multi_chunk_response(rpc_modules):
    """Real batchexecute responses contain multiple JSON chunks with length hints."""
    _, _, decoder = rpc_modules
    body = '11927\n[["wrb.fr","wXbhsf","\\"hello\\""]]\n27\n[["e",4,null,null,12542]]'
    chunks = decoder.parse_chunks(body)
    assert len(chunks) == 2
    assert '"wrb.fr"' in chunks[0]
    assert '"e"' in chunks[1]


def test_parse_chunks_ignores_length_hint_lines(rpc_modules):
    _, _, decoder = rpc_modules
    body = '5\n[]\n10\n[[1]]'
    assert len(decoder.parse_chunks(body)) == 2


def test_extract_result_finds_rpc_payload(rpc_modules):
    _, _, decoder = rpc_modules
    chunks = ['[["wrb.fr","xyz","[1,2,3]"]]']
    assert decoder.extract_result(chunks, "xyz") == [1, 2, 3]


def test_extract_result_raises_auth_error_on_code_7(rpc_modules):
    types, _, decoder = rpc_modules
    from cli_web.rpctest.core.exceptions import AuthError
    chunks = ['[["er",7,null,null,null]]']
    with pytest.raises(AuthError):
        decoder.extract_result(chunks, "xyz")


def test_extract_result_raises_rpc_error_on_unknown_code(rpc_modules):
    types, _, decoder = rpc_modules
    from cli_web.rpctest.core.exceptions import RPCError
    chunks = ['[["er",99,null]]']
    with pytest.raises(RPCError):
        decoder.extract_result(chunks, "xyz")


def test_extract_result_raises_rpc_error_when_missing(rpc_modules):
    _, _, decoder = rpc_modules
    from cli_web.rpctest.core.exceptions import RPCError
    chunks = ['[["wrb.fr","other","[]"]]']
    with pytest.raises(RPCError):
        decoder.extract_result(chunks, "wanted")


def test_decode_response_full_pipeline(rpc_modules):
    _, _, decoder = rpc_modules
    body = ')]}\'\n35\n[["wrb.fr","xyz","[\\"ok\\"]"]]'
    assert decoder.decode_response(body, "xyz") == ["ok"]
