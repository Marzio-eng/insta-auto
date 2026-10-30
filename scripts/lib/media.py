"""Media helpers: probing, decoding (HEIC included), house grade, speech detection.

Used by the preparation task only (runs in the Claude cloud session, not in GitHub Actions).
"""
import json
import os
import subprocess
from datetime import datetime

import numpy as np
from PIL import Image, ImageOps, ExifTags

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:  # HEIC unsupported without pillow-heif
    pass

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}

# "Elite Warm" house grade, shared by photos and videos so the grid stays consistent:
# blacks lifted a touch (never crushed), shadows slightly opened, highlights rolled off,
# warm shift in mids/highlights, saturation held back.
GRADE = ",".join([
    "curves=all='0/0.03 0.12/0.13 0.5/0.51 0.88/0.87 1/0.96'",
    "colorbalance=rs=0.02:bs=-0.03:rm=0.04:gm=0.005:bm=-0.04:rh=0.03:bh=-0.03",
    "eq=saturation=0.87",
])


def kind(path):
    ext = os.path.splitext(path)[1].lower()
    return "image" if ext in IMAGE_EXT else "video" if ext in VIDEO_EXT else None


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


# ---------------------------------------------------------------- metadata

def _gps_to_deg(v, ref):
    d, m, s = (float(x) for x in v)
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def image_meta(path):
    im = Image.open(path)
    exif = im.getexif()
    w, h = ImageOps.exif_transpose(im).size
    meta = {"width": w, "height": h}
    ifd = exif.get_ifd(ExifTags.IFD.Exif)
    taken = ifd.get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
    if taken:
        try:
            meta["taken_at"] = datetime.strptime(str(taken), "%Y:%m:%d %H:%M:%S").isoformat()
        except ValueError:
            pass
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    if gps.get(2) and gps.get(4):
        meta["gps"] = [round(_gps_to_deg(gps[2], gps.get(1)), 5), round(_gps_to_deg(gps[4], gps.get(3)), 5)]
    meta["camera"] = " ".join(str(exif.get(t, "")) for t in (ExifTags.Base.Make, ExifTags.Base.Model)).strip() or None
    return meta


def video_meta(path):
    p = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path]).stdout)
    v = next((s for s in p["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []):
        rot = int(sd.get("rotation", 0)) or rot
    if abs(rot) in (90, 270):
        w, h = h, w
    tags = {k.lower(): val for k, val in p["format"].get("tags", {}).items()}
    meta = {"width": w, "height": h, "duration": round(float(p["format"].get("duration", 0)), 2),
            "fps": v.get("avg_frame_rate"), "codec": v.get("codec_name"), "has_audio": a is not None,
            "hdr": v.get("color_transfer") in ("arib-std-b67", "smpte2084")}
    taken = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
    if taken:
        meta["taken_at"] = taken[:19]
    loc = tags.get("com.apple.quicktime.location.iso6709") or tags.get("location")
    if loc:
        import re
        m = re.match(r"([+-]\d+\.?\d*)([+-]\d+\.?\d*)", loc)
        if m:
            meta["gps"] = [round(float(m.group(1)), 5), round(float(m.group(2)), 5)]
    meta["camera"] = tags.get("com.apple.quicktime.model")
    return meta


# ---------------------------------------------------------------- decoding / previews

def load_image(path):
    """Decoded, orientation-corrected RGB image (HEIC supported)."""
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def video_frames(path, times, width=480):
    """Grab frames at the given timestamps (seconds) as PIL images."""
    out = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
                              "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                             capture_output=True, check=True).stdout
        if raw:
            from io import BytesIO
            out.append(Image.open(BytesIO(raw)).convert("RGB"))
    return out


def luma_stats(img):
    a = np.asarray(img.convert("L").resize((256, 256)), dtype=np.float32) / 255
    return {"mean": round(float(a.mean()), 3), "p05": round(float(np.percentile(a, 5)), 3),
            "p95": round(float(np.percentile(a, 95)), 3)}


def sharpness(img):
    a = np.asarray(img.convert("L").resize((512, 512)), dtype=np.float32)
    lap = a[1:-1, 1:-1] * 4 - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    return round(float(lap.var()), 1)


# ---------------------------------------------------------------- speech detection

def speech_score(path):
    """Share of 30 ms frames flagged as voice by WebRTC VAD (0..1), plus loudness.

    A high ratio with a person on screen means "Eliott talks"; music alone also triggers the
    VAD partly, so the result is a hint to confirm by looking at frames, not a verdict.
    """
    import webrtcvad
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    if not pcm:
        return {"voice_ratio": 0.0, "rms_db": None}
    samples = np.frombuffer(pcm, dtype=np.int16)
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) or 1e-9
    vad = webrtcvad.Vad(3)
    frame = 480 * 2  # 30 ms @ 16 kHz, 16-bit
    flags = [vad.is_speech(pcm[i:i + frame], 16000) for i in range(0, len(pcm) - frame, frame)]
    # speech band energy share (300-3400 Hz) as a second hint
    spec = np.abs(np.fft.rfft(samples[: 16000 * 30].astype(np.float32)))
    freqs = np.fft.rfftfreq(min(len(samples), 16000 * 30), 1 / 16000)
    band = spec[(freqs > 300) & (freqs < 3400)].sum() / (spec.sum() or 1)
    return {"voice_ratio": round(sum(flags) / max(len(flags), 1), 2),
            "speech_band": round(float(band), 2),
            "rms_db": round(20 * np.log10(rms / 32768), 1)}


# ---------------------------------------------------------------- rendering

def exposure_gamma(img):
    """Gentle lift for under-exposed phone shots; leaves night shots dark (never > 1.3)."""
    st = luma_stats(img)
    if st["p95"] > 0.6:  # real highlights (lit night scene, sunset): darkness is intended, keep it
        return 1.0
    return float(min(1.3, max(1.0, (0.36 / max(st["mean"], 0.05)) ** 0.3)))


def crop_box(w, h, ratio, focus=(0.5, 0.5), zoom=1.0):
    """Largest box of aspect `ratio` (w/h) inside w×h, centred on `focus` (0..1), optionally zoomed."""
    if w / h > ratio:
        ch, cw = h, h * ratio
    else:
        cw, ch = w, w / ratio
    cw, ch = cw / zoom, ch / zoom
    x = min(max(focus[0] * w - cw / 2, 0), w - cw)
    y = min(max(focus[1] * h - ch / 2, 0), h - ch)
    return int(x), int(y), int(x + cw), int(y + ch)


def render_image(src, dest, size, focus=(0.5, 0.5), zoom=1.0, rotate=0.0, gamma=None, extra_filters=""):
    """Final JPEG: straighten, crop to size, house grade, sRGB, quality 92."""
    img = load_image(src)
    if rotate:
        # rotate then crop away the empty corners
        w, h = img.size
        img = img.rotate(-rotate, resample=Image.BICUBIC, expand=False)
        import math
        r = math.radians(abs(rotate))
        k = 1 / (math.cos(r) + math.sin(r) * max(w / h, h / w))
        img = img.crop((int(w * (1 - k) / 2), int(h * (1 - k) / 2), int(w * (1 + k) / 2), int(h * (1 + k) / 2)))
    tw, th = size
    img = img.crop(crop_box(*img.size, tw / th, focus, zoom)).resize((tw, th), Image.LANCZOS)
    g = gamma if gamma is not None else exposure_gamma(img)
    tmp = dest + ".src.png"
    img.save(tmp)
    vf = f"eq=gamma={g:.3f}," + GRADE + (f",{extra_filters}" if extra_filters else "") + ",unsharp=3:3:0.3"
    try:
        run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-vf", vf, "-q:v", "2", "-pix_fmt", "yuvj420p", dest])
    finally:
        os.remove(tmp)
    return {"gamma": round(g, 3)}


HDR_TO_SDR = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
              "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def render_video(src, dest, size=(1080, 1920), start=0.0, duration=None, focus_x=0.5, zoom=1.0,
                 gamma=1.0, keep_audio=True, audio_gain_db=0.0, fps=30, extra_filters=""):
    """Instagram-ready MP4: H.264 High, yuv420p, 30 fps, AAC 48 kHz, faststart, house grade.

    Crops to the target ratio around `focus_x` (0..1, horizontal subject position), tone-maps HDR (iPhone
    Dolby Vision / HLG) to SDR first. Audio is kept as is (original sound) unless keep_audio=False,
    in which case a silent track is written (Instagram expects an audio stream).
    """
    m = video_meta(src)
    tw, th = size
    ratio = tw / th
    w, h = m["width"], m["height"]
    if w / h > ratio:
        cw, ch = h * ratio / zoom, h / zoom
    else:
        cw, ch = w / zoom, w / ratio / zoom
    cx = min(max(focus_x * w - cw / 2, 0), w - cw)
    cy = (h - ch) / 2
    chain = []
    if m.get("hdr"):
        chain.append(HDR_TO_SDR)
    chain += [f"crop={int(cw) // 2 * 2}:{int(ch) // 2 * 2}:{int(cx)}:{int(cy)}",
              f"scale={tw}:{th}:flags=lanczos", f"fps={fps}"]
    if gamma != 1.0:
        chain.append(f"eq=gamma={gamma:.3f}")
    chain.append(GRADE)
    if extra_filters:
        chain.append(extra_filters)
    chain.append("format=yuv420p")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}"]
    if duration:
        cmd += ["-t", f"{duration:.2f}"]
    cmd += ["-i", src]
    if not keep_audio or not m.get("has_audio"):
        cmd += ["-f", "lavfi", "-t", f"{duration or m['duration']:.2f}", "-i", "anullsrc=r=48000:cl=stereo",
                "-map", "0:v:0", "-map", "1:a:0", "-shortest"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0"]
        if audio_gain_db:
            cmd += ["-af", f"volume={audio_gain_db}dB"]
    cmd += ["-vf", ",".join(chain), "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "20",
            "-maxrate", "12M", "-bufsize", "24M", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", dest]
    run(cmd)
    return {"duration": video_meta(dest)["duration"]}
