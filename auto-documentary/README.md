# 신비한 건축사전 — 완전 자동화 다큐멘터리 파이프라인

건축물에 얽힌 숨겨진 역사를 다루는 5분 분량 다큐멘터리를 **명령어 하나**로 만듭니다.
저작권 등 법적 리스크를 원천 차단하고, 팩트 체크를 자동화하는 데 중점을 두고 설계했습니다.

```bash
python auto_documentary.py --topic "여의도 국회의사당 돔 지붕의 비밀"
```

결과물은 `output/<주제>/` 폴더에 저장됩니다.

| 파일 | 내용 |
|---|---|
| `[완성본]<주제>.mp4` | 즉시 업로드 가능한 영상 (자막 번인, 내레이션 + BGM) |
| `[완성본]<주제>.srt` | 별도 자막 파일 (유튜브 자막 업로드용) |
| `metadata.json` | SEO 제목·부제·설명·태그·챕터 타임스탬프 |
| `factcheck_report.json` | 교차 검증 결과와 **검증되지 않은 연도·수치 목록** |
| `script.json` / `assets.json` / `narration.json` / `render.json` | 단계별 중간 산출물 |

## 5단계 파이프라인

| 단계 | 모듈 | 역할 | 사용 API |
|---|---|---|---|
| 1 The Brain | `pipeline/stage1_brain.py` | 공공 데이터 수집 → 크로스 체크 → 4막 구조 대본 | 국가유산청 Open API, 한국어 위키백과, Google Gemini (LangChain) |
| 2 The Eyes | `pipeline/stage2_eyes.py` | 퍼블릭 도메인/CC0 자료만 수집, 부족분은 AI B롤 생성 | Wikimedia Commons, 공유마당, Runway Gen-3 |
| 3 The Voice & Sound | `pipeline/stage3_voice.py` | 감정 분석 → 성우 억양·BGM 템포 자동 조절 | ElevenLabs, Epidemic Sound |
| 4 The Editor | `pipeline/stage4_editor.py` | 켄 번스 효과, 오디오 파형 매칭 컷, 자막 번인, 렌더링 | MoviePy, FFmpeg, Whisper(선택) |
| 5 The Publisher | `pipeline/stage5_publisher.py` | SEO 메타데이터 생성, 유튜브 업로드 | YouTube Data API v3 |

### 크로스 체크 알고리즘 (1단계)
- 각 출처 원문에서 **연도(`1974년`)와 수치(`1000톤`, `지하 3층`)** 를 사실 키로 추출합니다.
- **서로 다른 출처 2곳 이상**에서 확인된 키만 `verified=True`가 됩니다. 저장소에 동봉된 편집 노트(`topic_db`)는 단독으로는 검증 출처가 되지 못합니다.
- LLM에는 검증된 사실만 사용하도록 지시하고, 완성 대본을 다시 스캔해 검증되지 않은 연도·수치를 `factcheck_report.json`과 콘솔 경고로 보고합니다.

### 저작권 필터 (2단계)
Wikimedia Commons `extmetadata`의 라이선스 이름이 `Public domain`, `CC0`, `PD-*`인 자료만 다운로드합니다 (`ALLOWED_LICENSE_TOKENS`). CC BY-SA 등 표시 의무가 있는 자료는 제외됩니다.
자료가 없는 섹션은 `"<검색어>, archival documentary B-roll, <무드 스타일>, cinematic 4K"` 프롬프트를 자동 생성해 Runway에 요청하고, 그것도 불가하면 플레이스홀더 카드를 만듭니다.

### 감정 분석 → 음성/음악 (3단계)
대본 문장의 키워드로 `mystery / tragic / grand / neutral` 무드를 판정하고, ElevenLabs `voice_settings`(stability·style)와 BGM 검색 태그·BPM을 무드별로 바꿉니다. Epidemic Sound가 없으면 무드별 코드 드론을 직접 합성해 저작권 걱정 없는 BGM으로 사용합니다.

### 오디오 파형 매칭 컷 (4단계)
섹션별 내레이션을 하나의 트랙으로 합친 뒤 RMS 에너지로 **무음(숨 쉬는) 구간**을 찾고, 장면 전환 시점을 가장 가까운 무음 구간 중앙으로 스냅합니다. 결과는 `render.json`의 `cut_snapped_from` → `start`로 확인할 수 있습니다.

## 설치

```bash
cd auto-documentary
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # API 키 입력
```

FFmpeg는 `imageio-ffmpeg`가 번들 바이너리를 제공하므로 별도 설치가 필요 없습니다.
자막 번인에는 한글 폰트가 필요합니다. 나눔고딕/Noto Sans CJK가 있으면 자동 감지하고, 없으면 `.env`의 `SUBTITLE_FONT`에 경로를 지정하세요 (폰트가 없어도 SRT 파일은 생성됩니다).

## 실행

```bash
# 추천 주제 목록
python auto_documentary.py --list-topics

# 온라인 실행 (키가 있는 API만 사용, 없는 단계는 자동 폴백)
python auto_documentary.py --topic "숭례문 복원"

# API 키·네트워크 없이 파이프라인 검증 (플레이스홀더 이미지 + 무음 내레이션)
python auto_documentary.py --topic "신설동 유령역" --offline --size 1280x720

# 렌더링 후 유튜브 업로드 (client_secret.json 필요, 기본 비공개 업로드)
python auto_documentary.py --topic "여의도 국회의사당 돔 지붕의 비밀" --publish
```

각 단계는 키가 없거나 API가 실패하면 **자동으로 다음 대안으로 내려갑니다**.

| 단계 | 1순위 | 폴백 |
|---|---|---|
| 대본 | Gemini (LangChain) | `topics/recommended_topics.yaml`의 4막 아웃라인 |
| 시각 자료 | 공유마당 → Wikimedia Commons(PD/CC0) | Runway B롤 → 플레이스홀더 카드 |
| 내레이션 | ElevenLabs | 글자 수 기반 타이밍의 무음 트랙 |
| BGM | Epidemic Sound | 무드별 합성 드론 |
| 자막 | Whisper | 대본 문장 길이 비례 타이밍 |

## 주제 추가

`topics/recommended_topics.yaml`에 항목을 추가하면 LLM 없이도 대본 뼈대가 생기고, 위키백과 검색어(`search_terms`), 국가유산청 검색명(`khs_names`), Commons 검색어(`commons_queries`)를 지정할 수 있습니다. 현재 3개 주제가 들어 있습니다.

1. 50년째 굳게 닫힌 신설동 '유령역'
2. 국보 1호 숭례문, 복원의 딜레마
3. 여의도 국회의사당 돔 지붕의 비밀

## 테스트

```bash
python -m pytest tests -q
```

오프라인 end-to-end 테스트가 저해상도로 실제 mp4를 렌더링합니다 (약 15초).

## 알려진 제약

- **외부 API 어댑터 검증 필요**: Wikimedia Commons·위키백과·국가유산청은 공개 API 스펙대로 구현했지만, 공유마당·Epidemic Sound·Runway는 계정별 계약/엔드포인트가 달라 `.env`의 BASE URL과 응답 파서(`parse()`)를 실제 스펙에 맞춰 조정해야 합니다.
- **Gemini 모델명**: `GEMINI_MODEL` 기본값은 설계서대로 `gemini-1.5-pro`입니다. 해당 모델이 종료된 경우 `.env`에서 최신 모델명으로 바꾸세요.
- **렌더링 시간**: 1080p 24fps 5분 영상은 켄 번스 효과를 프레임마다 계산하므로 CPU에서 수 분이 걸립니다. 빠른 확인은 `--size 1280x720`을 권장합니다.
- **팩트 체크 범위**: 크로스 체크는 연도·수치 단위입니다. 인물·사건의 서술 자체는 LLM 프롬프트 제약과 `factcheck_report.json` 검토로 보완해야 하며, 업로드 전 사람이 한 번 확인하는 것을 권장합니다.
