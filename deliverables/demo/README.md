# Bluebikes demo — 2 minutes 55 seconds

**[Play or download the MP4](bluebikes_demo.mp4)** · [English subtitles](bluebikes_demo_en.srt) · [Final timed script](SCRIPT.md)

If GitHub shows a file page instead of a player, choose **View raw / Download**. The MP4 includes burned-in English captions and a selectable subtitle stream. Avoid enabling duplicate subtitles during playback.

## What this video contains

Real app captures show the Executive Summary, Mermaid architecture, saved Marathon extraction, Confirm → Apply, Boston's April 12→13 full-time crews / $72,000→$78,000, March hiring and the same-month geographic comparison. Explanatory still holds and a closing card make this an edited demonstration, not a continuous live take.

Narration is **Microsoft Zira Desktop, rate -1**, generated locally as six continuous paragraphs. Satoshi selected the continuous-Zira sample. Sentence captions use measured word-boundary events with an explicit matching 16 kHz PCM output format; waveform segments are joined without inserted sentence gaps. There is no speech API, new OpenAI call, voice cloning or additional service charge. The saved real OpenAI extraction is separate from voice generation.

The 307-word source narration and original app/model evidence are retained. +3,000 handling actions is an uncalibrated human scenario; the map is station-coordinate context, not routes or crew bases. Confirmed contribution claims remain bounded to the evidence. Aditi's contribution is not yet confirmed.

## Verify and review

Media duration is **175.00 seconds**, 1920×1080 at 25 fps, H.264/AAC. See [verification](verification.json) and [production timing](production-manifest.json). Technical decoding and subtitle checks cannot certify pronunciation or listening quality; final full-video human review remains required.

For a correction, open a PR with the timestamp, issue and proposed edit. Update the narration and subtitles together; rerender and recheck the entire video after changing either. Put experimental variants in ignored `build/` and replace the committed release only after review. The earlier candidate remains preserved locally in `build/demo-video-c9583c8`.

## Rebuild on Windows

Prerequisites: the repository Python environment (including Pillow), Windows **PowerShell 5.1**, installed Microsoft Zira Desktop, Arial fonts, and `ffmpeg` / `ffprobe` on PATH. No network or API key is used. Other platforms and voices are not validated for this production recipe. The genuine source captures are from app commit `c9583c809bf0c7add65239ceb6d4be981ab10fc2`.

From the repository root, choose a new build folder:

```powershell
New-Item -ItemType Directory -Path build/demo-video-rebuild
tar -xzf deliverables/demo/editing-source.tar.gz -C build/demo-video-rebuild
powershell.exe -NoProfile -File build/demo-video-rebuild/synthesize_continuous.ps1
.\.venv\Scripts\python.exe build/demo-video-rebuild/split_continuous.py
.\.venv\Scripts\python.exe build/demo-video-rebuild/compose.py
```

The result is `build/demo-video-rebuild/bluebikes_demo_candidate.mp4`. The compositor checks the existing focused result before rendering. Installed voice/encoder versions can affect byte-level output; compare timing and content rather than expecting an identical MP4 hash. Never replace the genuine app captures with fabricated interaction frames.

## Submission access

The TA confirmed registration and requires a public repository. Publication and signed-out video access must be completed before Canvas submission; see [current checklist](../../docs/SUBMISSION_PREP.md). This production package does not claim a Canvas upload, all-member approval or acceptance by the teaching team.
