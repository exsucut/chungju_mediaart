#!/usr/bin/env python3
"""Atlas Cloud - Seedance 2.5 배치 생성기 (제오경 「염원」)

    export ATLASCLOUD_API_KEY=...
    python atlas_gen.py jobs.json --out out/r1 --workers 4
    python atlas_gen.py jobs.json --dry-run          # 비용만 계산

jobs.json 형태는 jobs_예시.json 참조.
API 문서 스키마대로 작성했으나 실제 호출로 검증하지 못했다.
첫 실행은 --workers 1 로 1컷만 돌려 응답 형태를 확인할 것.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

API   = "https://api.atlascloud.ai/api/v1/model"
CONSOLE = "https://console.atlascloud.ai/api/v1/sd"

# 2026-08~09 공개 요율 ($/초). 1080p 는 09-17 만료 20% 할인가.
RATE = {"480p": 0.14, "720p": 0.30, "1080p": 0.59, "4k-esr": 1.70}

DEFAULTS = {            # 이 프로젝트 고정값
    "ratio": "21:9",    # 미지정 시 adaptive 로 떨어지므로 반드시 명시
    "duration": 10,
    "resolution": "720p",
    "output_format": "mp4",
    "generate_audio": True,
    "watermark": False,
}


def _req(url, method="GET", body=None, key=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {key}")
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {url}\n{e.read().decode()[:800]}") from None


def register_asset(url, kind, key, poll=5, limit=600):
    """영상·오디오는 사전 등록이 필요하다. asset://<id> 를 돌려준다."""
    got = _req(f"{CONSOLE}/assets", "POST", {"type": kind, "url": url}, key)
    aid = (got.get("data") or got).get("id")
    if not aid:
        raise RuntimeError(f"asset id 없음: {got}")
    t0 = time.time()
    while time.time() - t0 < limit:
        st = _req(f"{CONSOLE}/assets/{aid}", key=key)
        s = str((st.get("data") or st).get("status", "")).lower()
        if s in ("active", "ready", "succeeded", "completed"):
            return f"asset://{aid}"
        if s in ("failed", "error"):
            raise RuntimeError(f"에셋 처리 실패 {aid}: {st}")
        time.sleep(poll)
    raise TimeoutError(f"에셋 {aid} 가 {limit}초 안에 Active 되지 않음")


def build(job):
    """job → 요청 본문. 첫 프레임을 잠가야 하면 model 에 image-to-video 를 쓴다."""
    b = {k: job.get(k, v) for k, v in DEFAULTS.items()}
    b["model"] = job.get("model", "bytedance/seedance-2.5/reference-to-video")
    b["prompt"] = job["prompt"]
    if b["model"].endswith("reference-to-video"):
        # auto 는 입력 구성에 따라 edit/extend 로 잘못 라우팅될 수 있다
        b["omni_reference_task_type"] = job.get("omni_reference_task_type", "reference")
    for f in ("reference_images", "reference_videos", "reference_audios"):
        if job.get(f):
            b[f] = job[f]          # 배열 순서 = 프롬프트의 @Image1, @Video1 ...
    if job.get("seed") is not None:
        b["seed"] = job["seed"]
    return b


def submit(body, key):
    got = _req(f"{API}/generateVideo", "POST", body, key)
    pid = (got.get("data") or got).get("id")
    if not pid:
        raise RuntimeError(f"prediction id 없음: {got}")
    return pid


def wait(pid, key, poll=6, limit=1800):
    t0 = time.time()
    while time.time() - t0 < limit:
        got = _req(f"{API}/prediction/{pid}", key=key)
        d = got.get("data") or got
        s = str(d.get("status", "")).lower()
        if s in ("completed", "succeeded"):
            return d
        if s in ("failed", "error", "canceled", "cancelled"):
            raise RuntimeError(f"생성 실패 {pid}: {json.dumps(d)[:600]}")
        time.sleep(poll)
    raise TimeoutError(f"{pid} 가 {limit}초 안에 끝나지 않음")


def urls_of(d):
    out = d.get("outputs") or d.get("output") or d.get("result")
    if isinstance(out, str):
        return [out]
    if isinstance(out, dict):
        out = out.get("video") or out.get("videos") or list(out.values())
    if isinstance(out, list):
        return [u if isinstance(u, str) else (u.get("url") or u.get("video")) for u in out]
    return []


def download(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(url, timeout=600) as r, open(path, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return path


def expand(jobs):
    """versions: 3 이면 같은 job 을 3개로 펼친다."""
    out = []
    for j in jobs:
        for i in range(int(j.get("versions", 1))):
            k = dict(j)
            k.pop("versions", None)
            k["name"] = f"{j['name']}_v{i+1}"
            if j.get("seed") is not None:
                k["seed"] = int(j["seed"]) + i
            out.append(k)
    return out


def cost(jobs):
    tot, unknown = 0.0, []
    for j in jobs:
        res = j.get("resolution", DEFAULTS["resolution"])
        dur = j.get("duration", DEFAULTS["duration"])
        if res in RATE:
            tot += RATE[res] * dur
        else:
            unknown.append(res)
    return tot, sorted(set(unknown))


def run_one(job, key, outdir):
    body = build(job)
    pid = submit(body, key)
    d = wait(pid, key)
    files = []
    for n, u in enumerate(urls_of(d)):
        if u:
            ext = body.get("output_format", "mp4")
            files.append(download(u, os.path.join(
                outdir, f"{job['name']}{'' if n == 0 else f'_{n}'}.{ext}")))
    return {"name": job["name"], "prediction_id": pid, "request": body, "files": files}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jobs")
    p.add_argument("--out", default="out")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    jobs = expand(json.load(open(a.jobs, encoding="utf-8")))
    total, unknown = cost(jobs)
    print(f"작업 {len(jobs)}건 · 예상 ${total:,.2f}")
    if unknown:
        print(f"  단가 미등록 해상도(비용 미포함): {', '.join(unknown)}")
    if a.dry_run:
        for j in jobs:
            print(f"  {j['name']:28s} {j.get('resolution', DEFAULTS['resolution']):8s} "
                  f"{j.get('duration', DEFAULTS['duration'])}s")
        return

    key = os.environ.get("ATLASCLOUD_API_KEY")
    if not key:
        sys.exit("ATLASCLOUD_API_KEY 가 설정되지 않았다")

    os.makedirs(a.out, exist_ok=True)
    done, failed = [], []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, j, key, a.out): j for j in jobs}
        for f in as_completed(futs):
            j = futs[f]
            try:
                r = f.result()
                done.append(r)
                print(f"  ✓ {r['name']} → {', '.join(r['files']) or '(파일 없음)'}")
            except Exception as e:
                failed.append({"name": j["name"], "error": str(e)})
                print(f"  ✗ {j['name']}: {e}")

    man = os.path.join(a.out, "_manifest.json")
    json.dump({"ok": done, "failed": failed}, open(man, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n성공 {len(done)} · 실패 {len(failed)} · 기록 {man}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
