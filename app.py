import base64
import io
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(page_title="Opisywanie schematów", page_icon="📐",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """
    <style>
      .block-container{padding:3rem 0.75rem 0 0.75rem;max-width:100%}
      [data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],
      [data-testid="collapsedControl"]{display:none}
    </style>
    """,
    unsafe_allow_html=True)

has_file = st.session_state.get("uploader") is not None
with st.expander("📐 Wgraj / zmień grafikę", expanded=not has_file):
    up = st.file_uploader("Wgraj grafikę", type=["png", "jpg", "jpeg", "webp"],
                          key="uploader", label_visibility="collapsed")
    st.caption("Cała edycja odbywa się w przeglądarce. Po zmianie grafiki opisy znikną, "
               "więc wcześniej zapisz projekt (.json).")

if up is None:
    st.info("☝️ Wgraj grafikę powyżej, aby zacząć.")
    st.stop()

raw = up.getvalue()
mime = up.type or "image/png"
im = Image.open(io.BytesIO(raw))
if len(raw) > 6_000_000 or max(im.size) > 5000:   # odchudzenie bardzo dużych plików
    im = im.convert("RGB")
    im.thumbnail((5000, 5000))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95)
    raw, mime = buf.getvalue(), "image/jpeg"

data_url = f"data:{mime};base64,{base64.b64encode(raw).decode()}"
html = (Path(__file__).parent / "editor.html").read_text(encoding="utf-8")
html = html.replace("__IMAGE__", json.dumps(data_url)).replace("__NAME__", json.dumps(up.name))

components.html(html, height=900, scrolling=False)
