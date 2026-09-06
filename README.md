# 염원 — 주성의 돛대 · 스토리보드

2026 청주 국가유산 미디어아트 / 제오경 「염원 – 주성의 돛대」
5분 · 25샷 · 21:9 생성 후 좌 16:9 / 우 4:3 크롭 운용

`index.html` 하나와 `images/` 폴더로 된 정적 사이트입니다. GitHub Pages로 그대로 배포됩니다.

---

## 1. 저장소 만들고 올리기

GitHub에서 새 저장소를 만듭니다 (예: `jusung-storyboard`). **README 체크는 하지 마세요** — 이미 있습니다.

그다음 이 폴더에서:

```bash
git remote add origin https://github.com/<아이디>/<저장소이름>.git
git branch -M main
git push -u origin main
```

## 2. Pages 켜기

저장소 → **Settings → Pages**
- Source: `Deploy from a branch`
- Branch: `main` / `/ (root)` → Save

1~2분 뒤 `https://<아이디>.github.io/<저장소이름>/` 에서 열립니다.

## 3. 샷별 코멘트 켜기 (giscus)

각 샷 카드의 **코멘트** 버튼은 giscus로 동작합니다. GitHub Discussions에 샷마다 별도 스레드가 생기고,
누구나 GitHub 계정으로 의견을 남기고 **본인 글은 직접 수정·삭제**할 수 있습니다.

1. 저장소 → **Settings → General → Features → Discussions** 체크
2. https://github.com/apps/giscus 에서 **Install** → 이 저장소 선택
3. https://giscus.app 접속 → 저장소 이름 입력 →
   - 페이지↔Discussion 연결: **특정 term 사용** (Discussion title contains a specific term)
   - Discussion 카테고리: **Announcements** 또는 **General**
4. 화면 아래 생성된 코드에서 네 값을 복사
5. 이 폴더에 **`giscus.json`** 파일을 만들고 값을 채웁니다
   (`giscus.example.json` 을 복사해서 쓰면 됩니다)

```json
{
  "repo": "아이디/저장소이름",
  "repoId": "R_kg...",
  "category": "General",
  "categoryId": "DIC_kw..."
}
```

6. 프로젝트 폴더의 **`배포.command`** 를 더블클릭하면 재빌드 + 푸시까지 한 번에 됩니다.

> 설정을 `index.html` 이 아니라 `giscus.json` 에 두었기 때문에, 보드를 몇 번을 다시 만들어도 값이 유지됩니다.

설정 전에는 코멘트 버튼을 눌러도 안내 문구만 뜹니다. 보드 자체는 정상 작동합니다.

---

## 갱신하는 법

프로젝트 폴더의 **`배포.command` 를 더블클릭**하면 끝입니다.
보드를 다시 만들고, 바뀐 게 있으면 커밋해서 푸시하고, 배포 주소까지 알려줍니다.

터미널에서 메시지를 직접 붙이고 싶으면:

```bash
"/Users/jojeong-ung/Desktop/청주 국가유산 프로잭트/배포.command" "S7 폭우 톤 수정"
```

샷을 추가·수정하려면 `../storyboard_v3/shots.json` 을 고치고 배포하면 됩니다.
타임라인과 밝기 곡선은 `len`·`tone` 값에서 자동 계산됩니다.

### 폴더 구조

```
청주 국가유산 프로잭트/
├ 배포.command          ← 더블클릭하면 재빌드 + 푸시
├ storyboard_v3/        원본
│   ├ shots.json        ★ 샷 데이터 — 여기만 고치면 됨
│   ├ images/           원본 해상도 이미지
│   ├ build_board.py    아티팩트용 (이미지 내장 단일 파일)
│   └ build_web.py      웹용 (상대 경로 + giscus)
└ storyboard_web/       ← 이 저장소
    ├ index.html
    ├ images/
    └ giscus.json       코멘트 설정 (재빌드해도 유지)
```

---

## 폴더

```
index.html     보드 (상대 경로로 images/ 참조)
images/        샷 이미지 전 버전 — S##_이름_v#.jpg
```
