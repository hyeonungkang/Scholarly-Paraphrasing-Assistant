"""LangGraph 워크플로우"""
from typing import TypedDict, Optional
import logging
from langgraph.graph import StateGraph, END
from nodes import (
    paraphrase,
    check_claim,
    match_journal,
    expand_claim,
    find_references,
    generate_reviewer_questions,
    detect_vague,
    analyze_prior_work,
    translate_to_korean,
)
from storage import get_journal, get_settings


class State(TypedDict):
    # 입력
    text: str
    journal_name: Optional[str]
    # 내부 데이터
    journal_data: Optional[dict]
    # 결과
    paraphrases: list
    claim: dict
    claim_section: Optional[str]
    journal_match: Optional[dict]
    expansions: list
    references: list
    reviewer_qs: list
    reviewer_section: Optional[str]
    positive_feedback: Optional[str]
    vague: list
    prior_work_analysis: Optional[dict]
    translation: Optional[str]
    translation_skipped_korean: Optional[bool]
    translation_error: Optional[bool]


async def load_journal(state: State) -> dict:
    """저널 데이터 로드"""
    if state.get("journal_name"):
        data = get_journal(state["journal_name"])
        return {"journal_data": data}
    return {"journal_data": None}


async def run_paraphrase(state: State) -> dict:
    j_name = state.get("journal_name", "") or ""
    result = await paraphrase(state["text"], j_name)
    # result는 이제 {"section": ..., "styles": [...]} 형태
    return {"paraphrases": result}


async def run_claim_check(state: State) -> dict:
    j_name = state.get("journal_name", "") or ""
    result = await check_claim(state["text"], j_name)
    return {"claim": result, "claim_section": result.get("section")}


async def run_journal_match(state: State) -> dict:
    j_data = state.get("journal_data")
    if not j_data:
        return {"journal_match": None}
    result = await match_journal(state["text"], j_data)
    return {"journal_match": result}


async def run_expand(state: State) -> dict:
    """주장 확장: claim 결과를 활용하여 더 정확한 확장 제안"""
    j_name = state.get("journal_name", "") or ""
    # claim 결과에서 추출한 주장을 활용 (quality 향상)
    claim_data = state.get("claim", {})
    claim_text = claim_data.get("claim", "")
    
    # claim이 있으면 사용, 없으면 원문에서 추출하도록 프롬프트에 전달
    result = await expand_claim(state["text"], claim_text, j_name)
    return {"expansions": result}


async def run_references(state: State) -> dict:
    settings = get_settings()
    if not settings.get("enable_references", False):
        return {"references": []}
    result = await find_references(state["text"])
    return {"references": result}


async def run_reviewer(state: State) -> dict:
    j_name = state.get("journal_name", "") or ""
    result = await generate_reviewer_questions(state["text"], j_name)
    # result는 이제 {"section": ..., "questions": [...], "positive_feedback": ...} 형태
    # questions만 추출하여 반환 (하위 호환성)
    questions = result.get("questions", []) if isinstance(result, dict) else result
    return {
        "reviewer_qs": questions, 
        "reviewer_section": result.get("section") if isinstance(result, dict) else None,
        "positive_feedback": result.get("positive_feedback") if isinstance(result, dict) else None
    }


async def run_vague(state: State) -> dict:
    result = detect_vague(state["text"])
    return {"vague": result}


async def run_prior_work(state: State) -> dict:
    """선행연구 비교 분석: 참고문헌 결과를 활용"""
    refs = state.get("references", [])
    if not refs:
        return {"prior_work_analysis": {}}
    j_name = state.get("journal_name", "") or ""
    result = await analyze_prior_work(state["text"], refs, j_name)
    return {"prior_work_analysis": result}


async def run_translation(state: State) -> dict:
    """영어→한국어 번역 (영어인 경우에만) - 패러프레이징과 주장확장 이후 실행"""
    logger = logging.getLogger(__name__)
    
    logger.debug("번역 노드 실행 시작")
    result = await translate_to_korean(state["text"])
    
    # 빈 문자열이면 None으로 변환하여 UI에서 구분 가능하도록 함
    # 빈 문자열 = 번역 건너뜀 (한국어 입력), None = 번역 실패
    if result:
        logger.debug("번역 성공")
        return {"translation": result}
    else:
        # 언어 감지 결과에 따라 구분
        from nodes import detect_language
        lang = detect_language(state["text"])
        if lang == "korean":
            # 한국어 입력이므로 번역 건너뜀 (정상)
            logger.debug("한국어 입력으로 번역 건너뜀")
            return {"translation": None, "translation_skipped_korean": True}
        else:
            # 번역 실패 또는 언어 감지 실패
            logger.warning("번역 실패 또는 언어 감지 실패")
            return {"translation": None, "translation_error": True}


def create_graph():
    g = StateGraph(State)

    # 노드 등록
    g.add_node("load_journal", load_journal)
    g.add_node("claim", run_claim_check)
    g.add_node("paraphrase", run_paraphrase)
    g.add_node("journal", run_journal_match)
    g.add_node("expand", run_expand)
    g.add_node("refs", run_references)
    g.add_node("reviewer", run_reviewer)
    g.add_node("vague", run_vague)
    g.add_node("prior_work", run_prior_work)
    g.add_node("translation", run_translation)

    # 실행 순서
    g.set_entry_point("load_journal")
    
    # load_journal 이후 핵심 분석 노드들을 병렬로 실행 (quality에 중요한 것들)
    g.add_edge("load_journal", "claim")
    g.add_edge("load_journal", "paraphrase")
    g.add_edge("load_journal", "journal")
    g.add_edge("load_journal", "refs")
    g.add_edge("load_journal", "reviewer")
    g.add_edge("load_journal", "vague")
    
    # claim 완료 후 expand 실행 (claim 결과를 활용하여 quality 향상)
    g.add_edge("claim", "expand")
    
    # refs 완료 후 prior_work 실행 (의존성 유지)
    g.add_edge("refs", "prior_work")
    
    # 패러프레이징과 주장확장 완료 후 번역 실행
    # paraphrase와 expand가 모두 완료된 후에만 번역 실행
    g.add_edge("paraphrase", "translation")
    g.add_edge("expand", "translation")
    
    # 다른 노드들은 직접 종료
    g.add_edge("journal", END)
    g.add_edge("reviewer", END)
    g.add_edge("vague", END)
    g.add_edge("prior_work", END)

    # 번역 완료 후 종료
    g.add_edge("translation", END)

    return g.compile()


# 싱글톤
graph = create_graph()


async def analyze(text: str, journal_name: str = "") -> dict:
    """메인 분석 함수"""
    result = await graph.ainvoke(
        {
            "text": text,
            "journal_name": journal_name or None,
        }
    )
    return result
