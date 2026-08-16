#!/usr/bin/env python3
"""
onboarding.py -- Entry point for standalone wizard testing.

The wizard logic lives in tray/setup/.
Run directly:
    python3 tray/onboarding.py
Or via tray menu: Setup Wizard... -> imports setup.OnboardingWizard
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from setup import OnboardingWizard

if __name__ == "__main__":
    w = OnboardingWizard(on_done=Gtk.main_quit)
    w.show()
    Gtk.main()
