# 온라인 대나무숲

쓰면 사라지는 익명 외침 공간. 설계안(`온라인 대나무숲 — 프로그램 설계안`)의 1단계(혼자 외치기)를 HTML 한 파일로 구현했다.

## 파일

| 파일 | 용도 |
|---|---|
| `index.html` | 서비스 전체. 입구 → 숲길 → 빈터 → 나가기, 위기 안내, 설정, 관리자(`#admin`) |
| `og.png` | 공유 미리보기 1200×630 |
| `icon-512.png` `icon-192.png` `apple-touch-icon.png` `favicon-32.png` | 아이콘 |

외부 파일 의존 없음. 폰트(나눔명조·Noto Sans KR)만 Google Fonts에서 불러온다. 배경음은 Web Audio로 합성한다.

## 동작 모드

- **데모 모드(기본)**: `CONFIG.FIREBASE`가 `null`이면 서버 없이 동작한다. 흔들림 횟수는 이 기기의 localStorage에만 쌓이고, 같은 기기의 다른 탭과만 흔들림 신호를 주고받는다. 입구의 다른 사람들과 이따금 들리는 '누군가 외쳤어요'는 이 모드에서는 기기 안에서 흉내 낸 것이다.
- **Firebase 모드**: `index.html` 상단 `CONFIG.FIREBASE`에 프로젝트 설정을 넣으면 익명 로그인 뒤 아래 구조로 동작한다. 갓바위와 별개의 새 프로젝트를 쓴다.

| 저장소 | 경로 | 내용 |
|---|---|---|
| Realtime DB | `forest/{channel}/presence/{uid}` | nickRole, hat, zone, t (접속 끊기면 삭제) |
| Realtime DB | `forest/{channel}/pulse` | 마지막 흔들림 신호 1건을 덮어씀 (t, uid, role). 쌓이지 않음 |
| Firestore | `shakes/{uid}_{day}` | count, day, nickRole, hours.{h} |
| Firestore | `stats/{day}` | totalShakes, crisisHints, reports (클라이언트는 이 문서만 읽음) |
| Firestore | `reports/{auto}` | reason, day (2단계 흐릿 모드용) |

Functions 없이도 돌아가도록 클라이언트가 `stats/{day}`를 increment 한다. 보안 규칙에서는 `shakes`·`stats`에 increment만 허용하고, 어떤 컬렉션에도 본문 필드를 두지 않는다.

## 설계안 대비 구현 범위

- 1단계 전부: 역할 닉네임, 꾹 눌러 걷기(약 36초, 걸을수록 다른 사람·소리가 줄어듦), 100자 외치기, 글자가 바람에 흩어짐(8초 이내), 1초 뒤 숲 흔들림, '숲이 들었어요', 30초 간격, 오늘의 흔들림 수, 흔적 카드(내용 없음), '우리가 저장하는 것', 시즌 문구(12월·1월·수능 뒤), 심야 모드(0~5시), 월하서재 연계(나가기 화면 1곳, 위기 세션 제외)
- 안전 설계: 위기 키워드는 기기 안에서만 검사하고 '횟수'만 센다. 강한 표현은 번호를 바로 펼치고, '죽겠다' 같은 관용구는 안내만 띄우고 번호를 접어 둔다. 학생 역할이면 1388을 맨 위로 올린다.
- 2단계('흐릿하게 두고 가기', 신고)는 넣지 않았다. `Net.report()`만 미리 두었다.

## 배포

별도 저장소로 옮길 때는 이 폴더의 파일을 저장소 루트에 두고, `index.html`의 `og:url`·`og:image`·`twitter:image`와 `CONFIG.REPO_URL`만 새 주소로 바꾸면 된다.
