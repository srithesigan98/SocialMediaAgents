#!/usr/bin/env python3
"""Themed covers for a campaign's reels. Every reel must go out with a SenangHomes cover.

    python reel_covers.py oneseputeh --profile senang-homes

For each reel in campaigns/<name>.yaml this:
  1. renders a full-height magazine cover at the reel's size: a picked campaign photo
     (reel `cover.photo`, else the campaign's `reel_cover_photo`, else its first slide photo —
     never a random video frame), project label, headline from `cover:` or the `angle`;
  2. commits that PNG to posters/ — Instagram gets it as the reel's cover_url;
  3. prepends the cover as the video's first half second (Threads' API has no cover parameter,
     so the opening frame is its thumbnail) and uploads it to the same GitHub release as
     <stem>-cover.mp4, which is what campaign_post.py posts.
Re-running redoes every reel (gh upload --clobber), so edit a cover and just run it again.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import requests
import yaml
from PIL import Image

import common
import daily_posts
import magazine

COVER_SECONDS = 0.5


def cover_png_path(cfg: dict, reel: dict) -> Path:
    return common.POSTERS_DIR / f"{cfg['_profile']}-reelcover-{Path(reel['file']).stem}.png"


def covered_file(reel: dict) -> str:
    return f"{Path(reel['file']).stem}-cover.mp4"


def cover_text(reel: dict) -> tuple[str, str]:
    """Explicit `cover: {headline, italic}` wins; else split the angle at its first ' — ' or ','."""
    if reel.get("cover"):
        return reel["cover"].get("headline", ""), reel["cover"].get("italic", "")
    angle = reel["angle"]
    for sep in (" — ", ", "):
        if sep in angle:
            head, rest = angle.split(sep, 1)
            return head, rest
    return angle, ""


def render_cover(cfg: dict, name: str, camp: dict, reel: dict, size: tuple[int, int]) -> Path:
    head, ital = cover_text(reel)
    photo = ((reel.get("cover") or {}).get("photo") or camp.get("reel_cover_photo")
             or camp["slides"][0]["photo"])
    slide = magazine.Slide(dict(
        layout="cover", photo=photo, headline=head, italic=ital,
        label=f"{camp['project']} · {camp.get('location', '')}".strip(" ·"),
        subtitle="Watch the full tour.", sticker="Showroom tour",
    ), series=camp.get("series", camp["project"]), page=0, total=0,
        photo_dir=common.profile_path(cfg, f"campaigns/{name}"))
    # magazine's cover is laid out for 1080x1350; stretch the canvas to the reel's ratio and drop
    # the text block by half the extra height so it sits inside Instagram's 3:4 grid crop.
    w, h = size
    full_h = round(magazine.W * h / w)
    saved = magazine.H, magazine.RULE_Y
    magazine.H, magazine.RULE_Y = full_h, magazine.RULE_Y + (full_h - saved[0]) // 2
    try:
        img = slide.render()
    finally:
        magazine.H, magazine.RULE_Y = saved
    out = cover_png_path(cfg, reel)
    img.resize((w, h), Image.LANCZOS).save(out)
    return out


def probe(video: Path) -> tuple[int, int, bool]:
    def q(args):
        return subprocess.run(["ffprobe", "-v", "error", *args, "-of", "csv=p=0", str(video)],
                              capture_output=True, text=True, check=True).stdout.strip()
    w, h = q(["-select_streams", "v:0", "-show_entries", "stream=width,height"]).split(",")[:2]
    has_audio = bool(q(["-select_streams", "a", "-show_entries", "stream=index"]))
    return int(w), int(h), has_audio


def prepend_cover(cover: Path, video: Path, out: Path, has_audio: bool) -> None:
    inputs = ["-loop", "1", "-framerate", "30", "-t", str(COVER_SECONDS), "-i", str(cover)]
    if has_audio:
        inputs += ["-f", "lavfi", "-t", str(COVER_SECONDS), "-i", "anullsrc=r=44100:cl=stereo"]
    inputs += ["-i", str(video)]
    v = 2 if has_audio else 1
    graph = (f"[0:v]format=yuv420p,setsar=1,fps=30[c];[{v}:v]format=yuv420p,setsar=1,fps=30[m];"
             + (f"[{v}:a]aformat=sample_rates=44100:channel_layouts=stereo[ma];"
                "[c][1:a][m][ma]concat=n=2:v=1:a=1[v][a]" if has_audio else "[c][m]concat=n=2:v=1:a=0[v]"))
    maps = ["-map", "[v]"] + (["-map", "[a]", "-c:a", "aac", "-b:a", "160k"] if has_audio else [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, *maps,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-movflags", "+faststart",
                    str(out)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("campaign")
    ap.add_argument("--profile", default=None)
    args = ap.parse_args()
    cfg = common.load_config(args.profile)
    camp = yaml.safe_load(common.profile_path(cfg, f"campaigns/{args.campaign}.yaml").read_text(encoding="utf-8"))
    base = camp["reel_base_url"].rstrip("/")
    tag = base.rsplit("/", 1)[1]
    posted = common.read_state(cfg, "posted").get("listings", {})
    for reel in camp.get("reels", []):
        if f"campaign-{args.campaign}-reel-{reel['file']}" in posted:  # campaign_post.reel_key
            continue
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / reel["file"]
            with requests.get(f"{base}/{reel['file']}", stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(src, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            w, h, has_audio = probe(src)
            png = render_cover(cfg, args.campaign, camp, reel, (w, h))
            out = tmp / covered_file(reel)
            prepend_cover(png, src, out, has_audio)
            subprocess.run(["gh", "release", "upload", tag, str(out), "--clobber"], check=True)
            daily_posts.commit_poster(png)
            print(f"{reel['file']}: cover {png.name}, uploaded {out.name}")


if __name__ == "__main__":
    main()
