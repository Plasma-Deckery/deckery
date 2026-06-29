# OpenWhispr

**Upstream:** [OpenWhispr/openwhispr](https://github.com/OpenWhispr/openwhispr)
**Deckery fork:** not yet — used unmodified

Hotkey-activated voice input via OpenAI Whisper. Hold a key, speak, release — the transcribed text is typed into the focused application. Supports both cloud (bring-your-own API key) and fully local Whisper models.

## Why it's in Deckery

On a handheld without a physical keyboard, voice input is the most practical text entry method for free-form text (messages, notes, agent instructions). It covers the majority of typing needs without reaching for an external keyboard.

## Setup

OpenWhispr can be triggered by a makima binding. Map a button (e.g. the right trackpad click) to the OpenWhispr hotkey in your `Steam Deck.toml`.

## Noise suppression

Outdoor use with the Steam Deck's built-in microphone benefits significantly from a noise suppressor. The [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles) include an RNNoise PipeWire filter configuration that handles background noise and wind well enough for practical outdoor dictation.

## Known limitations

There are open issues in the upstream OpenWhispr project that noticeably affect usability (response latency, occasional missed activations). These are upstream issues — worth checking their issue tracker before filing a Deckery bug.
