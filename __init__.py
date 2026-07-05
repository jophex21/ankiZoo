from . import deck_browser_widget, economy, reviewer_widget


def _register_all() -> None:
    economy.register_hooks()
    deck_browser_widget.register_hooks()
    reviewer_widget.register_hooks()


_register_all()
