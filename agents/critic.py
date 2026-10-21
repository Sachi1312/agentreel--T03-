"""Agent 7 - Critic / QA: explicit, checkable rules. Returns pass/fail + reasons + which agent must fix each failure."""
import json, re, subprocess
from pathlib import Path
from core import config as C
from core.rag import tokenize

PHONE = re.compile(r"\b\d{4,}\b")
DOMAIN = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:gov|nic|ac|edu|org|com|co|in)(?:\.[a-z]{2})?\b", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def contacts_in(text):
    found = set(PHONE.findall(text)) | {m.group(0).lower() for m in DOMAIN.finditer(text)} | set(EMAIL.findall(text.lower()))
    return {c for c in found if c}


def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))
    return i, tp


def run(plan, brief, facts_doc, script, storyboard, assets, edit, outdir, srt_path):
    checks = []

    def chk(cid, ok, detail, owner, **extra):
        checks.append(dict(id=cid, passed=bool(ok), detail=detail, owner=owner, **extra))

    facts = {f["id"]: f for f in facts_doc["facts"]}
    fact_text = " ".join(f["claim"] for f in facts_doc["facts"])
    from core import rag
    all_text = " ".join(c["claim"] for c in rag.ingest(C.ROOT / "data"))
    allowed_contacts = contacts_in(all_text)

    # 1 fact grounding (every spoken line)
    bad = []
    for l in script["lines"]:
        if l["role"] == "hook" and not l["fact_ids"]:
            continue
        cited = " ".join(facts[i]["claim"] for i in l["fact_ids"] if i in facts)
        miss = [i for i in l["fact_ids"] if i not in facts]
        lt = set(tokenize(l["text"]))
        cover = len(lt & set(tokenize(cited))) / max(len(lt), 1)
        if miss or not l["fact_ids"] or cover < 0.6 or not contacts_in(l["text"]) <= contacts_in(cited):
            bad.append({"line": l["id"], "fact_ids": l["fact_ids"], "coverage": round(cover, 2)})
    chk("fact_grounding", not bad, f"{len(script['lines'])} lines checked against facts.json" + (f"; failing: {bad}" if bad else ""),
        "scriptwriter", avoid_fact_ids=[i for b in bad for i in b["fact_ids"]])

    # 2 contacts verified (script + on-screen text + end card CTA)
    screen = " ".join(s["on_screen_text"] for s in storyboard["shots"])
    used = contacts_in(" ".join(l["text"] for l in script["lines"]) + " " + screen)
    unverified = sorted(used - allowed_contacts)
    chk("contacts_verified", not unverified, f"contacts used: {sorted(used)}; not in fact sheet: {unverified}", "scriptwriter")

    # 2b no unfilled placeholders / template text anywhere that is spoken or shown
    shown = " ".join(l["text"] for l in script["lines"]) + " " + screen
    ph = re.findall(r"<[^>]+>|\bTODO\b|PLACEHOLDER|lorem ipsum", shown, re.I)
    chk("no_placeholders", not ph, f"placeholder text found: {ph}" if ph else "no template/placeholder text in spoken or on-screen text", "scriptwriter")

    # 3 must_include / must_avoid
    corpus = (" ".join(l["text"] for l in script["lines"]) + " " + screen).lower()
    mi = [m for m in brief.get("must_include", []) if str(m).lower() not in corpus]
    chk("must_include", not mi, f"missing: {mi}" if mi else "all present", "scriptwriter")
    avoid = [a for a in list(brief.get("must_avoid", [])) + C.DEFAULT_FORBIDDEN if str(a).lower() in corpus]
    chk("must_avoid", not avoid, f"forbidden terms present: {avoid}" if avoid else "none present", "scriptwriter")

    # 4 hook names the topic in first 3 s
    hook = storyboard["shots"][0]
    topic_tokens = set(tokenize(" ".join(plan["subtopics"][:1] + [brief["topic"].split(":")[0]])))
    first = set(tokenize(script["lines"][0]["text"] + " " + hook["on_screen_text"]))
    first_vo_end = min(assets["timings"][script["lines"][0]["id"]][1], 99)
    chk("hook_topic", bool(topic_tokens & first), f"topic words {sorted(topic_tokens & first)} in hook; hook caption/headline visible from t=0.25s", "scriptwriter")

    # 5 end card
    last = storyboard["shots"][-1]
    cta_ok = last["visual"] == "endcard" and contacts_in(last["on_screen_text"]) <= allowed_contacts and bool(contacts_in(last["on_screen_text"]))
    lay = json.loads((Path(outdir) / "layout_report.json").read_text())
    kinds = {i["kind"] for i in lay["items"] if i["shot"] == last["id"]}
    disc = any(C.DISCLOSURE.split("—")[0].strip() in " ".join(i["text"] for i in lay["items"] if i["kind"] == "disclosure") for _ in [0])
    chk("end_card", cta_ok and {"cta", "logo"} <= kinds and disc, f"endcard CTA verified={cta_ok}; elements rendered={sorted(kinds)}; disclosure rendered={disc}", "editor")

    # 6 safe zones + caption size (measured from rendered layout)
    top, bot = lay["safe"]
    viol = [i for i in lay["items"] if i["bbox"][1] < top or i["bbox"][3] > bot]
    small = [i for i in lay["items"] if i["kind"] == "caption" and i["font_px"] * lay["w"] / 1080 < C.MIN_CAPTION_PX]
    chk("safe_zones_and_caption_size", not viol and not small,
        f"{len(lay['items'])} text boxes measured, safe y-range {top}-{bot}; violations={len(viol)}, undersized captions={len(small)}", "editor")

    # 7 every script line has a shot; shot count
    n = len(storyboard["shots"])
    covered = {s["script_line"] for s in storyboard["shots"]}
    chk("storyboard", 6 <= n <= 12 and all(l["id"] in covered for l in script["lines"]), f"{n} shots; all script lines covered={all(l['id'] in covered for l in script['lines'])}", "storyboarder")

    # 8 technical specs on the real file
    final = Path(edit["final"])
    pr = ffprobe(final)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next(s for s in pr["streams"] if s["codec_type"] == "audio")
    dur = float(pr["format"]["duration"])
    W, H = C.FORMATS[plan["format"]]
    size_mb = final.stat().st_size / 1e6
    over = dur > C.MAX_DUR
    chk("duration", C.MIN_DUR <= dur <= C.MAX_DUR, f"{dur:.2f}s (allowed {C.MIN_DUR}-{C.MAX_DUR}s, brief target {plan['duration_s']}s)", "scriptwriter",
        max_words=int(script["word_count"] * (C.MAX_DUR - 3) / dur) if over else None,
        min_words=int(script["word_count"] * (C.MIN_DUR + 3) / dur) + 1 if dur < C.MIN_DUR else None)
    chk("resolution", (v["width"], v["height"]) == (W, H), f"{v['width']}x{v['height']} (need {W}x{H})", "editor")
    fr = v["r_frame_rate"].split("/")
    chk("frame_rate", float(fr[0]) / float(fr[1]) == C.FPS and v["avg_frame_rate"] == v["r_frame_rate"], f"{v['r_frame_rate']} constant", "editor")
    chk("video_codec", v["codec_name"] == "h264" and v["profile"] == "High" and v["pix_fmt"] == "yuv420p", f"{v['codec_name']} {v['profile']} {v['pix_fmt']}", "editor")
    br = int(a.get("bit_rate", 0)) / 1000
    chk("audio_codec", a["codec_name"] == "aac" and int(a["sample_rate"]) == 48000 and a["channels"] == 2 and 128 <= br <= 192,
        f"{a['codec_name']} {a['sample_rate']}Hz {a['channels']}ch {br:.0f}kbps", "editor")
    chk("file_size", size_mb <= C.MAX_FILE_MB, f"{size_mb:.1f} MB (max {C.MAX_FILE_MB})", "editor")
    chk("container_name", final.suffix == ".mp4" and re.match(r"^T\w+_[A-Z]\d+_final\.mp4$", final.name) is not None, final.name, "editor")
    I, tp = loudness(final)
    off = I - C.TARGET_LUFS
    chk("loudness", abs(off) <= C.LUFS_TOL and tp <= C.MAX_TRUE_PEAK, f"integrated {I:.1f} LUFS (target {C.TARGET_LUFS}±{C.LUFS_TOL}), true peak {tp:.1f} dBTP (max {C.MAX_TRUE_PEAK})",
        "editor", lufs_offset=round(-off, 2))
    chk("subtitles_srt", Path(srt_path).exists() and Path(srt_path).stat().st_size > 20, f"{srt_path}", "asset_generator")

    ok = all(c["passed"] for c in checks)
    return {"passed": ok, "checks": checks, "measured": {"duration_s": round(dur, 2), "lufs": I, "true_peak": tp, "size_mb": round(size_mb, 2)}}
