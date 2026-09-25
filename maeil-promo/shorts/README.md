# 매일신문 숏폼 — 「피드 말고, 페이퍼.」

48초 · 1080×1920(9:16) · 30fps · `maeil_shorts.mp4` — 릴스·쇼츠·틱톡용 2030 타깃 버전

> 실사 사진 사이트가 작업 환경에서 막혀 있어서, 모든 장면을 **three.js 3D CG(PBR 재질·부드러운 그림자·피사계 심도·필름 그레인)** 로 직접 만들었습니다.
> 실제 사진이 생기면 `photos/<슬롯>.jpg` 로 넣기만 하면 해당 구간은 사진이 CG 위에 덮입니다.

※ 공식 CI 대신 글자로 조판한 제호를 쓴 **시안**입니다. 영상 속 신문 지면의 기사 문구는 광고 카피로 새로 쓴 것입니다.

## 구성

| 시간 | 화면 (CG) | 자막 | 사운드 |
|---|---|---|---|
| 0:00–0:07 | 밤, 이불 위에서 빛나는 폰 — 점점 빨라지는 피드 → 카메라가 멀어지며 폰만 덩그러니 | 솔직히, 신문 **누가 봐?** / 하루 종일 **스크롤**, 스크롤. / 근데 오늘 본 거, **하나라도** 기억나? | 차가운 비트 + 알림음 |
| 0:07.5 | 암전 | **로그아웃.** 잠깐, 화면 끄고. | 전부 끊기고 '딸깍' |
| 0:08–0:16 | 아침 햇살 · 블라인드 그림자 — 필름 카메라와 인화 사진 / 돌아가는 LP / 만년필로 필사 | **필카** 찍고 · **LP** 듣고 · **필사**하는 우리. `#텍스트힙 #고잉아날로그` | 따뜻한 로파이 + LP 잡음 |
| 0:16–0:25 | 김 나는 커피 → 초점이 신문으로 → 제호 「매일신문」 | 느린 게 힙한 이유? **진짜라서.** / 다음 텍스트힙은, **신문.** | 빌드업 → 임팩트 |
| 0:25–0:30 | 신문 활자 접사 (얕은 심도) | 스크롤은 흘러가도 활자는 **남는다.** | |
| 0:30–0:35 | 밤의 도시 항공샷, 타워와 자동차 불빛 | 알고리즘은 **네가 좋아할 걸**, 신문은 **우리 동네 진짜 이야기**를. | |
| 0:35–0:40 | 아침 해가 지나가는 테이블 위의 신문 | 1946년부터, 대구·경북의 아침을 기록한 **80년** 차 신문 | |
| 0:40–0:48 | 엔딩 | **피드 말고, 페이퍼.** 매일신문 · 오늘 아침, 한 장 넘겨볼래? | 마무리 화음 |

## 사실 근거

- 숏폼 뉴스 이용률 11.1% → 22.9% (한국언론진흥재단 언론수용자 조사) — [한국기자협회](https://m.journalist.or.kr/m/m_article.html?no=60017)
- 텍스트힙·고잉 아날로그 트렌드 — [KB의 생각](https://kbthink.com/main/living-finance/consumption-life/mz-consumption/text-hip.html), [경향신문](https://www.khan.co.kr/en/article/202604211134007/), [농민신문](https://www.nongmin.com/article/20260204500412)
- 종이 읽기 이해도: Delgado 외(2018) 54편 연구·171,055명 메타분석 — [ResearchGate](https://www.researchgate.net/publication/330854760_Don't_throw_away_your_printed_books_A_meta-analysis_on_the_effects_of_reading_media_on_reading_comprehension)
- 1946년 창간 — [대구역사문화대전](https://www.grandculture.net/daegu/toc/GC40005838)

## 다시 만들기

```bash
cd maeil-promo
./fetch_fonts.sh && ./shorts/fetch_vendor.sh          # 폰트, three.js (git 제외)
ln -sf "$(npm root -g)" node_modules                  # 전역 playwright 연결
SCENE=shorts/scene.html node render.mjs --stills 2,10,23   # 스틸 확인 → frames/
JOBS=4 ./shorts/render_parallel.sh                    # 병렬 렌더 + 사운드 → shorts/maeil_shorts.mp4
```

- `scene.html` — 자막·컷 타이밍(`data-in`/`data-out`, 초), 엔딩 카드
- `cg.js` — 3D 세트(밤의 폰 / 아침 테이블 / 밤의 도시)와 샷별 카메라·초점(`SHOTS`)
- `audio.py` — 96BPM 로파이 비트 합성
- `fetch_photos.py` — 네트워크가 허용되면 Unsplash/Wikimedia 무료 라이선스 사진을 받아 `photos/` 에 넣는 도구 (선택)
