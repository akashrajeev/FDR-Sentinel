# Four-minute product demo

Local project: `.local/sentinel-demo/` (ignored media and synthetic screen captures).
Studio: http://localhost:3017/#project/sentinel-demo

The 1920 × 1080 composition is exactly 240 seconds. It uses real portal screenshots
captured while the full real-service browser suite executed, not reconstructed UI or
mocked HTTP responses. Narration is English with an Indian accent: the stock HeyGen
Aditya voice, generated with the workspace-required Orca engine. The 334-word script
produced 154.75 seconds of speech. Generated word timestamps drive the chapter edits;
visual pauses retain time to inspect the actual screens. No voice cloning is used.

An original, procedurally composed electronic underscore and quiet chapter accents
support the narration. The score is reduced to 38% of its already-low level during
speech. The reference mix peaks at 0.860 linear amplitude (below clipping). A separate
`subtitles.srt` uses the generated word timestamps and does not span chapter pauses.
Subtitles are separate so they do not cover the evidence panels in the preview.

| Time | Workflow |
|---|---|
| 0:00–0:18 | Product story and actual public home |
| 0:18–0:37 | Scoped overview, register, dark theme and mobile view |
| 0:37–0:55 | Institution onboarding, operator assignments and atomic CSV intake |
| 0:55–1:14 | Deposit registration, private scanned evidence and provenance |
| 1:14–1:36 | OCR, evidence annotations and independent correction review |
| 1:36–1:58 | Provisional policy checks and independent sandbox mismatch |
| 1:58–2:17 | Officer scrutiny, correction and retained original history |
| 2:17–2:37 | Maturity email and independent renewal lineage |
| 2:37–2:58 | Follow-up reports, escalation, acknowledgement and source resolution |
| 2:58–3:19 | Real PGRC-pending approval block and separate bureau gates |
| 3:19–3:38 | Human synthetic issuance and independent sandbox reconciliation |
| 3:38–4:00 | Scoped audit, recorded engineering evidence and product close |

## Local preview and verification

Run commands from `.local/sentinel-demo/`. Package scripts pin HyperFrames 0.8.192.
The project contains a local FFmpeg/FFprobe distribution under `tools/ffmpeg/`; add
its `bin` directory to the current process PATH if the user's global FFmpeg link is
unavailable. Do not change the system PATH or the main application environment.

```powershell
npx hyperframes preview --background --port 3017 --no-open
npx hyperframes preview --status --json
npm run check
npx hyperframes snapshot --at 8,27,46,65,85,107,128,148,168,186,208,225,236
```

`DESIGN.md`, `SCRIPT.md`, `STORYBOARD.md`, `timeline.json`, `transcript.json`, the
three HTML acts and audio assets remain editable in that local project. `prepare.py`
rebuilds the chapter voice clips and subtitles from the already-generated recording;
`make_audio.py` rebuilds the original score and timed reference mix. Neither calls a
speech provider. Do not regenerate paid/provider audio merely to check status.

The handoff is a Studio preview. MP4 export is a separate explicit request; it has
not been claimed as rendered. When requested, export to the predictable local path:

```powershell
npx hyperframes render --output renders/fdr-sentinel-demo.mp4 --fps 30 --quality high
```

## Evidence and limits

See STATUS.md for the application tests and final composition checks. Fine original
UI text is smaller than the large editorial callouts; focused crops preserve the
real screen. Screen images are intentionally clipped inside camera frames. Crossfade
boundaries intentionally overlap outgoing and incoming scenes for 0.45 seconds.
The video describes supported implemented features; it does not demonstrate every
exception, adversarial fixture or production control. Existing acceptance documents
hold that detailed evidence.

All records are synthetic. Bank and AICTE exchanges use independent local sandboxes.
Policy fixtures remain provisional. Outputs have no official financial/regulatory
authority, and sandbox reconciliation does not represent real settlement. No genuine
connector, approval rule, release transition or policy scope was changed for the film.
