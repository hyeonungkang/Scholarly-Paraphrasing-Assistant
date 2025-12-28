import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-lite"  # 2.5 Flash Lite
GEMINI_PRO_MODEL = "gemini-2.5-pro"  # 저널 등록 시 사용
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")  # 선택적

# 파일 경로
DATA_DIR = "data"
JOURNALS_FILE = f"{DATA_DIR}/journals.json"
SETTINGS_FILE = f"{DATA_DIR}/settings.json"
HISTORY_FILE = f"{DATA_DIR}/history.json"

# 기본 설정 (함수로 만들어서 동적으로 로드)
def get_default_settings():
    """기본 설정 반환 (.env에서 SS 키 로드)"""
    return {
        "gemini_api_key": GEMINI_API_KEY or "",  # .env 우선, 없으면 빈 문자열
        "ss_api_key": SEMANTIC_SCHOLAR_API_KEY,  # .env에서 로드하거나 빈 문자열
        "enable_references": False,   # 참고문헌 기능 ON/OFF
        "ss_min_citations": 30,
        "ss_result_limit": 3,
    }

DEFAULT_SETTINGS = get_default_settings()

# 과대해석 단어
OVERSTATEMENT_WORDS = [
    "always", "never", "perfectly", "proven", "clearly",
    "revolutionary", "breakthrough", "novel", "first", "best",
    "항상", "절대", "완벽", "확실히", "혁신적", "획기적", "최초",
]

# 모호 단어와 보정 제안
VAGUE_WORDS = {
    "significant": "p-value 또는 효과크기 명시",
    "fast": "ms/s 단위 시간 명시",
    "efficient": "% 수치 명시",
    "better": "비교 기준과 차이값 명시",
    "high": "구체적 수치 명시",
    "low": "구체적 수치 명시",
    "상당한": "% 수치 명시",
    "빠른": "지연시간(ms) 명시",
    "우수한": "점수/순위 명시",
    "많은": "개수 명시",
}

