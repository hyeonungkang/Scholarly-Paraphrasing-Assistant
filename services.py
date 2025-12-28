"""외부 API 서비스"""
import asyncio
import json
import httpx
import google.genai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL
from storage import get_settings

# ========== Gemini 2.5 Flash (google.genai) ==========
_client = None
_client_api_key = None
_gen_config = {
    "temperature": 0.2, 
    "max_output_tokens": 4096,
    "system_instruction": """You are an expert academic writing assistant for engineering papers.
Your responses must be:
1. Strictly in JSON format as requested
2. Accurate and well-structured
3. Focused on academic writing quality
4. Error-free and ready to use

Always output valid JSON without markdown code blocks unless explicitly requested."""
}


def _get_client():
    """API 키 변경에 대응하는 Gemini 클라이언트 생성"""
    global _client, _client_api_key
    settings = get_settings()
    api_key = GEMINI_API_KEY or settings.get("gemini_api_key", "")

    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. 설정에서 키를 입력하세요.")

    if _client is None or _client_api_key != api_key:
        _client = genai.Client(api_key=api_key)
        _client_api_key = api_key
    return _client


async def ask_gemini(prompt: str, model: str = None) -> dict:
    """Gemini 호출 → JSON 파싱 (LangGraph 밖에서도 사용 가능)"""
    client = _get_client()
    
    target_model = model or GEMINI_MODEL

    def _call():
        return client.models.generate_content(
            model=target_model,
            contents={'text': prompt},
            config=_gen_config,
        )

    try:
        response = await asyncio.to_thread(_call)
        text = (getattr(response, "text", "") or "").strip()

        if not text:
            raise Exception("Gemini API가 빈 응답을 반환했습니다.")

        # 마크다운 코드블록 제거
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1].strip()
                if text.startswith("json"):
                    text = text[4:].strip()

        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise json.JSONDecodeError("JSON이 dict가 아님", text, 0)
            return parsed
        except json.JSONDecodeError as je:
            error_msg = f"JSON 파싱 실패: {str(je)}"
            # 원본 응답을 더 많이 저장 (최대 1000자)
            raw_text = text[:1000] if len(text) > 1000 else text
            return {
                "raw": raw_text,
                "error": "parse_failed",
                "error_detail": error_msg,
            }
    except Exception as e:
        raise Exception(f"Gemini API 오류: {str(e)}")


# ========== Semantic Scholar (선택적) ==========
SS_BASE = "https://api.semanticscholar.org/graph/v1"
SS_FIELDS = "title,authors,year,citationCount,venue,abstract,url,externalIds"


async def search_papers(query: str) -> list:
    """
    참고문헌 검색 - 설정에서 ON일 때만 호출됨
    """
    settings = get_settings()

    if not settings.get("enable_references", False):
        return []

    # .env에서 우선, 없으면 settings에서 가져오기
    from config import SEMANTIC_SCHOLAR_API_KEY
    api_key = SEMANTIC_SCHOLAR_API_KEY or settings.get("ss_api_key", "")
    min_citations = settings.get("ss_min_citations", 30)
    limit = settings.get("ss_result_limit", 3)

    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SS_BASE}/paper/search",
                params={"query": query, "limit": 20, "fields": SS_FIELDS},
                headers=headers,
            )

            if resp.status_code != 200:
                return []

            papers = resp.json().get("data", [])

            # 인용수 필터 + 정렬
            filtered = [p for p in papers if p.get("citationCount", 0) >= min_citations]
            filtered.sort(key=lambda x: x.get("citationCount", 0), reverse=True)

            results = []
            for p in filtered[:limit]:
                authors = p.get("authors", [])
                author_str = ", ".join([a["name"] for a in authors[:3]])
                if len(authors) > 3:
                    author_str += " et al."

                ext_ids = p.get("externalIds", {})
                doi = ext_ids.get("DOI", "")

                results.append(
                    {
                        "title": p.get("title", ""),
                        "authors": author_str,
                        "year": p.get("year", ""),
                        "venue": p.get("venue", ""),
                        "citations": p.get("citationCount", 0),
                        "doi": doi,
                        "doi_url": f"https://doi.org/{doi}" if doi else "",
                        "ss_url": p.get("url", ""),
                        "abstract": (p.get("abstract", "") or "")[:200],
                        "apa": f"{author_str} ({p.get('year', '')}). {p.get('title', '')}. {p.get('venue', '')}."
                        + (f" https://doi.org/{doi}" if doi else ""),
                        "bibtex": _make_bibtex(p, doi),
                    }
                )

            return results
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return []  # Rate limit - 조용히 실패
        print(f"SS API HTTP Error: {e}")
        return []
    except Exception as e:
        print(f"SS API Error: {e}")
        return []


def _make_bibtex(p: dict, doi: str) -> str:
    authors = p.get("authors", [])
    first = authors[0]["name"].split()[-1].lower() if authors else "unknown"
    year = p.get("year", "")
    return f"""@article{{{first}{year},
  title = {{{p.get('title', '')}}},
  author = {{{', '.join([a['name'] for a in authors])}}},
  journal = {{{p.get('venue', '')}}},
  year = {{{year}}},
  doi = {{{doi}}}
}}"""

