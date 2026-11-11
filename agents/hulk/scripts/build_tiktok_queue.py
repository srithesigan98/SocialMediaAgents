#!/usr/bin/env python3
"""Turn every post already published on Instagram/Threads into a ready-to-post TikTok video.

    python build_tiktok_queue.py --profile senang-homes          # run locally (needs ffmpeg + .env)

Runs locally because it needs ffmpeg and the licensed music beds (gitignored, never committed
raw). For each posting-history entry not yet on TikTok, oldest first, it:
  1. fetches the post exactly as published: Instagram first, Threads when Instagram can't read it
     (posts before 2026-10-18 belong to an Instagram account the current token can't see);
  2. renders a 1080x1920 TikTok video whose first frame is the post's cover (first slide, poster,
     or for a video its themed cover prepended unless it already opens on one — see video_cover),
     so the thumbnail taken at 250 ms is always the cover;
  3. lays a music bed under anything without audio of its own (images, carousels, silent animated
     posters). TikTok's trending sounds can't be added through any API, so this is the licensed
     catalog music the explainers use;
  4. writes posters/<profile>-tiktok-<ref>.mp4 (served from raw.githubusercontent, which Buffer
     accepts) and appends {ref, file, caption, ai_generated} to profiles/<profile>/tiktok_queue.yaml.
tiktok_backlog.py posts one queue item per non-video day. Re-running only adds missing items.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

import common
import platforms
import reel_covers

HERE = Path(__file__).resolve().parent
MUSIC = sorted((HERE.parent / "videos").glob("*/assets/bgm/track.mp3"))
W, H, BG = 1080, 1920, "0x0E1A16"   # Senang Homes ground colour for the letterbox
SLIDE_S, SINGLE_S, COVER_S = 3.0, 7.0, 0.5


def fetch(cfg: dict, platform: str, post_id: str) -> dict | None:
    """{caption, kind: image|video|text, urls} for a published post, or None if unreadable."""
    if platform == "instagram":
        base, (_, token), text = platforms.IG_BASE, platforms._ig(cfg), "caption"
    else:
        base, (_, token), text = platforms.THREADS_BASE, platforms._threads(cfg), "text"
    r = requests.get(f"{base}/{post_id}", timeout=30, params={
        "fields": f"{text},media_type,media_url,children{{media_type,media_url}}", "access_token": token})
    if not r.ok:
        return None
    d = r.json()
    caption = d.get(text, "")
    kids = [c["media_url"] for c in d.get("children", {}).get("data", [])
            if c.get("media_type") == "IMAGE" and c.get("media_url")]
    if kids:
        return {"caption": caption, "kind": "image", "urls": kids}
    if d.get("media_type") in ("VIDEO", "REELS") and d.get("media_url"):
        return {"caption": caption, "kind": "video", "urls": [d["media_url"]]}
    if d.get("media_url"):
        return {"caption": caption, "kind": "image", "urls": [d["media_url"]]}
    return {"caption": caption, "kind": "text", "urls": []}


def probe(path: Path) -> tuple[float, bool]:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                          "-of", "default=nw=1", str(path)], capture_output=True, text=True, check=True).stdout
    return float(re.search(r"duration=([\d.]+)", out).group(1)), "codec_type=audio" in out


def render(images: list[Path], video: Path | None, music: Path, out: Path) -> None:
    """Images (SLIDE_S each, SINGLE_S when alone, COVER_S when fronting a video), then the optional
    video, all letterboxed to 9:16. Audio: the video's own if it has any (delayed past the cover),
    otherwise the music bed with fades."""
    each = COVER_S if video else (SINGLE_S if len(images) == 1 else SLIDE_S)
    args, total, own_audio = [], each * len(images), False
    for img in images:
        args += ["-loop", "1", "-framerate", "30", "-t", str(each), "-i", str(img)]
    if video:
        dur, own_audio = probe(video)
        total += dur
        args += ["-i", str(video)]
    n = len(images) + (1 if video else 0)
    fit = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:"
           f"color={BG},setsar=1,fps=30,format=yuv420p")
    graph = "".join(f"[{i}:v]{fit}[v{i}];" for i in range(n))
    graph += "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v];"
    if own_audio:
        graph += f"[{n - 1}:a]adelay={int(each * len(images) * 1000)}:all=1,apad[a]"
    else:
        args += ["-stream_loop", "-1", "-i", str(music)]
        graph += f"[{n}:a]afade=t=in:d=0.5,afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5,volume=0.8[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                    "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", str(out)], check=True)


# The first explainer went out before topic covers were prepended; later ones carry theirs.
EXPLAINER_COVERS = {"tip-mrta-mlta-video": "video-mrta-mlta-myths-cover.png"}


def video_cover(cfg: dict, ref: str, poster: Path) -> Path | None:
    """The cover image to prepend to a published video, or None if it already opens on one."""
    if ref in EXPLAINER_COVERS:
        return common.POSTERS_DIR / f"{cfg['_profile']}-{EXPLAINER_COVERS[ref]}"
    m = re.fullmatch(r"campaign-(.+?)-reel-(.+)", ref)
    if m:
        # reel_covers.py writes the cover PNG and the cover-prepended upload together, so a reel
        # whose PNG exists was published already opening on it. Older reels get one rendered now.
        name, file = m.groups()
        camp = yaml.safe_load(common.profile_path(cfg, f"campaigns/{name}.yaml").read_text(encoding="utf-8"))
        reel = next(r for r in camp["reels"] if r["file"] == file)
        if reel_covers.cover_png_path(cfg, reel).exists():
            return None
        png = reel_covers.render_cover(cfg, name, camp, reel, (W, H))   # keep the rule above true:
        return png.replace(png.with_name(png.name.replace("-reelcover-", "-tiktokcover-")))
    return poster if poster.exists() else None


def download(url: str, dest: Path) -> Path:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="senang-homes")
    args = ap.parse_args()
    load_dotenv(HERE / ".env")
    cfg = common.load_config(args.profile)
    assert MUSIC, "no music beds found under videos/*/assets/bgm/"
    queue_path = common.profile_path(cfg, "tiktok_queue.yaml")
    queue = (yaml.safe_load(queue_path.read_text(encoding="utf-8")) or []) if queue_path.exists() else []
    have = {i["ref"] for i in queue}
    history = common.read_state(cfg, "posted").get("listings", {})
    todo = sorted((min(p["at"] for p in e["posts"]), ref) for ref, e in history.items()
                  if ref not in have and not ref.startswith("video-")
                  and not any(p["platform"].startswith("tiktok") for p in e["posts"]))

    for _, ref in todo:
        posts = sorted(history[ref]["posts"], key=lambda p: p["at"], reverse=True)   # newest first
        src = None
        for platform in ("instagram", "threads"):
            for p in (p for p in posts if p["platform"] == platform):
                src = src or fetch(cfg, platform, p["post_id"])
        poster = common.POSTERS_DIR / f"{cfg['_profile']}-{ref}.png"
        local = []
        if src and src["kind"] == "text" and poster.exists():   # text-only post: use its poster
            src["kind"], local = "image", [poster]
        if not src or not src["caption"] or not (src["urls"] or local):
            print(f"! {ref}: not readable on Instagram or Threads, or has no media; skipped")
            continue

        out = common.POSTERS_DIR / f"{cfg['_profile']}-tiktok-{re.sub(r'[^A-Za-z0-9_-]+', '-', ref.removesuffix('.mp4'))}.mp4"
        music = MUSIC[len(queue) % len(MUSIC)]
        with tempfile.TemporaryDirectory() as tmp:
            files = local or [download(u, Path(tmp) / f"m{i}") for i, u in enumerate(src["urls"])]
            if src["kind"] == "video":
                cover = video_cover(cfg, ref, poster)
                render([cover] if cover else [], files[0], music, out)
            else:
                render(files, None, music, out)
        queue.append({"ref": ref, "file": out.name, "caption": src["caption"].strip(),
                      "ai_generated": ref.endswith("-video")})   # only the TTS-narrated explainers
        queue_path.write_text(yaml.safe_dump(queue, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
        print(f"{ref}: {src['kind']} x{len(files)} -> {out.name} ({out.stat().st_size // 1024} KB)")
    print(f"{len(queue)} item(s) in {queue_path.name}")


if __name__ == "__main__":
    main()
