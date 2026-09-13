# Atlas Cloud 사용법 — 제오경 「염원」 작업 기준

2026-09-13 · Seedance 2.5 옴니레퍼런스 / 21:9 / 컷당 10초

---

## 0. 한눈에

| 항목 | 값 |
|---|---|
| 생성 엔드포인트 | `POST https://api.atlascloud.ai/api/v1/model/generateVideo` |
| 조회 엔드포인트 | `GET https://api.atlascloud.ai/api/v1/model/prediction/{id}` |
| 에셋 등록 | `POST https://console.atlascloud.ai/api/v1/sd/assets` ← **호스트가 다름** |
| 인증 | `Authorization: Bearer $ATLASCLOUD_API_KEY` |
| 모델 (다중 레퍼런스) | `bytedance/seedance-2.5/reference-to-video` |
| 모델 (첫 프레임 고정) | `bytedance/seedance-2.5/image-to-video` |

## 1. 어느 엔드포인트를 쓸 것인가

두 개를 섞어 써야 한다. 컷 성격에 따라 갈린다.

| 컷 성격 | 엔드포인트 | 예 |
|---|---|---|
| **첫 프레임을 그림으로 못박아야** 함 | `image-to-video` | S02 — @Image1(안개)이 반드시 0프레임 |
| 여러 레퍼런스로 **룩·구조만** 잡음 | `reference-to-video` | 용두사 세트 컷들, 배 룩 유지 |

`reference-to-video`는 레퍼런스를 "참고"로 쓰지 첫 프레임을 잠그지 않는다. S02처럼
0초 화면이 확정된 컷을 여기에 넣으면 안개 이미지가 그냥 분위기 참고로 소비된다.

`omni_reference_task_type`은 우리 용도에선 `"reference"`로 고정한다 (기본 `auto`는
입력 구성을 보고 edit/extend로 잘못 라우팅될 수 있다).

## 2. 이 프로젝트 고정 파라미터

```json
{
  "model": "bytedance/seedance-2.5/reference-to-video",
  "omni_reference_task_type": "reference",
  "ratio": "21:9",
  "duration": 10,
  "resolution": "720p",
  "output_format": "mp4",
  "generate_audio": true,
  "watermark": false
}
```

- **`ratio`를 반드시 명시**한다. 기본값이 `adaptive`라 레퍼런스 이미지의 비율을
  따라가 버린다. 우리 플레이트가 21:9니 우연히 맞을 수도 있지만, 안 맞으면
  레이아웃 계산이 전부 무너진다.
- `duration`은 10. S02만 13.
- `resolution`은 탐색 `720p` → 확정 `1080p` (3장 참조).
- `watermark`는 기본 false지만 명시해 두는 편이 안전하다.

## 3. 해상도 — 네이티브와 업스케일 구분

Seedance 2.5가 **네이티브로 만드는 건 480p / 720p / 1080p 셋뿐**이다.
나머지는 전부 사후 업스케일이다.

| 값 | 실제 동작 |
|---|---|
| `480p` `720p` `1080p` | 네이티브 생성 |
| `1080p-sr` | 720p 생성 후 FlashVSR 업스케일 |
| `1080p-esr` | 720p 생성 후 Atlas 자체 강화 |
| `4k-esr` | **네이티브 1080p에서 출발**해 4K로 |

`4k-esr`가 1080p에서 출발한다는 점이 중요하다. 캔버스가 5320×1600이라
1080p(21:9 = 2560×1097)로도 모자라니, 확정 컷은 `4k-esr`가 현실적인 종착지다.

**단가** (2026-08~09 공개 요율)

| 해상도 | $/초 | 10초 1컷 |
|---|---|---|
| 480p | $0.14 | $1.40 |
| 720p | $0.30 | $3.00 |
| 1080p 네이티브 | **$0.59** ← 20% 할인가, **09-17 만료** | $5.90 |
| 1080p 네이티브 (09-18~) | 약 $0.74 | 약 $7.38 |
| 4k-esr | 약 $1.70 | 약 $17.00 |

> **정정** — EvoLink뿐 아니라 **Atlas의 1080p 할인도 09-17에 끝난다**. 09-18 이후
> 두 곳의 1080p 단가는 $0.74 대 $0.739로 사실상 같아진다. Atlas를 택하는 근거는
> 가격이 아니라 **레퍼런스 입력이 과금에 잡히지 않는다**는 점 하나다.
>
> `1080p-esr`(720p 소스 강화) 단가는 아직 확인 못 했다. 네이티브 1080p보다 싸면
> 확정 컷 비용을 크게 줄일 수 있으니 콘솔 계산기에서 먼저 찍어 볼 것.

## 4. 레퍼런스 넣는 법

| 종류 | 인라인 | 사전 등록 |
|---|---|---|
| 이미지 | URL · Base64 · `asset://` | 선택 |
| **영상** | URL · `asset://` | **Base64 불가** |
| 오디오 | URL · Base64 · `asset://` | 선택 |

제약: 이미지 0–30장 (300–6000px, 비율 0.4–2.5, 30MB 이하) · 영상 0–10개
(합계 30초 이하, 개당 2–30초, 200MB 이하) · 오디오 0–10개 (합계 30초 이하).

### 에셋 라이브러리를 쓰는 이유

25컷을 각 5~8버전씩 돌리면 같은 플레이트를 수백 번 올리게 된다. 한 번 등록해
`asset://<id>`로 부르면 업로드·검증이 매번 반복되지 않는다.

```bash
# 등록
curl -X POST "https://console.atlascloud.ai/api/v1/sd/assets" \
  -H "Authorization: Bearer $ATLASCLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type":"Video","url":"https://your-host.com/S02_blockout.mp4"}'

# Active 될 때까지 폴링
curl "https://console.atlascloud.ai/api/v1/sd/assets/<asset_id>" \
  -H "Authorization: Bearer $ATLASCLOUD_API_KEY"
```

**공개 URL만 받는다.** 로그인이나 JS 렌더링이 필요한 주소는 안 된다. 우리는 이미
GitHub Pages로 보드를 서비스하고 있으니 `storyboard_v3/images/` 아래 파일은
그대로 쓸 수 있다. 영상은 레포에 올리거나 별도 공개 호스팅이 필요하다.

## 5. 프롬프트의 @ 문법

`reference_images` 배열의 **순서가 곧 번호**다.

```
reference_images[0] → @Image1
reference_images[1] → @Image2
reference_videos[0] → @Video1
reference_audios[0] → @Audio1
```

S02 프롬프트가 이미 `Use @Image1 as the first frame.` / `@Image2 defines how the
ship must look` 로 쓰여 있으니, 배열에 **안개 → 배** 순으로 넣으면 그대로 맞는다.
순서를 바꾸면 프롬프트가 통째로 어긋난다.

## 6. 요청 예시 — S02

첫 프레임을 잠가야 하므로 `image-to-video`를 쓴다.

```bash
curl -X POST "https://api.atlascloud.ai/api/v1/model/generateVideo" \
  -H "Authorization: Bearer $ATLASCLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bytedance/seedance-2.5/image-to-video",
    "prompt": "<S02_v2v_프롬프트_v1.md 4장 본문 그대로>",
    "reference_images": [
      "https://exsucut.github.io/chungju_mediaart/storyboard_v3/images/S02_v2v_레퍼런스_A_안개_첫프레임.png",
      "https://exsucut.github.io/chungju_mediaart/storyboard_v3/images/S02_v2v_레퍼런스_B_배_룩.png"
    ],
    "ratio": "21:9",
    "duration": 13,
    "resolution": "720p",
    "generate_audio": true,
    "watermark": false
  }'
```

응답은 `{"code":200,"data":{"id":"<prediction_id>"}}`. 그 id로 조회 엔드포인트를
`completed` / `succeeded` / `failed` 가 뜰 때까지 폴링하면 `outputs`에 영상 URL이 온다.

## 7. 배치 실행

`source/atlas/atlas_gen.py` 를 같이 넣어 뒀다.

```bash
export ATLASCLOUD_API_KEY=...
python source/atlas/atlas_gen.py source/atlas/jobs_예시.json --out out/r1 --workers 4
```

- `jobs_*.json` 에 컷별 프롬프트·레퍼런스·버전 수를 적는다.
- 제출 → 폴링 → 다운로드까지 하고 `_manifest.json` 에 요청/응답을 남긴다.
- `--dry-run` 으로 **예상 비용만 먼저 계산**할 수 있다.

> 이 스크립트는 API 키가 없어 실제 호출로는 검증하지 못했다. 문서에 적힌 스키마대로
> 짰으니 첫 1컷을 `--workers 1` 로 돌려 응답 형태를 확인한 뒤 전체를 돌릴 것.

## 8. 비용 관리 3가지

1. **2단 운용.** 버전 비교는 `720p`($3.00), 확정된 25컷만 `1080p` 또는 `4k-esr`로
   재생성. 전량 1080p 대비 33~43% 절감.
2. **영상 레퍼런스는 잘라서 넣는다.** Atlas는 레퍼런스 입력을 과금하지 않지만
   합계 30초 제한이 있고, 긴 레퍼런스는 결과를 원본 페이싱 쪽으로 끌어당긴다.
3. **`--dry-run` 을 먼저 돌린다.** 25컷 × 버전 수 × 해상도로 총액이 바로 나온다.

## 9. 주의

- **`ratio` 미지정 시 `adaptive`** — 21:9를 매번 명시.
- **에셋 호스트가 다르다** — 등록은 `console.`, 생성은 `api.`.
- **영상 레퍼런스는 Base64 불가** — 반드시 공개 URL이나 `asset://`.
- 09-17에 1080p 할인 만료. 확정 컷 중 일부라도 그 전에 뽑아 둘 수 있으면 컷당
  $1.48을 아낀다.
