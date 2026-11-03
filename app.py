import os
from pathlib import Path

import openai
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL") or "gpt-6-astra"

# 버튼 라벨 → API에 넘길 언어명
LANGUAGES = {"영어": "English", "일본어": "Japanese", "베트남어": "Vietnamese"}
# 버튼 보조 표기 (국기 이모지는 Windows에서 "US" 같은 글자로 보여서 각 언어의 자국어 이름을 사용)
NATIVE_NAMES = {"영어": "English", "일본어": "日本語", "베트남어": "Tiếng Việt"}
MAX_CHARS = 5000

SYSTEM_PROMPT = (
    "You are a professional translator.\n"
    "Translate the user's text into {target_language}.\n"
    "Output only the translated text without any explanations, notes, or quotation marks.\n"
    "Preserve the original line breaks, paragraph structure, and tone."
)


class TranslationError(Exception):
    """사용자에게 그대로 보여줄 한국어 메시지를 담는 예외."""


@st.cache_resource
def get_client(api_key: str) -> openai.OpenAI:
    return openai.OpenAI(api_key=api_key)


def translate(text: str, target_language: str) -> str:
    if not API_KEY:
        raise TranslationError(".env 파일에 OPENAI_API_KEY를 설정해 주세요.")
    try:
        response = get_client(API_KEY).chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(target_language=target_language)},
                {"role": "user", "content": text},
            ],
        )
    except openai.AuthenticationError:
        raise TranslationError("API 키가 올바르지 않습니다. .env 파일을 확인해 주세요.")
    except openai.NotFoundError:
        raise TranslationError("모델을 찾을 수 없습니다. .env의 OPENAI_MODEL 값을 확인해 주세요.")
    except openai.RateLimitError:
        raise TranslationError("요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")
    except openai.APIConnectionError:
        raise TranslationError("네트워크 연결에 실패했습니다. 인터넷 연결을 확인해 주세요.")
    except Exception as e:
        raise TranslationError(f"번역 중 오류가 발생했습니다: {e}")
    return (response.choices[0].message.content or "").strip()


def handle_click(label: str, text: str) -> None:
    st.session_state.error = None
    st.session_state.warning = None
    if not text.strip():
        st.session_state.warning = "번역할 글을 입력해 주세요."
        return
    with st.spinner("번역 중..."):
        try:
            st.session_state.result = translate(text, LANGUAGES[label])
            st.session_state.result_lang = label
        except TranslationError as e:
            st.session_state.error = str(e)


CSS = """
<style>
.block-container { max-width: 760px; padding-top: 2.5rem; }
h1 { margin-bottom: 0 !important; word-break: keep-all; }
@media (max-width: 640px) {
    h1 { font-size: 1.9rem !important; }
}
div[data-testid="stButton"] button {
    border-radius: 999px;
    font-weight: 600;
    transition: transform .08s ease, border-color .15s ease, color .15s ease;
}
div[data-testid="stButton"] button:hover { transform: translateY(-1px); }
.empty-hint { opacity: .55; text-align: center; padding: 1.5rem 0; margin: 0; }
</style>
"""


def render_sidebar() -> None:
    with st.sidebar:
        st.header("사용 방법")
        st.markdown(
            "1. 번역할 글을 입력합니다.\n"
            "2. 원하는 언어 버튼을 누릅니다.\n"
            "3. 결과 오른쪽 위 아이콘으로 복사합니다.\n\n"
            "원문 언어는 자동으로 인식됩니다."
        )
        st.divider()
        st.caption("사용 중인 모델")
        st.code(MODEL, language=None)


def render() -> None:
    st.set_page_config(page_title="다국어 번역기", page_icon="🌐", layout="centered")
    for key in ("result", "result_lang", "error", "warning"):
        st.session_state.setdefault(key, None)

    st.markdown(CSS, unsafe_allow_html=True)
    render_sidebar()

    st.title("🌐 다국어 번역기")
    st.caption("글을 입력하고 원하는 언어 버튼을 누르세요")

    text = st.text_area(
        "번역할 글",
        height=180,
        placeholder="여기에 번역할 글을 입력하세요",
        label_visibility="collapsed",
        max_chars=MAX_CHARS,  # 입력하는 동안 실시간으로 갱신되는 글자 수 표시
    )

    for col, label in zip(st.columns(3), LANGUAGES):
        is_last = label == st.session_state.result_lang
        if col.button(
            f"{label} · {NATIVE_NAMES[label]}",
            key=f"btn_{label}",
            type="primary" if is_last else "secondary",
            width="stretch",
        ):
            handle_click(label, text)
            st.rerun()  # 마지막 언어 버튼 강조를 바로 반영

    if st.session_state.warning:
        st.warning(st.session_state.warning, icon="⚠️")
    if st.session_state.error:
        st.error(st.session_state.error, icon="🚫")

    with st.container(border=True):
        if st.session_state.result is not None:
            st.markdown(f"**번역 결과 · {st.session_state.result_lang}**")
            st.code(st.session_state.result, language=None, wrap_lines=True)
        else:
            st.markdown('<p class="empty-hint">여기에 번역 결과가 표시됩니다</p>', unsafe_allow_html=True)


render()
