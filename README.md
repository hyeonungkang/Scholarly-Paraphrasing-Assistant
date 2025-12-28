# 📝 Paragraph Reviewer

논문 문단을 AI로 분석하고 개선 제안을 제공하는 데스크톱 애플리케이션입니다. Google Gemini API를 활용하여 학술 논문의 품질을 향상시킵니다.

## 🎥 데모 영상

[프로젝트 데모 보기](https://github.com/hyeonungkang/Scholarly-Paraphrasing-Assistant/blob/main/project_demo.mp4)

## ✨ 주요 기능

- **🔄 패러프레이징**: 다양한 스타일로 문단을 재작성하여 더 나은 표현 제안
- **⚠️ 주장 체크**: 과대해석 위험도 분석 및 개선 제안
- **📊 저널 매칭**: 타겟 저널에 맞는 적합도 평가 및 맞춤 수정본 생성
- **🚀 주장 확장**: 연구 방향 제안 및 Next Level 연구 아이디어 제공
- **📚 참고문헌**: Semantic Scholar API를 통한 관련 논문 추천
- **❓ 리뷰어 Q&A**: 리뷰어가 제기할 수 있는 질문 예측 및 긍정적 피드백
- **🌐 자동 번역**: 영어 입력 시 한국어 번역 자동 제공

## 🛠️ 기술 스택

- **UI**: [Flet](https://flet.dev/) - 크로스 플랫폼 Python GUI 프레임워크
- **AI 워크플로우**: [LangGraph](https://langchain-ai.github.io/langgraph/) - AI 워크플로우 오케스트레이션
- **LLM**: [Google Gemini 2.5](https://ai.google.dev/) - 대규모 언어 모델
- **논문 검색**: [Semantic Scholar API](https://www.semanticscholar.org/product/api) - 학술 논문 검색

## 📦 설치 방법

### 사전 요구사항

- Python 3.10 이상
- Google Gemini API 키 ([발급받기](https://makersuite.google.com/app/apikey))
- (선택) Semantic Scholar API 키 ([발급받기](https://www.semanticscholar.org/product/api))

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/paragraph-reviewer.git
cd paragraph-reviewer
```

### 2. 가상환경 생성 및 활성화

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# .env.example 파일을 복사하여 .env 파일 생성
cp .env.example .env
# 또는 직접 생성
```

`.env` 파일 내용:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_api_key_here  # 선택적
```

**또는** 애플리케이션 실행 후 **설정** 메뉴에서 API 키를 입력할 수 있습니다.

## 🚀 사용 방법

### 실행

**방법 1: 가상환경 활성화 후 실행 (권장)**

```bash
# Windows
venv\Scripts\activate
python main.py

# macOS/Linux
source venv/bin/activate
python main.py
```

**방법 2: 직접 실행 (가상환경 자동 감지)**

```bash
python main.py
```

애플리케이션이 자동으로 `venv` 폴더를 감지하고 가상환경의 Python으로 재실행합니다.

### 빌드 (실행 파일 생성)

**Windows:**
```bash
pyinstaller ParagraphReviewer.spec
```

**macOS/Linux:**
```bash
pyinstaller ParagraphReviewer.spec
```

빌드된 실행 파일은 `dist/` 폴더에 생성됩니다. 빌드된 실행 파일은 다른 컴퓨터에서도 Python 설치 없이 실행 가능합니다.

### 다른 컴퓨터에서 실행하기

1. **소스 코드로 실행:**
   - 저장소를 클론하고 위의 설치 방법을 따라주세요
   - 가상환경은 각 컴퓨터에서 새로 생성해야 합니다

2. **빌드된 실행 파일 사용:**
   - `dist/` 폴더의 실행 파일을 다른 컴퓨터로 복사
   - API 키는 실행 파일과 같은 폴더에 `.env` 파일로 설정하거나, 애플리케이션 내 설정에서 입력

## 📁 프로젝트 구조

```
paragraph-reviewer/
├── main.py              # 메인 UI (Flet)
├── config.py            # 설정 및 상수
├── storage.py           # 로컬 저장소 관리
├── services.py          # 외부 API 서비스 (Gemini, Semantic Scholar)
├── graph.py             # LangGraph 워크플로우
├── nodes.py             # 개별 분석 노드
├── prompts.py           # 프롬프트 템플릿
├── prompt_generator.py  # 동적 프롬프트 생성
├── requirements.txt     # 의존성 목록
├── ParagraphReviewer.spec  # PyInstaller 빌드 설정
├── icon.ico             # 애플리케이션 아이콘
└── data/                # 로컬 데이터 (저널, 설정, 히스토리)
    ├── journals.json     # 등록된 저널 목록
    ├── settings.json     # 사용자 설정 (API 키 등)
    └── history.json      # 분석 히스토리
```

## 🎯 주요 기능 상세

### 저널 등록

타겟 저널의 **Aims & Scope**를 등록하면, AI가 해당 저널의 심사 기준에 맞춰 분석합니다.

1. **저널 추가** 메뉴로 이동
2. 저널 약어, 전체 이름, Aims & Scope 입력
3. AI가 자동으로 맞춤 프롬프트 생성
4. 분석 시 해당 저널 선택 가능

### 분석 워크플로우

1. **입력**: 분석할 문단을 입력란에 붙여넣기
2. **저널 선택**: (선택사항) 타겟 저널 선택
3. **분석 시작**: Ctrl + Enter 또는 버튼 클릭
4. **결과 확인**: 6가지 탭에서 상세 분석 결과 확인

## 🔒 보안

- API 키는 환경 변수(`.env`) 또는 로컬 설정 파일(`data/settings.json`)에만 저장됩니다
- `.env` 파일과 `data/settings.json`은 `.gitignore`에 포함되어 Git에 커밋되지 않습니다
- 코드에 하드코딩된 API 키는 없습니다

## 🤝 기여하기

이슈 리포트나 풀 리퀘스트를 환영합니다! 프로젝트를 포크하고 개선사항을 제안해주세요.

## 📄 라이선스

이 프로젝트는 [MIT License](LICENSE) 하에 배포됩니다.

## 🙏 감사의 말

- [Google Gemini](https://ai.google.dev/) - 강력한 AI 모델 제공
- [Semantic Scholar](https://www.semanticscholar.org/) - 학술 논문 검색 API
- [Flet](https://flet.dev/) - 훌륭한 크로스 플랫폼 UI 프레임워크
- [LangGraph](https://langchain-ai.github.io/langgraph/) - AI 워크플로우 오케스트레이션

---

**🤣 논문 쓰기 너무 힘들어서 잠깐 딴짓하다가 심심해서 만든 앱입니다. 연구자 여러분 파이팅! 🦾📚**
