from __future__ import annotations

import veille
from supervisor.contracts.preflight import PreflightRequest
from supervisor.runtime import RuntimeSupervisor


def test_public_veille_sdk_reexports_the_single_runtime() -> None:
    assert veille.RuntimeSupervisor is RuntimeSupervisor
    assert veille.Supervisor is RuntimeSupervisor
    assert veille.PreflightRequest is PreflightRequest
