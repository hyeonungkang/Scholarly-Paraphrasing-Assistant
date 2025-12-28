"""분석 노드 함수들"""
import logging
from services import ask_gemini, search_papers
from prompts import (
    DEFAULT_PARAPHRASE_PROMPT,
    DEFAULT_CLAIM_CHECK_PROMPT,
    DEFAULT_JOURNAL_FIT_PROMPT,
    DEFAULT_EXPANSION_PROMPT,
    DEFAULT_REVIEWER_PROMPT,
    DEFAULT_PRIOR_WORK_PROMPT,
    DEFAULT_TRANSLATION_PROMPT,
    SEARCH_QUERY_PROMPT,
)
from prompt_generator import get_journal_prompts
from config import VAGUE_WORDS, OVERSTATEMENT_WORDS
from storage import get_settings, get_journal

logger = logging.getLogger(__name__)


def _get_prompt(journal_name: str, prompt_type: str, default: str) -> str:
    """저널 맞춤 프롬프트 또는 기본 프롬프트 반환"""
    if journal_name:
        custom_prompts = get_journal_prompts(journal_name)
        if custom_prompts and prompt_type in custom_prompts:
            custom_prompt = custom_prompts[prompt_type]
            logger.debug(f"맞춤 프롬프트 사용: {journal_name} - {prompt_type}")
            return custom_prompt
        else:
            logger.debug(f"맞춤 프롬프트 없음, 기본 프롬프트 사용: {journal_name} - {prompt_type}")
    return default


def _safe_format(template: str, **kwargs) -> str:
    """안전한 템플릿 포맷팅 (누락된 키는 그대로 유지)"""
    try:
        # 모든 플레이스홀더를 찾아서 대체
        result = template
        
        # claim_section이 있으면 claim으로도 사용 가능하도록 매핑
        if "claim_section" in kwargs and "claim" not in kwargs:
            kwargs["claim"] = kwargs["claim_section"]
        
        for key, value in kwargs.items():
            # {key} 또는 {{key}} 패턴 모두 대체
            result = result.replace(f"{{{key}}}", str(value))
            result = result.replace(f"{{{{{key}}}}}", str(value))
        
        # 남아있는 {claim} 플레이스홀더가 있으면 빈 문자열로 대체 (claim_section도 없는 경우)
        # 먼저 오타 수정
        import re
        result = re.sub(r'\{+\s*calim\s*\}+', '', result, flags=re.IGNORECASE)
        result = re.sub(r'\{+\s*cliam\s*\}+', '', result, flags=re.IGNORECASE)
        # 그 다음 정상적인 {claim} 제거 (단일 중괄호만) - 여러 번 반복하여 모든 경우 처리
        # {claim}, { claim }, {claim_section} 등 모든 변형 제거
        result = re.sub(r'\{+\s*claim(?:_section)?\s*\}+', '', result, flags=re.IGNORECASE)
        
        return result
    except Exception as e:
        logger.error(f"템플릿 포맷팅 오류: {e}, 템플릿: {template[:100]}")
        return template


# ========== 1. 패러프레이징 (영어 출력) ==========
async def paraphrase(text: str, journal_name: str = "") -> dict:
    try:
        prompt_template = _get_prompt(journal_name, "paraphrase", DEFAULT_PARAPHRASE_PROMPT)
        prompt = _safe_format(prompt_template, text=text)
        # #region agent log
        try:
            with open(r'c:\Users\khw95\OneDrive\문서\paper_assistance\paragraph-reviewer\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "P1", "location": "nodes.py:66", "message": "paraphrase entry", "data": {"journal_name": journal_name, "text_length": len(text), "prompt_length": len(prompt), "has_text_placeholder": "{text}" in prompt_template or "{{text}}" in prompt_template}, "timestamp": time.time() * 1000}) + '\n')
        except: pass
        # #endregion
        result = await ask_gemini(prompt)
        styles = result.get("styles", [])
        # #region agent log
        try:
            with open(r'c:\Users\khw95\OneDrive\문서\paper_assistance\paragraph-reviewer\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "P2", "location": "nodes.py:70", "message": "paraphrase result", "data": {"result_type": type(result).__name__, "keys": list(result.keys()) if isinstance(result, dict) else None, "styles_count": len(styles) if isinstance(styles, list) else None}, "timestamp": time.time() * 1000}) + '\n')
        except: pass
        # #endregion
        if not styles:
            logger.warning(f"패러프레이징 결과가 비어있습니다. journal_name={journal_name}")
        # section 정보를 포함한 dict 반환
        return {
            "section": result.get("section"),
            "styles": styles
        }
    except Exception as e:
        logger.error(f"패러프레이징 오류: {e}")
        return {"section": None, "styles": []}


# ========== 2. 주장 체크 (한국어) ==========
async def check_claim(text: str, journal_name: str = "") -> dict:
    found = [w for w in OVERSTATEMENT_WORDS if w.lower() in text.lower()]

    try:
        prompt_template = _get_prompt(journal_name, "claim_check", DEFAULT_CLAIM_CHECK_PROMPT)
        prompt = _safe_format(prompt_template, text=text)
        logger.debug(f"주장 체크 프롬프트 전송: journal_name={journal_name}, text_length={len(text)}")
        result = await ask_gemini(prompt)
        
        # JSON 파싱 실패 에러 확인
        if isinstance(result, dict) and result.get("error") == "parse_failed":
            raw_text = result.get("raw", "")
            error_detail = result.get("error_detail", "")
            logger.error(f"주장 체크 JSON 파싱 실패: {error_detail}")
            logger.debug(f"원본 응답 (처음 500자): {raw_text}")
            # JSON 파싱 실패 시 빈 결과로 처리하고 fallback 로직으로 진행
            result = {}
        
        if not isinstance(result, dict):
            logger.warning(f"주장 체크 결과가 딕셔너리가 아닙니다: {type(result)}, result={result}")
            result = {}
        
        # 필수 필드 검증 및 기본값 설정
        if "claim" not in result:
            logger.warning("주장 체크 결과에 'claim' 필드가 없습니다.")
            result["claim"] = ""
        if "score" not in result:
            logger.warning("주장 체크 결과에 'score' 필드가 없습니다.")
            result["score"] = 0
        if "issues" not in result or not isinstance(result.get("issues"), list):
            logger.warning("주장 체크 결과에 'issues' 필드가 없거나 리스트가 아닙니다.")
            result["issues"] = []
        if "suggestions" not in result or not isinstance(result.get("suggestions"), list):
            logger.warning("주장 체크 결과에 'suggestions' 필드가 없거나 리스트가 아닙니다.")
            result["suggestions"] = []
        if "section" not in result:
            logger.warning("주장 체크 결과에 'section' 필드가 없습니다.")
            result["section"] = None
        
        # claim이 비어있을 때 fallback 로직
        claim_text = result.get("claim", "").strip()
        if not claim_text:
            logger.warning("주장 체크 결과의 'claim' 필드가 비어있습니다. 원문에서 fallback 추출 시도.")
            # 원문에서 첫 문장 추출 시도
            import re
            # 문장 끝 구분자로 분리 (., !, ?)
            sentences = re.split(r'[.!?]+\s+', text.strip())
            if sentences and sentences[0]:
                # 첫 문장을 claim으로 사용 (최대 200자)
                fallback_claim = sentences[0].strip()
                if len(fallback_claim) > 200:
                    fallback_claim = fallback_claim[:197] + "..."
                result["claim"] = fallback_claim
                logger.info(f"Fallback claim 추출: {fallback_claim[:50]}...")
            else:
                # 문장 분리가 안되면 원문의 처음 200자를 사용
                fallback_claim = text.strip()[:200]
                if len(text.strip()) > 200:
                    fallback_claim += "..."
                result["claim"] = fallback_claim
                logger.info(f"Fallback claim (원문 일부): {fallback_claim[:50]}...")
        
        result["found_overstatements"] = found
        logger.debug(f"주장 체크 완료: claim={result.get('claim', '')[:50]}..., score={result.get('score', 0)}")
        return result
    except Exception as e:
        logger.error(f"주장 체크 오류: {e}", exc_info=True)
        # 에러 발생 시에도 원문에서 fallback 추출 시도
        import re
        fallback_claim = ""
        try:
            sentences = re.split(r'[.!?]+\s+', text.strip())
            if sentences and sentences[0]:
                fallback_claim = sentences[0].strip()
                if len(fallback_claim) > 200:
                    fallback_claim = fallback_claim[:197] + "..."
            else:
                fallback_claim = text.strip()[:200]
                if len(text.strip()) > 200:
                    fallback_claim += "..."
        except:
            # fallback 추출도 실패하면 원문의 처음 부분 사용
            fallback_claim = text.strip()[:200] if text.strip() else "Unable to extract claim"
        
        return {
            "claim": fallback_claim, 
            "score": 0, 
            "issues": [], 
            "suggestions": [], 
            "section": None,
            "found_overstatements": found,
            "error": str(e)
        }


# ========== 3. 저널 적합도 (한국어) ==========
async def match_journal(text: str, journal_data: dict) -> dict | None:
    if not journal_data:
        return None

    try:
        prompt_template = _get_prompt(
            journal_data.get("name", ""),
            "journal_fit",
            DEFAULT_JOURNAL_FIT_PROMPT,
        )

        prompt = _safe_format(
            prompt_template,
            text=text,
            journal_name=journal_data.get("full_name", journal_data.get("name", "")),
            scope=journal_data.get("aims_scope", ""),
        )

        result = await ask_gemini(prompt)
        if not isinstance(result, dict):
            logger.warning(f"저널 매칭 결과가 딕셔너리가 아닙니다: {type(result)}")
            return None
        return result
    except Exception as e:
        logger.error(f"저널 매칭 오류: {e}")
        return None


# ========== 4. 주장 확장 (한국어) ==========
async def expand_claim(text: str, claim: str = "", journal_name: str = "") -> list:
    """
    주장 확장: claim이 제공되면 사용하여 더 정확한 확장 제안 (quality 향상)
    claim이 없으면 원문에서 직접 추출
    """
    try:
        # Hybrid Prompting: Use DEFAULT_EXPANSION_PROMPT (Static Structure) with Dynamic Context (Journal Info)
        # We explicitly IGNORE the generated 'expansion' prompt from get_journal_prompts because the hybrid one is more robust.
        prompt_template = DEFAULT_EXPANSION_PROMPT
        
        # Get Journal Context
        target_journal = "General Academic Context"
        target_scope = "Broad impact and rigorous methodology"
        
        if journal_name:
            journal_data = get_journal(journal_name)
            if journal_data:
                target_journal = journal_data.get("full_name", journal_name)
                target_scope = journal_data.get("aims_scope", "")

        # claim이 제공되면 사용, 없으면 프롬프트에서 원문에서 추출하도록 안내
        if claim and claim.strip():
            # claim_section is minimal now because specific prompts are in the template
            claim_section = f"[핵심 주장]\n{claim}"
            logger.debug(f"주장 확장: 제공된 claim 사용, claim_length={len(claim)}")
        else:
            claim_section = "" # Template handles missing claim by asking to extract it if needed, but our new template assumes claim is passed or context is there.
            # Actually the new template has {claim_section} placeholder.
            # If no claim provided, we should ask it to extract.
            claim_section = "[핵심 주장]\n(입력된 문단에서 핵심 주장을 추출하여 분석의 기반으로 삼으세요)"
            logger.debug(f"주장 확장: 원문에서 claim 추출")
        
        # claim_section이 있으면 claim으로도 사용 가능하도록 전달
        format_kwargs = {
            "text": text, 
            "claim_section": claim_section,
            "journal_name": target_journal,
            "aims_scope": target_scope
        }
        if claim and claim.strip():
            format_kwargs["claim"] = claim
            
        prompt = _safe_format(prompt_template, **format_kwargs)
        logger.debug(f"주장 확장 프롬프트 전송: journal_name={journal_name}, text_length={len(text)}, has_claim={bool(claim)}")
        result = await ask_gemini(prompt)
        
        if not isinstance(result, dict):
            logger.warning(f"주장 확장 결과가 딕셔너리가 아닙니다: {type(result)}, result={result}")
            return []
        
        directions = result.get("directions", [])
        if not directions or not isinstance(directions, list):
            logger.warning(f"주장 확장 결과가 비어있거나 리스트가 아닙니다. journal_name={journal_name}, result={result}")
            return []
        
        # 각 direction 검증 및 section 정보 추가
        section = result.get("section")
        validated_directions = []
        for idx, d in enumerate(directions):
            if not isinstance(d, dict):
                logger.warning(f"주장 확장 direction {idx}가 딕셔너리가 아닙니다: {type(d)}")
                continue
            
            # 필수 필드 검증
            if "type" not in d:
                d["type"] = f"방향 {idx + 1}"
            if "claim" not in d:
                logger.warning(f"주장 확장 direction {idx}에 'claim' 필드가 없습니다.")
                d["claim"] = ""
            if "pro" not in d:
                logger.warning(f"주장 확장 direction {idx}에 'pro' 필드가 없습니다.")
                d["pro"] = ""
            if "con" not in d:
                logger.warning(f"주장 확장 direction {idx}에 'con' 필드가 없습니다.")
                d["con"] = ""
            if "reason" not in d:
                logger.warning(f"주장 확장 direction {idx}에 'reason' 필드가 없습니다.")
                d["reason"] = ""
            if "experiments" not in d:
                logger.warning(f"주장 확장 direction {idx}에 'experiments' 필드가 없습니다.")
                d["experiments"] = []
            elif not isinstance(d.get("experiments"), list):
                logger.warning(f"주장 확장 direction {idx}의 'experiments' 필드가 리스트가 아닙니다.")
                d["experiments"] = []
            
            if section:
                d["section"] = section
            
            validated_directions.append(d)
        
        logger.debug(f"주장 확장 완료: directions_count={len(validated_directions)}, section={section}")
        return validated_directions
    except Exception as e:
        logger.error(f"주장 확장 오류: {e}", exc_info=True)
        return []


# ========== 5. 리뷰어 질문 (한국어) ==========
async def generate_reviewer_questions(text: str, journal_name: str = "") -> dict:
    try:
        prompt_template = _get_prompt(journal_name, "reviewer", DEFAULT_REVIEWER_PROMPT)
        prompt = _safe_format(prompt_template, text=text)
        logger.debug(f"리뷰어 질문 프롬프트 전송: journal_name={journal_name}, text_length={len(text)}")
        result = await ask_gemini(prompt)
        
        if not isinstance(result, dict):
            logger.warning(f"리뷰어 질문 결과가 딕셔너리가 아닙니다: {type(result)}, result={result}")
            return {"section": None, "questions": [], "positive_feedback": None}
        
        questions = result.get("questions", [])
        positive_feedback = result.get("positive_feedback", "")
        
        if not questions:
            logger.warning(f"리뷰어 질문 결과가 비어있습니다. journal_name={journal_name}")
        
        if not positive_feedback:
            logger.warning(f"긍정적인 피드백이 없습니다. journal_name={journal_name}")
        
        # section 정보와 긍정적인 피드백을 포함한 dict 반환
        return {
            "section": result.get("section"),
            "questions": questions,
            "positive_feedback": positive_feedback if positive_feedback else None
        }
    except Exception as e:
        logger.error(f"리뷰어 질문 생성 오류: {e}", exc_info=True)
        return {"section": None, "questions": [], "positive_feedback": None}


# ========== 6. 선행연구 비교 분석 (한국어) ==========
async def analyze_prior_work(text: str, references: list, journal_name: str = "") -> dict:
    """참고문헌 검색 결과를 활용해 선행연구와의 겹침/차별점을 분석"""
    if not references:
        return {}

    try:
        # 상위 5개까지만 사용
        top_refs = references[:5]
        prior_works = []
        for r in top_refs:
            prior_works.append(
                f"- {r.get('title', '')} ({r.get('year', '')}) | {r.get('venue', '')} | DOI: {r.get('doi', 'N/A')}"
            )

        prior_text = "\n".join(prior_works)
        prompt_template = _get_prompt(journal_name, "prior_work", DEFAULT_PRIOR_WORK_PROMPT)
        prompt = _safe_format(prompt_template, text=text, prior_works=prior_text)
        result = await ask_gemini(prompt)
        return result or {}
    except Exception as e:
        logger.error(f"선행연구 분석 오류: {e}")
        return {}


# ========== 6. 참고문헌 (조건부) ==========
async def find_references(text: str) -> list:
    settings = get_settings()
    if not settings.get("enable_references", False):
        return []

    try:
        query_result = await ask_gemini(SEARCH_QUERY_PROMPT.format(text=text))
        query = query_result.get("query", "")

        if not query:
            return []

        return await search_papers(query)
    except Exception as e:
        logger.error(f"참고문헌 검색 오류: {e}")
        return []


# ========== 7. 모호성 체크 (로컬, LLM 미사용) ==========
def detect_vague(text: str) -> list:
    found = []
    text_lower = text.lower()
    for word, suggestion in VAGUE_WORDS.items():
        if word.lower() in text_lower:
            found.append({"word": word, "fix": suggestion})
    return found


# ========== 언어 감지 (간단한 휴리스틱) ==========
def detect_language(text: str) -> str:
    """텍스트의 언어를 감지 (영어/한국어)"""
    if not text or not text.strip():
        return "unknown"
    
    # 간단한 휴리스틱: 한글 유니코드 범위 체크
    korean_chars = sum(1 for char in text if '\uAC00' <= char <= '\uD7A3')
    total_chars = sum(1 for char in text if char.isalpha())
    
    if total_chars == 0:
        return "unknown"
    
    korean_ratio = korean_chars / total_chars if total_chars > 0 else 0
    
    # 한글이 30% 이상이면 한국어로 판단
    if korean_ratio >= 0.3:
        return "korean"
    else:
        return "english"


# ========== 8. 영어→한국어 번역 ==========
async def translate_to_korean(text: str) -> str:
    """영어 학술 문단을 한국어로 번역 (영어인 경우에만)"""
    if not text or not text.strip():
        logger.warning("번역할 텍스트가 비어있습니다.")
        return ""
    
    # 언어 감지
    lang = detect_language(text)
    logger.debug(f"번역 언어 감지: lang={lang}, text_length={len(text)}")
    
    if lang == "korean":
        logger.info("입력이 한국어이므로 번역을 건너뜁니다.")
        return ""
    
    if lang == "unknown":
        logger.warning("언어를 감지할 수 없어 번역을 건너뜁니다.")
        return ""
    
    # 영어인 경우에만 번역 실행
    try:
        prompt = _safe_format(DEFAULT_TRANSLATION_PROMPT, text=text)
        logger.debug(f"번역 프롬프트 전송: text_length={len(text)}")
        result = await ask_gemini(prompt)
        translation = result.get("translation", "")
        if not translation:
            logger.warning("번역 결과가 비어있습니다. result={result}")
        else:
            logger.debug(f"번역 완료: translation_length={len(translation)}")
        return translation
    except Exception as e:
        logger.error(f"번역 오류: {e}", exc_info=True)
        return ""
