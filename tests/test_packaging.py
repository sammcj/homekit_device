"""Guards on how the suite is invoked, rather than on integration behaviour."""
from __future__ import annotations

import os
import sys
from pathlib import Path

COMPONENT_ROOT = Path(__file__).resolve().parent.parent


def test_repo_root_is_not_on_sys_path():
    """The repo root must stay off sys.path or it shadows stdlib modules.

    Platform modules are named for their Home Assistant domain, so the root
    holds select.py. On Linux the stdlib `select` is a shared object rather
    than a builtin, so a repo root on sys.path shadows it and `import
    subprocess` fails inside pytest's own startup - long before any test runs.
    macOS cannot reproduce it, because there `select` is compiled in.

    Run the suite through the `pytest` console script (what `make test` does).
    `python -m pytest` prepends the working directory and trips this.
    """
    shadowing = [
        entry
        for entry in sys.path
        if Path(os.path.abspath(entry or ".")) == COMPONENT_ROOT
    ]
    assert not shadowing, (
        f"{COMPONENT_ROOT} is on sys.path via {shadowing}. Run `make test` or "
        "`pytest`, not `python -m pytest`, which prepends the working directory "
        "and lets this repo's select.py shadow the stdlib module on Linux."
    )


def test_the_component_shadows_exactly_one_stdlib_module():
    """Pin which root modules collide with the stdlib, so a new one is noticed.

    select.py is a known and unavoidable collision - Home Assistant requires
    the filename. A second one appearing silently is what this catches.
    """
    collisions = {
        path.stem
        for path in COMPONENT_ROOT.glob("*.py")
        if path.stem in sys.stdlib_module_names
    }

    assert collisions == {"select"}
