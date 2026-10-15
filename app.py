import base64
import io
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(page_title="Opisywanie schematów", page_icon="📐",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(
    "<style>.block-container{padding:0.5rem 0.5rem 0 0.5rem;max-width:100%}"
    "header[data-testid='stHeader']{height:0;visibility:hidden}</style>",
    unsafe_allow_html=True)

up = st.sidebar.file_uploader("📐 Wgraj grafikę", type=["png", "jpg", "jpeg", "webp"])
st.sidebar.caption("Cała edycja odbywa się w przeglądarce. Po wgraniu zwiń ten panel (strzałka u góry), "
                   "aby mieć więcej miejsca.")

if up is None:
    st.info("⬅️ Wgraj grafikę w panelu bocznym, aby zacząć.")
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
import json
html = (Path(__file__).parent / "editor.html").read_text(encoding="utf-8")
html = html.replace("__IMAGE__", json.dumps(data_url)).replace("__NAME__", json.dumps(up.name))

components.html(html, height=940, scrolling=False)
