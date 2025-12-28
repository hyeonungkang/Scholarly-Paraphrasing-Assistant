"""JSON 저장소 관리"""
import json
import os
from datetime import datetime
from config import DATA_DIR, JOURNALS_FILE, SETTINGS_FILE, HISTORY_FILE, DEFAULT_SETTINGS


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


# ========== 설정 ==========
def get_settings() -> dict:
    _ensure_dir()
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)

    # 새 필드가 추가된 경우 기본값으로 채워서 저장
    changed = False
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
            changed = True
    if changed:
        save_settings(settings)
    return settings


def save_settings(settings: dict):
    _ensure_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def update_setting(key: str, value):
    settings = get_settings()
    settings[key] = value
    save_settings(settings)


# ========== 저널 ==========
def get_journals() -> list:
    """저널 목록을 JSON 파일에서 로드"""
    _ensure_dir()
    if not os.path.exists(JOURNALS_FILE):
        save_journals([])
        return []
    try:
        with open(JOURNALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"저널 파일 로드 오류: {e}")
        # 백업 후 빈 리스트 반환
        if os.path.exists(JOURNALS_FILE):
            backup_path = f"{JOURNALS_FILE}.backup"
            os.rename(JOURNALS_FILE, backup_path)
        return []


def save_journals(journals: list):
    """저널 목록을 JSON 파일에 저장 (스왑 가능한 형식)"""
    _ensure_dir()
    try:
        with open(JOURNALS_FILE, "w", encoding="utf-8") as f:
            json.dump(journals, f, ensure_ascii=False, indent=2)
    except IOError as e:
        raise Exception(f"저널 파일 저장 오류: {e}")


def save_journal(journal_data: dict):
    """단일 저널 추가/업데이트 (JSON 스왑 가능)"""
    try:
        journals = get_journals()
        if not isinstance(journals, list):
            journals = []
        
        # 필수 필드 확인
        if "name" not in journal_data:
            raise ValueError("저널 데이터에 'name' 필드가 없습니다.")
        
        idx = next((i for i, j in enumerate(journals) if j.get("name") == journal_data["name"]), None)
        if idx is not None:
            journals[idx] = journal_data
            print(f"저널 업데이트: {journal_data['name']}")
        else:
            journals.append(journal_data)
            print(f"저널 추가: {journal_data['name']}")
        
        save_journals(journals)
        print(f"저널 저장 완료: 총 {len(journals)}개")
    except Exception as e:
        print(f"저널 저장 오류: {e}")
        raise


def get_journal(name: str) -> dict | None:
    """이름으로 저널 조회"""
    journals = get_journals()
    return next((j for j in journals if j["name"] == name), None)


def delete_journal(name: str):
    """저널 삭제"""
    journals = [j for j in get_journals() if j["name"] != name]
    save_journals(journals)


def export_journals_to_json(file_path: str = None) -> str:
    """저널 데이터를 JSON 파일로 내보내기 (스왑 가능)"""
    journals = get_journals()
    if file_path is None:
        file_path = f"{DATA_DIR}/journals_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(journals, f, ensure_ascii=False, indent=2)
    return file_path


def import_journals_from_json(file_path: str, merge: bool = False):
    """JSON 파일에서 저널 데이터 가져오기 (스왑 가능)
    
    Args:
        file_path: 가져올 JSON 파일 경로
        merge: True면 기존 데이터와 병합, False면 교체
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            imported = json.load(f)
        
        if not isinstance(imported, list):
            raise ValueError("JSON 파일은 저널 배열이어야 합니다.")
        
        if merge:
            existing = get_journals()
            existing_names = {j["name"] for j in existing}
            for journal in imported:
                if journal.get("name") not in existing_names:
                    existing.append(journal)
            save_journals(existing)
        else:
            save_journals(imported)
    except (json.JSONDecodeError, IOError, ValueError) as e:
        raise Exception(f"저널 파일 가져오기 오류: {e}")


# ========== 히스토리 ==========
def save_history(text: str, result: dict):
    _ensure_dir()
    history = get_history()
    history.insert(
        0,
        {
            "time": datetime.now().isoformat(),
            "text": text[:100],
            "result": result,
        },
    )
    history = history[:30]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)


def get_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history_list(history: list):
    """히스토리 리스트 전체 저장"""
    _ensure_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
