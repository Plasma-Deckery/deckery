#!/usr/bin/env python3
"""
onboarding.py -- Deprecated entry point for the old setup wizard.

The wizard logic lived in tray/setup/, but it is no longer used by the
application and has been removed. Running this script directly now only
prints a short notice and exits.
"""
import sys

def _deprecated_notice():
    """Print a short notice that the onboarding wizard has been removed."""
    sys.stderr.write(
        "The onboarding wizard has been deprecated and is no longer available.\n"
        "Please use the tray menu for configuration.\n"
    )
    sys.exit(0)

if __name__ == "__main__":
    _deprecated_notice()