# SHOT_LIST.md — raw demo assets

| File | Content | Source | Status |
|---|---|---|---|
| `video/starforge-erc8004-demo.mp4` | Final 2:26 demo with narration | assembled 2026-09-18 | ✅ final |
| `video/narration.mp3` | TTS narration (146s, EN) | `tts synthesize-script`, voice avocado_v2:MAI_03 | ✅ final |
| `video/script.txt` | Narration script | written 2026-09-18 | ✅ final |
| `/tmp/clip_game.mp4` | 25s live STARFORGE gameplay | Chromium kiosk capture :99 | raw (in final) |
| `/tmp/clip_dash2.mp4` | 25s live dashboard (4 sessions, 205.21%) | Chromium kiosk capture :99 | raw (in final) |
| `/tmp/clip_term.mp4` | 26.5s terminal, real session-9 output | PIL render of real stdout | raw (in final) |
| `/tmp/card_title.png`, `/tmp/card_closing.png` | Title/closing cards | PIL render | raw (in final) |
| `/tmp/dash8.png` | Dashboard screenshot (3 sessions era) | superseded by clip_dash2 | archive |

Notes:
- Raw clips live in /tmp (ephemeral). The final mp4 + narration + script are committed in `video/`.
- To re-render with new numbers: update `frontend/index.html`, push gh-pages, re-capture, re-run assembly (see DEMO_SCRIPT.md).
