# Deckery

A Steam-independent, context-aware input stack for the Steam Deck (and other handheld Linux devices) in desktop mode.

## What it does

- Context-aware button mappings per focused app (via makima)
- Radial menus per app context (via Kando)
- Single source-of-truth config that generates all tool configs
- Visual mode overlay on layer switch
- No Steam required for desktop input

## Projects

| # | Project | Status |
|---|---------|--------|
| 1 | Steam-independence via makima | 🔧 In Progress |
| 2 | Unified config system | 📋 Planned |
| 3 | AT-SPI dynamic menus | 💡 Concept |
| 4 | Mode overlay / HUD | 📋 Planned |

## Structure

```
configs/        # master config (source of truth)
  contexts/     # per-app context definitions
generated/      # auto-generated tool configs (do not edit manually)
  makima/       # generated makima TOML files
  kando/        # generated Kando menus.json
scripts/        # generator scripts
docs/           # architecture, decisions, notes
```

## Device

Tested on: Steam Deck (Bazzite, KDE Plasma 6, Wayland)
Should work on: any handheld Linux device running HHD
