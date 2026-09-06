# 원본 (source)

이 폴더가 작업의 원본입니다. 루트의 `index.html` · `images/` 는 여기서 생성된 결과물입니다.

```
storyboard_v3/
  shots.json        ★ 샷 데이터 — 구성을 바꾸려면 여기만 고치면 됨
  images/           원본 해상도, 전 버전 보존 (S##_이름_v#.jpg)
  build_board.py    아티팩트용 — 이미지를 내장한 단일 HTML
  build_web.py      웹용 — 상대 경로 + Supabase 코멘트 → ../../
reference/          고증·무드보드 자료
lookdev_v1/         룩 개발 10컷
_환경설정/           이관 문서 + sd25-pe 스킬
```

## 빌드

```bash
cd source/storyboard_v3
python3 build_board.py     # → board.html (git 제외됨, 13MB)
python3 build_web.py       # → 저장소 루트의 index.html + images/
```

`build_web.py` 는 출력 경로가 `~/Documents/GitHub/chungju_mediaart` 로 고정돼 있습니다.
다른 위치에 clone 했다면 그 파일 상단의 `OUT` 을 고쳐 주세요.

## 주의

- **발주처 원본 PDF는 이 저장소에 없습니다.** 공개 저장소라 제외했습니다
- `build_*.py` 는 macOS 전용 `sips` 를 씁니다. Windows/Linux 에서는 Pillow 등으로 교체 필요
- 이관 절차는 `_환경설정/데스크톱_이관.md` 참고
