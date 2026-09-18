# DEMO_SCRIPT.md — Starforge × ERC-8004 demo video

Final video: `video/starforge-erc8004-demo.mp4` (2:26, 1280×720, narration EN).
All footage is real: live GitHub Pages site, real testnet bot output, real on-chain numbers. No AI imagery.

## Narration (TTS: avocado_v2:MAI_03, English)

1. "Meet Starforge: a fully on-chain arcade slot with verifiable randomness and a published RTP of ninety-seven point six percent. Every spin settles by smart contract. No house can cheat the math."
2. "But the player isn't human. It's an AI agent. And on most chains, AI agents are ghosts: no identity, no history, no reputation. You can't tell a winning agent from a scammer."
3. "ERC-8004 changes that. It's the open standard for agent identity and reputation. Our Starforge player is registered as agent eighteen eighty on the official ERC-8004 identity registry, on Monad testnet."
4. "Watch it work. The agent opens a session with a tiny wager. The game draws randomness from the block hash. The arena settles. And here's the key moment: the game contract itself posts that session's RTP as reputation feedback on the official registry. Signed, timestamped, impossible to fake."
5. "Four sessions settled on chain. Lifetime RTP: two hundred five point two one percent. Every number on this dashboard is read straight from chain events: the wallet, the sessions, the payouts, the feedback count."
6. "Four contracts, one open standard, zero trust required. Starforge times ERC-8004: proof that an AI agent can earn its reputation, one verifiable game at a time. Built by Nueve for Monad Metropolis. Testnet only, zero dollars spent."

Source: `video/script.txt`. Audio: `video/narration.mp3` (146s).

## Timeline
| Time | Visual | Narration |
|---|---|---|
| 0:00–0:08 | Title card (slow zoom) | §1 starts |
| 0:08–0:33 | Live STARFORGE game footage | §1–§2 |
| 0:33–0:59 | Terminal: real `play-agent.py` run (session 9) | §3–§4 |
| 0:59–1:39 | Live dashboard (agent #1880, 4 sessions, 205.21%) | §5 |
| 1:39–2:26 | Closing card: contract addresses + repo | §6 |

## Production notes
- Screen capture: Chromium kiosk on Xvfb :99, 1280×720 @15fps via ffmpeg x11grab (proxy workaround for TLS-intercepted network documented in run log).
- Terminal footage: rendered from the REAL stdout of the live testnet run (session 9, 2026-09-18) — see `/tmp/bot_session9.log`.
- Video may be re-cut before 2026-10-13 if more sessions are played; numbers on cards must match the dashboard at render time.
