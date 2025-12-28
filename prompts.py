# ============================================================
# 🔧 프롬프트 생성용 (저널 등록 시 1회 실행)
# ============================================================

GENERATE_JOURNAL_PROMPTS = """당신은 학술 저널 분석 및 프롬프트 엔지니어링 전문가입니다.
제공된 저널 정보와 '기본 프롬프트 템플릿'을 바탕으로, 해당 저널에 최적화된 '맞춤 프롬프트 세트'를 JSON 형식으로 작성하세요.

[저널 정보]
이름: {journal_name}
Aims & Scope:
{aims_scope}

[사용자 커스텀 요구사항]
{custom_methodology}

[지시사항]
1. 아래 제공된 5가지 **기본 프롬프트 템플릿**을 기반으로 작성하세요.
2. 각 프롬프트의 **JSON 출력 형식**과 **필수 플레이스홀더({{text}}, {{claim}} 등)**는 **절대 변경하지 마세요.** 구조를 유지하는 것이 가장 중요합니다.
3. 대신, 프롬프트의 **지시문(Instructions)과 평가 기준(Criteria)** 내용을 저널의 Aims & Scope에 맞춰 구체적으로 수정하세요.
   - 예: "이 저널의 심사 기준에 맞춰..." -> "{journal_name}의 핵심 가치인 '실용적 응용'을 중심으로..."
   - 예: "과대해석 평가" -> "{journal_name}이 엄격히 금지하는 'Speculative Claims' 기준으로 평가..."
4. **언어 규칙**:
   - **분석 결과(문제점, 제안, 장단점, 이유 등)는 반드시 한국어로 작성하도록 지시하세요.**
   - 단, `claim`(핵심 주장)과 `revised_en`(영어 수정본)은 반드시 **영어**로 작성해야 합니다.
   - 프롬프트 자체는 한국어로 작성하세요.

[기본 프롬프트 템플릿 (참고용)]

--- 1. PARAPHRASE TEMPLATE ---
이 저널의 스타일({{preferred_style}})에 맞게 입력된 영문 문단({{text}})을 재작성하세요. 다음 5가지 스타일 옵션을 고려하여 재작성하세요...
[출력 형식]
반드시 다음 JSON 형식으로 출력하세요: {{"section": "...", "styles": [{{"name": "...", "text": "...", "translation": "한국어 번역본"}}]}}

--- 2. CLAIM_CHECK TEMPLATE ---
이 저널의 심사 기준에 맞춰 입력된 문단({{text}})의 주장이 과도하거나 검증되지 않았는지 평가하세요...
[출력 형식]
반드시 다음 JSON 형식으로 출력하세요: {{"section": "...", "claim": "핵심 주장 1문장 (영어)", "score": 0-10, "issues": ["문제점1 (한국어)", "문제점2"], "suggestions": ["수정 제안1 (한국어)", "수정 제안2"]}}

--- 3. JOURNAL_FIT TEMPLATE ---
입력된 문단({{text}})이 이 저널({{journal_name}})의 Scope에 부합하는지 10점 만점으로 평가하세요...
[출력 형식]
반드시 다음 JSON 형식으로 출력하세요: {{"section": "...", "score": 0, "matches": ["구체적 일치점1 (한국어)"], "gaps": ["부족한 점1 (한국어)"], "revised": "저널 맞춤 수정본 (한국어)", "revised_en": "Revised paragraph (English)"}}

--- 4. EXPANSION TEMPLATE ---
이 저널의 관심사를 고려하여, 입력된 문단({{text}})과 핵심 주장({{claim}})을 기반으로 3-5가지 'Next Level' 연구 방향을 제안하세요...
[출력 형식]
반드시 다음 JSON 형식으로 출력하세요: {{"section": "...", "directions": [{{"type": "...", "claim": "New Claim (English)", "pro": "장점 (한국어)", "con": "단점 (한국어)", "reason": "이유 (한국어)", "experiments": ["실험1 (한국어)", "실험2"]}}]}}

--- 5. REVIEWER TEMPLATE ---
이 저널의 까다로운 리뷰어 관점에서 입력된 문단({{text}})에 대해 비판적인 질문 3-5개와 긍정적인 피드백 1개를 생성하세요...
[출력 형식]
반드시 다음 JSON 형식으로 출력하세요: {{"section": "...", "positive_feedback": "긍정적 피드백 (한국어)", "questions": [{{"q": "질문 (한국어)", "severity": "critical|major|minor", "reason": "이유 (한국어)"}}]}}

[최종 출력 형식]
반드시 다음 JSON 구조로만 출력하세요 (마크다운 코드블록 금지, 순수 JSON):
{{
  "journal_keywords": ["키워드1", "키워드2", "키워드3"],
  "target_audience": "독자층 분석",
  "preferred_style": "선호하는 스타일 분석",
  "prompts": {{
    "paraphrase": "수정된 paraphrase 프롬프트 (템플릿 구조 유지, 필드/포맷 엄수)",
    "claim_check": "수정된 claim_check 프롬프트 (템플릿 구조 유지, 필드/포맷 엄수, 한국어 출력 지시)",
    "journal_fit": "수정된 journal_fit 프롬프트 (템플릿 구조 유지, 필드/포맷 엄수, 한국어 출력 지시)",
    "expansion": "수정된 expansion 프롬프트 (템플릿 구조 유지, 필드/포맷 엄수, 한국어 출력 지시)",
    "reviewer": "수정된 reviewer 프롬프트 (템플릿 구조 유지, 필드/포맷 엄수, 한국어 출력 지시)"
  }},
  "evaluation_criteria": ["평가기준1", "평가기준2", "평가기준3"]
}}"""


# ============================================================
# 📝 기본 분석 프롬프트 (저널 미선택 시 사용)
# ============================================================

DEFAULT_PARAPHRASE_PROMPT = """You are an expert academic writer for engineering journals.
Rewrite the following paragraph in 5 different academic styles IN ENGLISH.

[Original Paragraph]
{text}

[Section Detection]
First, determine which section of an academic paper this paragraph belongs to. Possible sections: Introduction, Related Work, Methodology, Results, Discussion, Conclusion, Abstract

[5 Styles Required]
1. **Assertive**: Strong claims. "demonstrates", "confirms", "establishes"
2. **Objective**: Neutral, passive voice. "was observed", "was measured"
3. **Connective**: Logical flow. "Therefore", "Consequently", "In contrast"
4. **Hedged**: Cautious. "suggests", "may indicate", "potentially"
5. **Concise**: 30% shorter, key points only.

Output JSON only:
{{"section": "Introduction|Related Work|Methodology|Results|Discussion|Conclusion|Abstract", "styles": [{{"name": "Assertive", "text": "...", "translation": "Korean translation of the rewritten text"}}, {{"name": "Objective", "text": "...", "translation": "..."}}, {{"name": "Connective", "text": "...", "translation": "..."}}, {{"name": "Hedged", "text": "...", "translation": "..."}}, {{"name": "Concise", "text": "...", "translation": "..."}}]}}"""


DEFAULT_CLAIM_CHECK_PROMPT = """당신은 IEEE/ACM 등 주요 공학 저널의 경험이 풍부한 심사위원입니다. 다음 문단을 엄격하게 분석하세요.

[분석할 문단]
{text}

[Section 파악]
먼저 이 문단이 논문의 어느 section에 속하는지 파악하세요. 가능한 section: Introduction, Related Work, Methodology, Results, Discussion, Conclusion, Abstract

[분석 지침]
1. **핵심 주장 추출 (필수)**: 
   - 문단의 핵심 논점을 반드시 1문장으로 명확히 추출하세요 (반드시 영어로 작성)
   - 추출이 어려운 경우에도 문단의 주요 논점을 요약하여 1문장으로 작성해야 합니다
   - "claim" 필드는 절대 비어있을 수 없습니다. 반드시 문단의 핵심 내용을 담은 영어 문장을 제공하세요
   - 예시: "This study proposes a novel deep learning architecture that improves accuracy by 15% compared to existing methods."
2. **과대해석 점수 (1-10)**: 
   - 1-3: 적절한 주장 강도
   - 4-6: 약간 과장된 표현
   - 7-10: 심각한 과대해석 (근거 부족, 절대적 표현 사용 등)
3. **문제점 분석 (2-3개)**: 다음 관점에서 구체적으로 지적 (한국어로 작성)
   - 선행연구와의 겹침: 어떤 기존 연구와 어떤 부분이 중복되는가?
   - 실험/방법론 한계: 데이터나 방법의 제약사항은 무엇인가?
   - 논리적 결함: 주장과 증거 사이의 불일치는 무엇인가?
4. **수정 제안 (2-3개)**: 구체적이고 실행 가능한 개선안 (한국어로 작성)
   - 선행연구와의 차별화를 어떻게 강조할 것인가?
   - 주장을 뒷받침할 추가 실험/분석은 무엇인가?
   - 표현을 더 정확하고 신중하게 바꾸는 방법은?

[중요 사항]
- 반드시 JSON 형식으로만 출력하세요. 마크다운 코드블록(```json)을 사용하지 마세요.
- **"claim" 필드는 필수이며 절대 비어있을 수 없습니다.** 문단의 핵심 내용을 반드시 영어로 1문장으로 추출하세요.
- "issues"와 "suggestions"는 반드시 한국어로 작성된 리스트여야 합니다.
- "section" 필드는 반드시 다음 중 하나여야 합니다: Introduction, Related Work, Methodology, Results, Discussion, Conclusion, Abstract

[출력 형식]
반드시 다음 JSON 형식으로 출력 (claim 필드는 필수이며 반드시 영어로 작성된 1문장이어야 함):
{{"section": "Introduction|Related Work|Methodology|Results|Discussion|Conclusion|Abstract", "claim": "핵심 주장 1문장 (영어, 필수, 절대 비어있을 수 없음)", "score": 0, "issues": ["구체적 문제점1 (한국어)", "구체적 문제점2 (한국어)"], "suggestions": ["구체적 수정 제안1 (한국어)", "구체적 수정 제안2 (한국어)"]}}

**주의**: claim 필드가 비어있으면 출력이 유효하지 않습니다. 반드시 문단의 핵심 주장을 영어로 1문장으로 추출하여 제공하세요."""


DEFAULT_JOURNAL_FIT_PROMPT = """당신은 {journal_name} 저널의 수석 에디터입니다. 투고된 문단이 우리 저널의 Aims & Scope와 스타일 기준에 얼마나 부합하는지 정밀하게 분석하세요.

[투고된 문단]
{text}

[타겟 저널 정보]
저널명: {journal_name}
Aims & Scope: {scope}

[Section 파악]
먼저 이 문단이 논문의 어느 section에 속하는지 파악하세요 (Introduction, Related Work, Methodology, Results, Discussion, Conclusion, Abstract).

[평가 기준]
1. **적합도 점수 (0-10 점)**: 
   - 10점: 완벽함. 저널의 핵심 주제와 완전히 일치하며 스타일도 완벽함.
   - 8-9점: 매우 우수함. 약간의 다듬기만 필요함.
   - 6-7점: 적합하나 문체나 강조점이 저널 스타일과 다소 차이가 있음.
   - 4-5점: 경계선. 저널 범위에 걸쳐있으나 매력도가 떨어짐.
   - 0-3점: 부적합. 다른 저널을 알아보는 것이 좋음.
2. **구체적인 일치점 (Specific Matches)**: 
   - 일반적인 칭찬이 아닌, 저널의 Aims & Scope의 **어떤 구체적인 키워드나 문장**과 문단의 내용이 일치하는지 명시하세요.
   - 예: "저널 Scope의 'Micro-electromechanical systems' 항목과 문단의 'MEMS fabrication process' 내용이 정확히 일치함."
3. **보완이 필요한 점 (Gaps & Improvements)**: 
   - 저널의 독자층(Audience)이 기대하는 깊이나 선호하는 표현 방식과 다른 점을 지적하세요.
   - 예: "이 저널은 실험적 검증을 중시하므로, 이론적 서술만으로는 부족함. 구체적인 수치 데이터가 더 필요함."
4. **수정된 문단 (Revised Versions)**:
   - **Korean Revised**: 한국어로 재작성하되, 저널의 톤앤매너를 완벽하게 반영하세요.
   - **English Revised**: Formal Academic English로 재작성하되, 해당 분야에서 선호하는 전문 용어와 문장 구조를 사용하세요.

[출력 형식]
반드시 다음 JSON 형식으로 출력하세요:
{{"section": "...", "score": 8, "matches": ["구체적 일치점1 (한국어)", "구체적 일치점2 (한국어)"], "gaps": ["보완점1 (한국어)", "보완점2 (한국어)"], "revised": "저널 스타일에 완벽히 맞춘 수정본 (한국어)", "revised_en": "Revised paragraph in English (highly polished, journal-ready)"}}"""


DEFAULT_EXPANSION_PROMPT = """당신은 세계적인 석학이자 연구 전략 컨설턴트입니다. 이 문단의 주장을 훨씬 더 강력하고 파급력 있게 확장할 수 있는 'Next Level' 연구 방향을 제안하세요.

[문단]
{text}

{claim_section}

[Target Journal Context]
Journal: {journal_name}
Focus: {aims_scope}

[Strategic Directions]
다음 4가지 관점에서 주장을 확장하여 제안하세요:

1. **Theoretical Deepening (이론적 심화)**:
   - 현상에 대한 단순 관찰을 넘어, 근본적인 메커니즘이나 수학적 모델링으로 발전시키세요.
   - 예: "경험적 결과" -> "제 1원리 기반의 이론적 모델 수립"

2. **Methodological Generalization (방법론적 일반화)**:
   - 특정 케이스에만 적용되는 방법을 다양한 도메인이나 조건에서도 작동하도록 확장하세요.
   - 예: "특정 데이터셋 최적화" -> "다양한 분포에 강건한(Robust) 프레임워크"

3. **Practical Application / Impact (실용적 응용 및 파급력)**:
   - 연구 결과를 실제 산업이나 사회적 문제 해결에 어떻게 직접적으로 응용할 수 있을지 제안하세요.
   - 예: "알고리즘 개선" -> "실시간 엣지 디바이스 탑재를 위한 경량화 및 최적화"

4. **Interdisciplinary Fusion (다학제적 융합)**:
   - 다른 학문 분야(물리학, 생물학, 심리학 등)의 이론이나 방법론을 접목하여 새로운 시각을 제시하세요.
   - 예: "최적화 문제" -> "열역학적 엔트로피 개념 도입을 통한 수렴성 개선"

[각 방향별 필수 구성요소]
- **Type**: 위 4가지 전략 중 하나 선택 (e.g., "Theoretical Deepening")
- **Claim (영어)**: 이 방향으로 발전시켰을 때의 새로운 핵심 주장. **반드시 원어민 석학 수준의 세련된 학술 영어(English)로 2-3문장 작성하세요.**
- **Pro (장점)**: 이 방향이 왜 연구의 가치를 높이는지 (한국어).
- **Con (난관)**: 예상되는 어려움이나 한계점 (한국어).
- **Reason**: 왜 이 방향을 제안했는지에 대한 전략적 이유 (한국어). {journal_name}의 성향({aims_scope})과 연결하여 설명하세요.
- **Experiments**: 이 주장을 증명하기 위해 수행해야 할 **구체적인 실험이나 분석** (한국어).

[출력 형식]
반드시 다음 JSON 형식으로 출력하세요:
{{"section": "...", "directions": [{{"type": "...", "claim": "High-level academic English claim", "pro": "...", "con": "...", "reason": "...", "experiments": ["..."]}}, ...]}}"""


DEFAULT_REVIEWER_PROMPT = """당신은 IEEE/ACM 등 주요 공학 저널의 경험이 풍부한 리뷰어입니다. 다음 문단을 검토하고 저자에게 할 핵심 질문 3-5개와 긍정적인 칭찬 1개를 생성하세요.

[검토할 문단]
{text}

[Section 파악]
먼저 이 문단이 논문의 어느 section에 속하는지 파악하세요. 가능한 section: Introduction, Related Work, Methodology, Results, Discussion, Conclusion, Abstract

[질문 생성 가이드]
다음 관점을 종합적으로 평가하여 질문을 생성하세요:
1. **실험 타당성**: 실험 설계, 데이터 수집, 변수 제어가 적절한가?
2. **비교 대상 적절성**: 베이스라인/비교 대상이 공정하고 관련성이 있는가?
3. **통계적 유의성**: 통계 분석이 적절하고 결과 해석이 타당한가?
4. **재현 가능성**: 실험/방법론이 충분히 상세히 설명되어 재현 가능한가?
5. **방법론의 신뢰성**: 사용된 방법론이 문제 해결에 적합한가?
6. **선행연구 대비 차별화**: 기존 연구와의 차별점이 명확하고 의미 있는가?
7. **주장의 근거**: 주장을 뒷받침하는 증거가 충분한가?

[긍정적인 칭찬 생성 가이드]
문단에서 잘된 점, 강점, 혁신적인 부분을 찾아 1개의 긍정적인 피드백을 생성하세요:
- 혁신적인 방법론이나 접근 방식
- 탄탄한 실험 설계나 검증
- 명확하고 논리적인 서술
- 선행연구 대비 의미 있는 기여
- 실용적이거나 이론적으로 중요한 발견

[Severity 판단 기준]
각 질문의 심각도를 정확히 판단하세요:
- **critical**: 논문의 핵심 주장을 근본적으로 반박하거나, 실험/방법론에 치명적 결함이 있어 수정 없이는 게재 불가능한 경우
- **major**: 논문의 품질에 큰 영향을 미치지만 수정 가능한 문제 (예: 추가 실험 필요, 비교 대상 부적절, 통계 분석 오류)
- **minor**: 논문의 품질에 작은 영향을 미치는 개선 사항 (예: 표현 개선, 추가 설명 필요, 참고문헌 보완)

[출력 요구사항]
- 질문 개수: 3-5개 (중요도에 따라 조절, critical이 0개일 수도 있음)
- 긍정적인 칭찬: 1개 (반드시 포함)
- 각 질문은 구체적이고 실행 가능해야 함
- **모든 질문, 이유, 칭찬은 반드시 한국어로 작성해야 합니다**
- severity는 각 질문의 실제 심각도를 정확히 판단하여 할당
- reason에는 왜 그 severity인지 명확히 설명

[출력 형식]
반드시 다음 JSON 형식으로 출력 (모든 텍스트는 한국어):
{{"section": "Introduction|Related Work|Methodology|Results|Discussion|Conclusion|Abstract", "questions": [{{"q": "구체적이고 실행 가능한 질문 (한국어)", "severity": "critical|major|minor", "reason": "이 severity를 선택한 구체적 이유 (한국어)"}}, ...], "positive_feedback": "긍정적인 칭찬 1개 (한국어, 잘된 점, 강점, 혁신적인 부분 등을 구체적으로 언급)"}}"""


DEFAULT_PRIOR_WORK_PROMPT = """당신은 공학 논문 심사위원으로서 선행연구와의 비교 분석을 수행합니다. 다음 문단과 관련 선행연구를 비교하여 겹침, 개선점, 차별화 전략을 도출하세요.

[분석할 문단]
{text}

[관련 선행연구 목록]
{prior_works}

[분석 지침]
1. **기존 연구와 겹치는 점 (2-3개)**: 
   - 어떤 선행연구의 어떤 부분과 겹치는가? (연구명, 저자, 핵심 방법/결과 명시)
   - 겹침의 정도는 어느 정도인가? (완전 중복 vs 부분적 유사)
   - 이 겹침이 문제가 되는 이유는 무엇인가?
2. **선행연구보다 나은 점 (2-3개)**:
   - 기술적 차별점: 어떤 기술/알고리즘/방법이 개선되었는가?
   - 방법론적 차별점: 실험 설계, 평가 방법 등이 어떻게 나은가?
   - 실험적 차별점: 데이터셋, 성능, 정확도 등이 어떻게 향상되었는가?
   - 각 개선점이 왜 의미 있는가? (정량적/정성적 근거)
3. **차별화 전략 제안 (2-3개)**:
   - 논문에서 강조해야 할 차별점은 무엇인가?
   - 어떤 추가 실험/분석으로 차별화를 입증할 수 있는가?
   - 저널 투고 시 어떤 부분을 강조해야 하는가?

[출력 형식]
JSON 형식으로만 출력:
{{"overlaps": [{{"aspect": "겹치는 부분 (예: 방법론, 실험 설계 등)", "prior_work": "관련 선행연구 (저자명 또는 제목)", "detail": "어떻게 겹치는지, 왜 문제인지 상세 설명"}}],
  "improvements": [{{"aspect": "개선점 (예: 정확도 향상, 계산 복잡도 감소 등)", "prior_work": "비교 대상 선행연구", "detail": "왜 나은지, 정량적/정성적 근거 포함"}}],
  "differentiation": ["실행 가능한 차별화 전략1", "실행 가능한 차별화 전략2"]}}"""


SEARCH_QUERY_PROMPT = """Extract 3-5 English keywords for academic paper search from this paragraph.

[Paragraph]
{text}

Output JSON only: {{"query": "keyword1 keyword2 keyword3"}}"""


DEFAULT_TRANSLATION_PROMPT = """당신은 학술 논문 전문 번역가입니다. 다음 영어 학술 문단을 자연스러운 한국어로 번역하세요.

[번역할 문단]
{text}

[번역 요구사항]
1. **의미 정확성**: 학술 논문의 정확한 의미를 보존하면서 자연스러운 한국어로 번역
2. **전문 용어 처리**: 
   - 일반적으로 통용되는 한국어 번역이 있으면 사용
   - 번역이 어색하거나 의미 전달이 부정확한 경우 영어 원문을 괄호로 표기
   - 예: "machine learning (기계 학습)" 또는 "딥러닝 (deep learning)"
3. **문장 구조**: 한국어 어순에 맞게 자연스럽게 재구성하되, 논리적 흐름 유지
4. **톤과 형식**: 학술적 톤과 형식성을 유지하며, 원문의 강조나 논조를 보존
5. **가독성**: 한국어 독자가 이해하기 쉽도록 명확하고 자연스러운 표현 사용

[출력 형식]
JSON 형식으로만 출력 (마크다운 코드블록 없이):
{{"translation": "번역된 한국어 문단"}}"""


# ============================================================
# 🗺️ 저널 등록용 Map-Reduce 프롬프트 (High Quality Profile 생성)
# ============================================================

ANALYZE_JOURNAL_THEMES_PROMPT = """당신은 저널 분석 전문가입니다. 다음 저널 정보를 바탕으로 핵심 테마와 독자 정보를 분석하세요.

[저널 정보]
이름: {journal_name}
Aims & Scope:
{aims_scope}

[분석 목표]
1. **핵심 키워드 추출**: 저널이 다루는 가장 중요한 기술적/학술적 키워드 5-10개를 추출하세요.
2. **타겟 독자 분석**: 이 저널을 주로 읽는 사람은 누구인가? (예: "반도체 공정 엔지니어", "임상 심리학자", "정책 입안자" 등 구체적으로)
3. **연구 범위 및 한계**: 이 저널이 선호하는 연구 주제와 반대로 배제하거나 덜 선호하는 주제는 무엇인지 파악하세요.

[출력 형식]
JSON 형식으로만 출력:
{{"keywords": ["키워드1", "키워드2"], "audience_description": "상세한 독자 분석", "scope_focus": "선호하는 연구 주제 설명", "out_of_scope": "배제하는 주제 설명"}}"""


ANALYZE_JOURNAL_STYLE_PROMPT = """당신은 학술 작문 컨설턴트입니다. 다음 저널의 Aims & Scope를 바탕으로 선호하는 논문 스타일과 톤을 분석하세요.

[저널 정보]
이름: {journal_name}
Aims & Scope:
{aims_scope}

[분석 목표]
1. **논리 전개 방식**: 이 저널은 어떤 식의 논리 전개를 선호하는가? (예: "실험적 증거 중심", "수학적 엄밀성", "응용 사례 위주", "이론적 고찰")
2. **문체 및 톤**: 선호하는 문체는 무엇인가? (예: "간결하고 명확한", "서사적인", "매우 전문적이고 기술적인")
3. **주의사항**: 저자들이 흔히 범하는 스타일 관련 실수나 피해야 할 표현 방식.

[출력 형식]
JSON 형식으로만 출력:
{{"logic_flow": "선호하는 논리 전개 방식", "writing_style": "문체 및 톤에 대한 상세 설명", "style_tips": ["팁1", "팁2"]}}"""


ANALYZE_JOURNAL_CRITERIA_PROMPT = """당신은 저널 심사위원장입니다. 다음 저널에 논문을 게재하기 위해 가장 중요한 심사 기준 3가지를 도출하세요.

[저널 정보]
이름: {journal_name}
Aims & Scope:
{aims_scope}

[사용자 커스텀 요구사항]
{custom_methodology}

[분석 목표]
심사위원들이 이 저널의 논문을 평가할 때 가장 중요하게 보는 3가지 기준(Criteria)을 정의하고, 각 기준별로 "어떤 질문을 던져야 하는지" 구체적으로 작성하세요.

[출력 형식]
JSON 형식으로만 출력:
{{"criteria": [{{"name": "기준명1", "description": "설명", "checklist": ["점검질문1", "점검질문2"]}}, ...]}}"""


SYNTHESIZE_JOURNAL_PROFILE_PROMPT = """당신은 저널 전략가입니다. 저널에 대한 여러 차원의 분석 결과를 종합하여 하나의 완벽한 '저널 페르소나(Profile)'를 생성하세요.

[입력 데이터]
이름: {journal_name}
테마 분석: {themes_json}
스타일 분석: {style_json}
심사 기준: {criteria_json}

[지시사항]
위의 정보를 종합하여, 향후 이 저널에 투고할 논문을 평가하고 피드백할 때 사용할 "마스터 기준"을 작성하세요.

[출력 형식]
JSON 형식으로만 출력:
{{"journal_name": "{journal_name}", "profile_summary": "저널 성격 요약", "core_competencies": ["핵심역량1", "핵심역량2"], "review_strategy": "이 저널을 위한 리뷰 전략 설명"}}"""


GENERATE_PROMPTS_FROM_PROFILE_PROMPT = """당신은 프롬프트 엔지니어링 전문가입니다. 다음 '저널 프로필'을 바탕으로, 실제 논문 문단을 분석할 때 사용할 최적의 프롬프트 세트를 작성하세요.

[저널 프로필]
{profile_json}

[생성할 프롬프트 목록]
1. **paraphrase**: 문단을 저널 스타일에 맞게 재작성.
   - 필수: `{{text}}` 플레이스홀더 포함.
   - 출력 지시: 반드시 JSON 형식(`{{"section": "...", "styles": [...]}}`)으로 출력하도록 작성.
2. **claim_check**: 과대해석 여부 및 주장 강도 평가.
   - 필수: `{{text}}` 플레이스홀더 포함.
   - 출력 지시: 반드시 JSON 형식(`{{"section": "...", "claim": "...", "score": 0, "issues": [], "suggestions": []}}`)으로 출력하도록 작성.
3. **journal_fit**: 저널 적합도 평가 (0-10점).
   - 필수: `{{text}}`, `{{journal_name}}` 플레이스홀더 포함.
   - 출력 지시: 반드시 JSON 형식(`{{"section": "...", "score": 0, "matches": [], "gaps": [], "revised": "...", "revised_en": "..."}}`)으로 출력하도록 작성.
4. **expansion**: 주장 확장 및 업그레이드 제안.
   - 필수: `{{text}}`, `{{claim}}` 플레이스홀더 포함.
   - 출력 지시: 반드시 JSON 형식(`{{"section": "...", "directions": [...]}}`)으로 출력하도록 작성.
   - "Next Level" 연구 방향 제안 강조.
5. **reviewer**: 까다로운 심사위원의 질문 생성.
   - 필수: `{{text}}` 플레이스홀더 포함.
   - 출력 지시: 반드시 JSON 형식(`{{"section": "...", "positive_feedback": "...", "questions": [...]}}`)으로 출력하도록 작성.

[출력 형식]
JSON 형식으로만 출력 (모든 값은 긴 문자열이어야 합니다):
{{
  "prompts": {{
    "paraphrase": "지시사항... {{text}}... 반성... JSON 포맷...",
    "claim_check": "지시사항... {{text}}... JSON 포맷...",
    "journal_fit": "지시사항... {{text}}... {{journal_name}}... JSON 포맷...",
    "expansion": "지시사항... {{text}}... {{claim}}... JSON 포맷...",
    "reviewer": "지시사항... {{text}}... JSON 포맷..."
  }}
}}"""
