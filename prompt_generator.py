"""
저널 Aims & Scope 기반 맞춤 프롬프트 자동 생성기
"""
import re
from services import ask_gemini
from prompts import GENERATE_JOURNAL_PROMPTS
from storage import save_journal, get_journal
from config import GEMINI_MODEL


def _normalize_placeholder(text: str) -> str:
    """프롬프트 내 플레이스홀더 정규화: {text}, {{text}}, {{{{text}}}} 등을 {text}로 통일"""
    # #region agent log
    import json
    try:
        with open(r'c:\Users\khw95\OneDrive\문서\paper_assistance\paragraph-reviewer\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "prompt_generator.py:11", "message": "_normalize_placeholder entry", "data": {"text_preview": text[:150], "has_calim": "calim" in text.lower(), "has_double_braces_claim": "{{claim}}" in text}, "timestamp": __import__('time').time() * 1000}) + '\n')
    except: pass
    # #endregion
    # {text} 패턴을 찾아서 정규화
    # 여러 중괄호가 있어도 {text}로 통일
    text = re.sub(r'\{+\s*text\s*\}+', '{text}', text)
    # claim 오타 자동 수정 (calim, cliam, cliam 등)
    text = re.sub(r'\{+\s*calim\s*\}+', '{claim}', text, flags=re.IGNORECASE)
    text = re.sub(r'\{+\s*cliam\s*\}+', '{claim}', text, flags=re.IGNORECASE)
    text = re.sub(r'\{+\s*claim\s*\}+', '{claim}', text)
    text = re.sub(r'\{+\s*journal_name\s*\}+', '{journal_name}', text)
    text = re.sub(r'\{+\s*scope\s*\}+', '{scope}', text)
    text = re.sub(r'\{+\s*prior_works\s*\}+', '{prior_works}', text)
    text = re.sub(r'\{+\s*claim_section\s*\}+', '{claim_section}', text)
    # #region agent log
    try:
        with open(r'c:\Users\khw95\OneDrive\문서\paper_assistance\paragraph-reviewer\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "prompt_generator.py:24", "message": "_normalize_placeholder exit", "data": {"has_claim": "{claim}" in text, "has_calim": "calim" in text.lower()}, "timestamp": __import__('time').time() * 1000}) + '\n')
    except: pass
    # #endregion
    return text


def _validate_prompt(prompt: str, prompt_type: str) -> str:
    """프롬프트 유효성 검증 및 정규화"""
    if not prompt or not isinstance(prompt, str):
        raise ValueError(f"프롬프트 '{prompt_type}'가 유효하지 않습니다.")
    
    # 플레이스홀더 정규화
    prompt = _normalize_placeholder(prompt)
    
    # 필수 플레이스홀더 확인
    if prompt_type == "paraphrase" and "{text}" not in prompt:
        raise ValueError(f"프롬프트 '{prompt_type}'에 {{text}} 플레이스홀더가 없습니다.")
    elif prompt_type in ["claim_check", "journal_fit", "reviewer"] and "{text}" not in prompt:
        raise ValueError(f"프롬프트 '{prompt_type}'에 {{text}} 플레이스홀더가 없습니다.")
    elif prompt_type == "expansion":
        has_text = "{text}" in prompt
        has_claim = "{claim}" in prompt or "{claim_section}" in prompt
        # #region agent log
        import json
        try:
            with open(r'c:\Users\khw95\OneDrive\문서\paper_assistance\paragraph-reviewer\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "prompt_generator.py:40", "message": "expansion validation check", "data": {"has_text": has_text, "has_claim": "{claim}" in prompt, "has_claim_section": "{claim_section}" in prompt, "prompt_preview": prompt[:200]}, "timestamp": __import__('time').time() * 1000}) + '\n')
        except: pass
        # #endregion
        if not has_text or not has_claim:
            raise ValueError(f"프롬프트 '{prompt_type}'에 {{text}} 또는 {{claim}} 플레이스홀더가 없습니다.")
    elif prompt_type == "journal_fit" and "{scope}" not in prompt:
        # journal_fit은 scope가 필수는 아니지만 있으면 좋음
        pass
    
    return prompt


async def generate_journal_prompts(
    journal_name: str,
    aims_scope: str,
    custom_methodology: str = ""
) -> dict:
    """
    Aims & Scope를 분석하여 저널 맞춤 프롬프트 세트 생성 (Single-Shot High Quality)
    """
    # #region agent log
    try:
        import json
        with open(r'c:\Users\khw95\OneDrive\문서\paper_assistance\paragraph-reviewer\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "prompt_generator.py", "message": "generate_journal_prompts entry (Single-Shot ver)", "data": {"journal_name": journal_name}, "timestamp": __import__('time').time() * 1000}) + '\n')
    except: pass
    # #endregion
    
    # 1. 프롬프트 구성
    prompt = GENERATE_JOURNAL_PROMPTS.format(
        journal_name=journal_name,
        aims_scope=aims_scope,
        custom_methodology=custom_methodology
    )
    
    # 2. Gemini 호출 (gemini-2.5-pro 사용 권장)
    try:
        # 모델은 config의 GEMINI_MODEL 사용 (보통 gemini-2.0-flash-exp 등)
        # 하지만 품질이 중요하다면 2.5-pro 명시 가능하나, 여기서는 기본 설정 따름
        result = await ask_gemini(prompt)
        
        # 필수 필드 검증
        if not result or "prompts" not in result or not result["prompts"]:
            raise Exception("프롬프트 생성 실패: 결과가 비어있습니다.")
            
        prompts = result["prompts"]
        
        # ⚠️ 중요: 생성된 프롬프트 검증 및 보정 (Prompt Repair)
        
        # helper: expansion 프롬프트에 필수 플레이스홀더 보정
        def _ensure_expansion_placeholders(p: str) -> str:
            if not p: return p
            updated = p
            if "{text}" not in updated:
                updated = f"[입력 문단]\n{{text}}\n\n" + updated
            if "{claim}" not in updated and "{claim_section}" not in updated:
                updated = updated + "\n\n[핵심 주장]\n{claim}\n"
            return updated

        # helper: 기본 프롬프트에 {text} 보정
        def _ensure_basic_placeholders(p: str) -> str:
            if not p: return p
            if "{text}" not in p:
                return f"[입력 문단]\n{{text}}\n\n" + p
            return p
        
        # 각 프롬프트 검증 및 정규화
        validated_prompts = {}
        for ptype, ptext in prompts.items():
            try:
                # 1. 자동 보정 (Validation 전에 수행)
                if ptype == "expansion":
                    ptext = _ensure_expansion_placeholders(ptext)
                elif ptype in ["paraphrase", "claim_check", "journal_fit", "reviewer"]:
                    # 다른 프롬프트들도 {text}가 필수이므로 없으면 자동 추가
                    ptext = _ensure_basic_placeholders(ptext)

                # 2. Validation
                validated_prompts[ptype] = _validate_prompt(ptext, ptype)
            
            except ValueError as e:
                # 에러 로깅 후 throw
                raise Exception(f"프롬프트 '{ptype}' 검증 실패: {str(e)}")

        # preferred_style 대체
        preferred_style = result.get("preferred_style", "") or "Analyzed Journal Style"
        if "paraphrase" in validated_prompts:
             validated_prompts["paraphrase"] = validated_prompts["paraphrase"].replace("{preferred_style}", preferred_style)
             # 만약 유저가 실수로 이중 중괄호를 썼다면
             validated_prompts["paraphrase"] = validated_prompts["paraphrase"].replace("{{preferred_style}}", preferred_style)
             
        # journal_fit 프롬프트의 journal_name 대체
        if "journal_fit" in validated_prompts:
            validated_prompts["journal_fit"] = validated_prompts["journal_fit"].replace("{journal_name}", journal_name)
            validated_prompts["journal_fit"] = validated_prompts["journal_fit"].replace("{{journal_name}}", journal_name)

        result["prompts"] = validated_prompts
        return result

    except Exception as e:
        raise Exception(f"저널 프롬프트 생성 실패: {str(e)}")


async def register_journal(
    name: str,
    full_name: str,
    aims_scope: str,
    custom_methodology: str = ""
) -> dict:
    """
    저널 등록 + 프롬프트 자동 생성 + 저장
    LangGraph 밖에서 실행되어 JSON 형식으로 동적 프롬프트 리스트 업데이트
    """
    if not name or not aims_scope:
        raise ValueError("저널 약어와 Aims & Scope는 필수입니다.")
    
    # LangGraph 밖에서 실행 - JSON 형식으로 프롬프트 생성
    generated = await generate_journal_prompts(name, aims_scope, custom_methodology)

    # 프롬프트 구조 검증
    prompts = generated.get("prompts", {})
    if not isinstance(prompts, dict):
        raise ValueError("생성된 프롬프트가 올바른 형식이 아닙니다.")
    
    # 필수 프롬프트 타입 확인
    required_types = ["paraphrase", "claim_check", "journal_fit", "expansion", "reviewer"]
    missing_types = [ptype for ptype in required_types if ptype not in prompts]
    if missing_types:
        raise ValueError(f"필수 프롬프트 타입이 생성되지 않았습니다: {', '.join(missing_types)}")

    journal_data = {
        "name": name,
        "full_name": full_name,
        "aims_scope": aims_scope,
        "custom_methodology": custom_methodology,
        "keywords": generated.get("journal_keywords", []),
        "audience": generated.get("target_audience", ""),
        "style": generated.get("preferred_style", ""),
        "prompts": prompts,  # 동적 프롬프트 리스트
        "criteria": generated.get("evaluation_criteria", []),
    }

    # JSON 형식으로 저장하여 동적 프롬프트 리스트 업데이트
    try:
        print(f"저널 저장 시도: {name}")
        save_journal(journal_data)
        print(f"저널 저장 성공: {name}")
    except Exception as e:
        print(f"저널 저장 실패: {name}, 오류: {e}")
        raise Exception(f"저널 저장 중 오류 발생: {str(e)}")
    
    return journal_data


def get_journal_prompts(journal_name: str) -> dict | None:
    """저장된 저널의 맞춤 프롬프트 가져오기"""
    if not journal_name:
        return None
    
    journal = get_journal(journal_name)
    if journal and "prompts" in journal:
        prompts = journal["prompts"]
        if isinstance(prompts, dict) and len(prompts) > 0:
            return prompts
    return None
