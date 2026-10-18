# fork_addons.py
# CrossWatch - entry point for the additions of this fork
#
# Everything the fork adds is registered here, so crosswatch.py needs a single
# hook and merges from the original project stay conflict free.
from __future__ import annotations

from fork_update import install_update_router
from i18n_frontend import install_i18n
from setup_guard import install_setup_guard

__all__ = ["install_fork_addons"]


def install_fork_addons(app) -> None:
    install_i18n(app)
    install_setup_guard(app)
    install_update_router(app)
