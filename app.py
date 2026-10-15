import io
import json

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

import labeler as lb

st.set_page_config(page_title="Opisywanie schematów", page_icon="📐", layout="wide")
COLS = ["text", "ax", "ay", "tx", "ty"]
S = st.session_state


# ---------------------------------------------------------------- pomocnicze
def make_table(labels):
    return pd.DataFrame(labels, columns=COLS)


def clean(df):
    out = []
    for r in df.to_dict("records"):
        text = r.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            vals = {k: int(r[k]) for k in ("ax", "ay", "tx", "ty")}
        except (TypeError, ValueError):
            continue
        out.append({"text": text.strip(), **vals})
    return out


def set_labels(labels):
    """Zmiana etykiet spoza edytora tabeli – wymusza przebudowanie tabeli."""
    S.labels = labels
    S.table = make_table(labels)
    S.ver += 1


def style_from_state():
    return dict(font_size=int(S.font_size), line_w=float(S.line_w), wrap_pct=int(S.wrap_pct),
                color=S.color, bg=S.bg, pads=(int(S.pl), int(S.pt), int(S.pr), int(S.pb)))


def cb_autofit():
    pl, pt, pr, pb = lb.autofit_pads(S.image, S.labels, {**style_from_state(), "pads": (0, 0, 0, 0)})
    S.pl, S.pt, S.pr, S.pb = pl, pt, pr, pb


def cb_align():
    labels = [dict(l) for l in S.labels]
    right = [l for l in labels if l["tx"] >= l["ax"]]
    left = [l for l in labels if l["tx"] < l["ax"]]
    if right:
        x = max(l["tx"] for l in right)
        for l in right:
            l["tx"] = x
    if left:
        x = min(l["tx"] for l in left)
        for l in left:
            l["tx"] = x
    set_labels(labels)


def cb_clear():
    S.pending = None
    set_labels([])


def cb_cancel():
    S.pending = None


# ------------------------------------------------------------------ plik
st.sidebar.title("📐 Opisywanie schematów")
up = st.sidebar.file_uploader("Wgraj grafikę", type=["png", "jpg", "jpeg", "webp"])
if up is None:
    st.info("⬅️ Wgraj grafikę w panelu bocznym, aby zacząć.")
    st.stop()

fid = f"{up.name}-{up.size}"
if S.get("fid") != fid:
    img = Image.open(up).convert("RGB")
    S.update(fid=fid, image=img, labels=[], table=make_table([]), ver=0, pending=None,
             last_click=None, export=None,
             font_size=max(14, round(img.width * 0.020)),
             line_w=max(1.5, round(img.width * 0.0013, 1)),
             wrap_pct=24, color="#222222", bg=lb.sample_bg(img),
             pl=0, pt=0, pr=0, pb=0)
image = S.image

# projekt – wczytanie (przed utworzeniem widgetów stylu)
with st.sidebar.expander("💾 Wczytaj projekt (.json)"):
    pj = st.file_uploader("Plik projektu", type=["json"], key="pj_up")
    if pj is not None and S.get("pj_id") != f"{pj.name}-{pj.size}":
        S.pj_id = f"{pj.name}-{pj.size}"
        data = json.load(pj)
        st_ = data.get("style", {})
        for key in ("font_size", "line_w", "wrap_pct", "color", "bg"):
            if key in st_:
                S[key] = st_[key]
        for key, v in zip(("pl", "pt", "pr", "pb"), st_.get("pads", (0, 0, 0, 0))):
            S[key] = int(v)
        set_labels(data.get("labels", []))
        st.rerun()

st.sidebar.subheader("Wygląd")
st.sidebar.number_input("Rozmiar tekstu (px)", 8, 400, key="font_size")
st.sidebar.number_input("Grubość linii (px)", 0.5, 20.0, step=0.5, key="line_w")
st.sidebar.slider("Maks. szerokość opisu (% szerokości)", 5, 100, key="wrap_pct")
st.sidebar.color_picker("Kolor linii i tekstu", key="color")

st.sidebar.subheader("Płótno – marginesy (px)")
c1, c2 = st.sidebar.columns(2)
c1.number_input("Lewy", 0, 5000, step=20, key="pl")
c2.number_input("Prawy", 0, 5000, step=20, key="pr")
c1.number_input("Górny", 0, 5000, step=20, key="pt")
c2.number_input("Dolny", 0, 5000, step=20, key="pb")
st.sidebar.color_picker("Kolor marginesów", key="bg")
st.sidebar.button("Dopasuj płótno do opisów", on_click=cb_autofit, use_container_width=True)

style = style_from_state()
pl, pt, pr, pb = style["pads"]

# ------------------------------------------------------------- układ
left, right = st.columns([3, 1.6], gap="large")

with right:
    st.subheader("Opisy")
    st.caption("Edytuj tekst i współrzędne, usuń wiersz (zaznacz → Delete). "
               "W tekście `|` = złamanie linii.")
    edited = st.data_editor(
        S.table, key=f"editor_{S.ver}", num_rows="dynamic", use_container_width=True,
        column_config={
            "text": st.column_config.TextColumn("Opis"),
            "ax": st.column_config.NumberColumn("Kropka X", step=1),
            "ay": st.column_config.NumberColumn("Kropka Y", step=1),
            "tx": st.column_config.NumberColumn("Opis X", step=1),
            "ty": st.column_config.NumberColumn("Opis Y", step=1),
        })
    S.labels = clean(edited)

    b1, b2 = st.columns(2)
    b1.button("Wyrównaj opisy", on_click=cb_align, use_container_width=True)
    b2.button("Wyczyść wszystko", on_click=cb_clear, use_container_width=True)

with left:
    st.text_input("Tekst następnego opisu (wpisz PRZED drugim kliknięciem)",
                  value="Nowy opis", key="new_text")
    if S.pending is None:
        st.info("**Krok 1:** kliknij na schemacie punkt, który ma wskazywać patyczek (kropka).")
    else:
        st.warning("**Krok 2:** kliknij miejsce, w którym ma stanąć opis.")
        st.button("Anuluj ten punkt", on_click=cb_cancel)

    scale = min(1.0, 1100 / (image.width + pl + pr))
    prev = lb.render(image, S.labels, style, scale, 2)

    # uchwyty pomocnicze – tylko w podglądzie
    dr = ImageDraw.Draw(prev)
    for l in S.labels:
        x, y = (l["ax"] + pl) * scale, (l["ay"] + pt) * scale
        dr.ellipse([x - 7, y - 7, x + 7, y + 7], outline="#2b7de9", width=2)
        x, y = (l["tx"] + pl) * scale, (l["ty"] + pt) * scale
        dr.rectangle([x - 5, y - 5, x + 5, y + 5], outline="#2b7de9", width=2)
    if S.pending:
        x, y = (S.pending[0] + pl) * scale, (S.pending[1] + pt) * scale
        dr.ellipse([x - 6, y - 6, x + 6, y + 6], fill="#e53935", outline="white", width=2)

    res = streamlit_image_coordinates(prev, key="schemat", width=prev.width)

    if res:
        sig = (res["x"], res["y"], res.get("unix_time"))
        if sig != S.last_click:
            S.last_click = sig
            fx = res["x"] * prev.width / res["width"]
            fy = res["y"] * prev.height / res["height"]
            x, y = int(fx / scale) - pl, int(fy / scale) - pt
            if S.pending is None:
                S.pending = (x, y)
                st.rerun()
            else:
                ax, ay = S.pending
                S.pending = None
                text = (S.get("new_text") or "").strip() or "Opis"
                set_labels(S.labels + [{"text": text, "ax": ax, "ay": ay, "tx": x, "ty": y}])
                st.rerun()

# ------------------------------------------------------------- eksport
st.divider()
e1, e2, e3 = st.columns(3)
if e1.button("🖼️ Wygeneruj PNG w pełnej rozdzielczości", type="primary"):
    with st.spinner("Renderowanie…"):
        final = lb.render(image, S.labels, style, 1.0, 3)
        buf = io.BytesIO()
        final.save(buf, format="PNG", dpi=(300, 300))
        S.export = buf.getvalue()
if S.get("export"):
    e2.download_button("⬇️ Pobierz PNG", S.export, file_name="schemat_opisany.png", mime="image/png")
e3.download_button(
    "💾 Pobierz projekt (.json)",
    json.dumps({"labels": S.labels, "style": style}, ensure_ascii=False, indent=2),
    file_name="projekt_opisow.json", mime="application/json")