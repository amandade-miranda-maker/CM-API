import colorsys
import random
from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

# =========================================================
# 1. Configuração da Página
# =========================================================
st.set_page_config(
    page_title="Monitor de Cotações",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# 2. Paletas de Cores (presets) e estado inicial
# =========================================================
PALETAS = {
    "🌊 Oceano Noturno": dict(fundo="#0F172A", card="#1E293B", lateral="#111C33", texto="#F8FAFC", destaque="#10B981", positivo="#10B981", negativo="#F43F5E"),
    "🔮 Neon Roxo": dict(fundo="#0B0618", card="#1A1030", lateral="#130A26", texto="#F5F3FF", destaque="#A855F7", positivo="#34D399", negativo="#FB7185"),
    "🌅 Pôr do Sol": dict(fundo="#1C1017", card="#2D1B24", lateral="#231319", texto="#FFF1E6", destaque="#FB923C", positivo="#4ADE80", negativo="#F87171"),
    "🌲 Floresta": dict(fundo="#0B1410", card="#14241C", lateral="#0F1C16", texto="#ECFDF5", destaque="#84CC16", positivo="#4ADE80", negativo="#F87171"),
    "🪙 Ouro & Carvão": dict(fundo="#121212", card="#1E1E1E", lateral="#171717", texto="#FAFAFA", destaque="#FACC15", positivo="#4ADE80", negativo="#F87171"),
    "☀️ Claro Minimalista": dict(fundo="#F8FAFC", card="#FFFFFF", lateral="#E2E8F0", texto="#0F172A", destaque="#2563EB", positivo="#16A34A", negativo="#DC2626"),
}
OPCOES_PRESET = list(PALETAS.keys()) + ["🎛️ Personalizada"]
CHAVES_COR = ["fundo", "card", "lateral", "texto", "destaque", "positivo", "negativo"]
ROTULOS_COR = {
    "fundo": "Fundo",
    "card": "Cards",
    "lateral": "Barra lateral",
    "texto": "Texto",
    "destaque": "Destaque",
    "positivo": "Alta (positivo)",
    "negativo": "Queda (negativo)",
}


def hls_hex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, l, s)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(h, a):
    r, g, b = hex_rgb(h)
    return f"rgba({r},{g},{b},{a})"


def texto_sobre(h):
    """Escolhe preto ou branco para ter contraste sobre a cor informada."""
    r, g, b = hex_rgb(h)
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#0B0B0B" if lum > 0.6 else "#FFFFFF"


def aplicar_preset():
    nome = st.session_state.get("preset")
    if nome in PALETAS:
        for k, v in PALETAS[nome].items():
            st.session_state[f"cor_{k}"] = v


def paleta_aleatoria():
    h = random.random()
    escuro = random.random() > 0.2
    if escuro:
        novas = dict(
            fundo=hls_hex(h, 0.07, 0.40),
            card=hls_hex(h, 0.13, 0.35),
            lateral=hls_hex(h, 0.10, 0.38),
            texto=hls_hex(h, 0.96, 0.30),
            destaque=hls_hex(h + random.choice([0.0, 0.08, 0.5]), 0.58, 0.80),
        )
    else:
        novas = dict(
            fundo=hls_hex(h, 0.97, 0.40),
            card="#FFFFFF",
            lateral=hls_hex(h, 0.90, 0.35),
            texto=hls_hex(h, 0.12, 0.40),
            destaque=hls_hex(h + random.choice([0.0, 0.08, 0.5]), 0.42, 0.75),
        )
    for k, v in novas.items():
        st.session_state[f"cor_{k}"] = v
    st.session_state["preset"] = "🎛️ Personalizada"


if "preset" not in st.session_state:
    st.session_state["preset"] = "🌊 Oceano Noturno"
    aplicar_preset()

# =========================================================
# 3. Mapeamento de Moedas
# =========================================================
MOEDAS = {
    "Tradicionais": {
        "🇺🇸 Dólar Americano (USD)": "USD-BRL",
        "🇪🇺 Euro (EUR)": "EUR-BRL",
        "🇬🇧 Libra Esterlina (GBP)": "GBP-BRL",
        "🇦🇷 Peso Argentino (ARS)": "ARS-BRL",
        "🇯🇵 Iene Japonês (JPY)": "JPY-BRL",
        "🇨🇦 Dólar Canadense (CAD)": "CAD-BRL",
        "🇦🇺 Dólar Australiano (AUD)": "AUD-BRL",
        "🇨🇭 Franco Suíço (CHF)": "CHF-BRL",
        "🇨🇳 Yuan Chinês (CNY)": "CNY-BRL",
    },
    "Criptomoedas": {
        "₿ Bitcoin (BTC)": "BTC-BRL",
        "⟠ Ethereum (ETH)": "ETH-BRL",
        "Ł Litecoin (LTC)": "LTC-BRL",
        "✕ XRP (XRP)": "XRP-BRL",
        "🐕 Dogecoin (DOGE)": "DOGE-BRL",
    },
}
TODOS_PARES = {cod: nome for cat in MOEDAS.values() for nome, cod in cat.items()}

# =========================================================
# 4. Funções utilitárias e de consulta
# =========================================================
API = "https://economia.awesomeapi.com.br/json"


def fmt_num(v, casas=2):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_brl(v):
    return "R$ " + fmt_num(v, 2 if abs(v) >= 1 else 4)


@st.cache_data(ttl=10, show_spinner=False)
def buscar_cotacoes(pares: tuple):
    url = f"{API}/last/{','.join(pares)}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.json(), None
        if r.status_code == 404:
            return None, "Moeda não encontrada ou indisponível no momento."
        return None, f"Erro na requisição (código {r.status_code})."
    except Exception as e:
        return None, f"Erro de conexão com o servidor: {e}"


@st.cache_data(ttl=300, show_spinner=False)
def buscar_historico(par: str, dias: int):
    url = f"{API}/daily/{par}/{dias}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None, f"Erro ao buscar histórico (código {r.status_code})."
        linhas = [
            {
                "data": datetime.fromtimestamp(int(i["timestamp"])),
                "bid": float(i["bid"]),
                "high": float(i["high"]),
                "low": float(i["low"]),
            }
            for i in r.json()
        ]
        if not linhas:
            return None, "Sem dados históricos para este período."
        return pd.DataFrame(linhas).sort_values("data").reset_index(drop=True), None
    except Exception as e:
        return None, f"Erro de conexão com o servidor: {e}"


def tabela_html(cabecalho, linhas):
    th = "".join(f"<th>{c}</th>" for c in cabecalho)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


# =========================================================
# 5. Barra Lateral
# =========================================================
st.sidebar.title("🔍 Seleção de Câmbio")

categoria = st.sidebar.radio("Tipo de moeda:", list(MOEDAS.keys()), horizontal=True)
opcoes_moeda = MOEDAS[categoria]
nome_moeda = st.sidebar.selectbox("Escolha a moeda:", list(opcoes_moeda.keys()))
codigo_moeda = opcoes_moeda[nome_moeda]
eh_cripto = categoria == "Criptomoedas"

st.sidebar.divider()
st.sidebar.subheader("⏱️ Atualização")
auto = st.sidebar.toggle("Atualizar automaticamente", value=False)
intervalo = st.sidebar.select_slider("Intervalo (segundos)", options=[10, 15, 30, 60], value=30, disabled=not auto)
if st.sidebar.button("🔄 Atualizar agora", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
with st.sidebar.expander("🎨 Paleta de Cores", expanded=True):
    st.selectbox("Tema pronto", OPCOES_PRESET, key="preset", on_change=aplicar_preset)
    c1, c2 = st.columns(2)
    for i, chave in enumerate(CHAVES_COR):
        with (c1 if i % 2 == 0 else c2):
            st.color_picker(ROTULOS_COR[chave], key=f"cor_{chave}")
    st.button("🎲 Paleta aleatória", on_click=paleta_aleatoria, use_container_width=True)
    cores_atuais = {k: st.session_state[f"cor_{k}"] for k in CHAVES_COR}
    st.caption("Códigos da paleta atual:")
    st.code("\n".join(f"{k:<9} {v}" for k, v in cores_atuais.items()), language="text")

P = {k: st.session_state[f"cor_{k}"] for k in CHAVES_COR}

# =========================================================
# 6. CSS dinâmico (gerado a partir da paleta)
# =========================================================
CSS = """
<style>
.stApp { background-color: __FUNDO__; color: __TEXTO__; }
header[data-testid="stHeader"] { background: transparent; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label,
.stApp li, [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"] p, .stApp [data-testid="stSidebar"] span { color: __TEXTO__; }
section[data-testid="stSidebar"] { background-color: __LATERAL__; border-right: 1px solid __BORDA__; }
hr { border-color: __BORDA__ !important; }

/* Inputs */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, .stNumberInput input {
    background-color: __CARD__ !important; color: __TEXTO__ !important; border-color: __BORDA__ !important; }
div[data-baseweb="select"] svg { fill: __TEXTO__; }
[data-testid="stExpander"] { background: __CARD__; border: 1px solid __BORDA__; border-radius: 12px; }
[data-testid="stExpander"] summary p { color: __TEXTO__; font-weight: 600; }
pre, code { background: __FUNDO__ !important; color: __TEXTO__ !important; }

/* Botões */
.stButton > button {
    background-color: __DESTAQUE__; color: __SOBRE__; border: none; border-radius: 10px;
    font-weight: 600; transition: all .2s ease; }
.stButton > button:hover { filter: brightness(1.12); transform: translateY(-1px);
    box-shadow: 0 6px 18px __DESTAQUE_SOMBRA__; color: __SOBRE__; }
.stButton > button p { color: __SOBRE__ !important; }

/* Abas */
.stTabs [data-baseweb="tab"] p { color: __TEXTO__; font-weight: 600; }
.stTabs [aria-selected="true"] p { color: __DESTAQUE__; }
.stTabs [data-baseweb="tab-highlight"] { background-color: __DESTAQUE__; }
.stTabs [data-baseweb="tab-border"] { background-color: __BORDA__; }

/* Cards */
.card {
    background: __CARD__; border: 1px solid __BORDA__; border-radius: 16px;
    padding: 18px 22px; box-shadow: 0 8px 24px rgba(0,0,0,.15);
    transition: all .2s ease; height: 100%; }
.card:hover { transform: translateY(-3px); border-color: __DESTAQUE__;
    box-shadow: 0 12px 28px __DESTAQUE_SOMBRA__; }
.card-label { font-size: .8rem; opacity: .7; text-transform: uppercase; letter-spacing: .06em; }
.card-value { font-size: 2rem; font-weight: 800; margin-top: 4px; color: __DESTAQUE__; line-height: 1.15; }
.card-value.sm { font-size: 1.45rem; color: __TEXTO__; }
.card-delta { font-size: .95rem; font-weight: 700; margin-top: 6px; }
.hero { background: linear-gradient(135deg, __CARD__ 0%, __DESTAQUE_FRACO__ 100%); }

/* Faixa do dia */
.faixa { position: relative; height: 10px; border-radius: 99px; margin: 14px 0 6px;
    background: linear-gradient(90deg, __NEGATIVO__, __POSITIVO__); }
.faixa-marca { position: absolute; top: -5px; width: 20px; height: 20px; border-radius: 50%;
    background: __TEXTO__; border: 4px solid __DESTAQUE__; transform: translateX(-50%); }
.faixa-legenda { display: flex; justify-content: space-between; font-size: .8rem; opacity: .75; }

/* Tabela */
.tbl-wrap { border: 1px solid __BORDA__; border-radius: 14px; overflow-x: auto; background: __CARD__; }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { text-align: left; padding: 12px 16px; font-size: .78rem; text-transform: uppercase;
    letter-spacing: .06em; opacity: .7; border-bottom: 1px solid __BORDA__; }
.tbl td { padding: 12px 16px; border-bottom: 1px solid __BORDA__; }
.tbl tr:last-child td { border-bottom: none; }
.tbl tbody tr:hover { background: __DESTAQUE_FRACO__; }

/* Alertas */
div[data-testid="stAlert"] { border-radius: 12px; }
</style>
"""
SUBST = {
    "__FUNDO__": P["fundo"],
    "__CARD__": P["card"],
    "__LATERAL__": P["lateral"],
    "__TEXTO__": P["texto"],
    "__DESTAQUE__": P["destaque"],
    "__POSITIVO__": P["positivo"],
    "__NEGATIVO__": P["negativo"],
    "__SOBRE__": texto_sobre(P["destaque"]),
    "__BORDA__": rgba(P["texto"], 0.12),
    "__DESTAQUE_SOMBRA__": rgba(P["destaque"], 0.30),
    "__DESTAQUE_FRACO__": rgba(P["destaque"], 0.10),
}
for token, valor in SUBST.items():
    CSS = CSS.replace(token, valor)
st.markdown(CSS, unsafe_allow_html=True)

# =========================================================
# 7. Painel Principal
# =========================================================
st.title("📊 Monitor de Cotações")
st.caption("Acompanhe, compare e converta moedas em tempo real via AwesomeAPI.")

aba_cotacao, aba_hist, aba_comp, aba_conv = st.tabs(
    ["💵 Cotação", "📈 Histórico", "⚖️ Comparar", "🔁 Conversor"]
)

# ---------------------------------------------------------
# Aba 1 - Cotação atual
# ---------------------------------------------------------
def renderizar_cotacao():
    dados, erro = buscar_cotacoes((codigo_moeda,))
    if erro:
        st.error(f"❌ {erro}")
        st.info("Dica: verifique se a sua conexão com a internet está ativa.")
        return
    d = dados.get(codigo_moeda.replace("-", ""))
    if not d:
        st.warning("A API não retornou dados para esta moeda.")
        return

    bid = float(d["bid"])
    ask = float(d.get("ask", bid))
    high = float(d.get("high", bid))
    low = float(d.get("low", bid))
    var = float(d.get("pctChange", 0))
    cor_var = P["positivo"] if var >= 0 else P["negativo"]
    seta = "▲" if var >= 0 else "▼"

    st.subheader(f"Cotação: {d.get('name', nome_moeda)}")

    c1, c2, c3 = st.columns([1.4, 1, 1])
    c1.markdown(
        f'<div class="card hero"><div class="card-label">Valor atual (compra)</div>'
        f'<div class="card-value">{fmt_brl(bid)}</div>'
        f'<div class="card-delta" style="color:{cor_var}">{seta} {fmt_num(abs(var), 2)}% (24h)</div></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div class="card"><div class="card-label">Venda</div>'
        f'<div class="card-value sm">{fmt_brl(ask)}</div>'
        f'<div class="card-delta" style="opacity:.7">Spread: {fmt_brl(ask - bid)}</div></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="card"><div class="card-label">Máx. / Mín. do dia</div>'
        f'<div class="card-value sm" style="color:{P["positivo"]}">{fmt_brl(high)}</div>'
        f'<div class="card-value sm" style="color:{P["negativo"]}">{fmt_brl(low)}</div></div>',
        unsafe_allow_html=True,
    )

    st.write("")
    pos = 50 if high <= low else max(0, min(100, (bid - low) / (high - low) * 100))
    st.markdown(
        f'<div class="card"><div class="card-label">Posição no intervalo do dia</div>'
        f'<div class="faixa"><div class="faixa-marca" style="left:{pos:.1f}%"></div></div>'
        f'<div class="faixa-legenda"><span>Mín. {fmt_brl(low)}</span>'
        f'<span>{pos:.0f}% do intervalo</span><span>Máx. {fmt_brl(high)}</span></div></div>',
        unsafe_allow_html=True,
    )
    st.caption(f"🕒 Última atualização da API: {d.get('create_date', 'N/A')}"
               + (f" · atualizando a cada {intervalo}s" if auto else ""))


with aba_cotacao:
    if auto and hasattr(st, "fragment"):
        st.fragment(run_every=f"{intervalo}s")(renderizar_cotacao)()
    else:
        renderizar_cotacao()
        if auto:
            st.info("Atualize o Streamlit (>= 1.37) para usar a atualização automática.")

# ---------------------------------------------------------
# Aba 2 - Histórico
# ---------------------------------------------------------
with aba_hist:
    st.subheader(f"Histórico: {nome_moeda}")
    h1, h2 = st.columns([2, 1])
    with h1:
        dias = st.select_slider("Período (dias)", options=[7, 15, 30, 60, 90, 180], value=30)
    with h2:
        mostrar_faixa = st.checkbox("Mostrar máxima/mínima diárias", value=False)

    df, erro = buscar_historico(codigo_moeda, dias)
    if erro:
        st.error(f"❌ {erro}")
    else:
        variacao_periodo = (df["bid"].iloc[-1] / df["bid"].iloc[0] - 1) * 100
        cor_p = P["positivo"] if variacao_periodo >= 0 else P["negativo"]
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="card"><div class="card-label">Variação no período</div>'
                    f'<div class="card-value sm" style="color:{cor_p}">{"▲" if variacao_periodo >= 0 else "▼"} {fmt_num(abs(variacao_periodo))}%</div></div>',
                    unsafe_allow_html=True)
        k2.markdown(f'<div class="card"><div class="card-label">Máxima</div>'
                    f'<div class="card-value sm">{fmt_brl(df["high"].max())}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="card"><div class="card-label">Mínima</div>'
                    f'<div class="card-value sm">{fmt_brl(df["low"].min())}</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="card"><div class="card-label">Média</div>'
                    f'<div class="card-value sm">{fmt_brl(df["bid"].mean())}</div></div>', unsafe_allow_html=True)
        st.write("")

        y_escala = alt.Scale(zero=False)
        base = alt.Chart(df).encode(
            x=alt.X("data:T", title=None),
            y=alt.Y("bid:Q", title=None, scale=y_escala),
            tooltip=[
                alt.Tooltip("data:T", title="Data", format="%d/%m/%Y"),
                alt.Tooltip("bid:Q", title="Fechamento", format=",.4f"),
                alt.Tooltip("high:Q", title="Máxima", format=",.4f"),
                alt.Tooltip("low:Q", title="Mínima", format=",.4f"),
            ],
        )
        camadas = [
            base.mark_area(opacity=0.18, color=P["destaque"]),
            base.mark_line(color=P["destaque"], strokeWidth=3),
            base.mark_circle(color=P["destaque"], size=45),
        ]
        if mostrar_faixa:
            camadas.append(alt.Chart(df).mark_line(color=P["positivo"], strokeDash=[5, 4]).encode(
                x="data:T", y=alt.Y("high:Q", scale=y_escala)))
            camadas.append(alt.Chart(df).mark_line(color=P["negativo"], strokeDash=[5, 4]).encode(
                x="data:T", y=alt.Y("low:Q", scale=y_escala)))
        grafico = (
            alt.layer(*camadas)
            .properties(height=380)
            .configure(background=P["card"])
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=P["texto"], gridColor=rgba(P["texto"], 0.10),
                            domainColor=rgba(P["texto"], 0.25), tickColor=rgba(P["texto"], 0.25))
        )
        st.altair_chart(grafico, use_container_width=True, theme=None)

# ---------------------------------------------------------
# Aba 3 - Comparar
# ---------------------------------------------------------
with aba_comp:
    st.subheader("Comparativo de moedas")
    dados_all, erro = buscar_cotacoes(tuple(TODOS_PARES.keys()))
    if erro:
        st.error(f"❌ {erro}")
    else:
        registros = []
        for cod, nome in TODOS_PARES.items():
            d = dados_all.get(cod.replace("-", ""))
            if d:
                registros.append({
                    "nome": nome,
                    "bid": float(d["bid"]),
                    "var": float(d.get("pctChange", 0)),
                    "high": float(d.get("high", 0)),
                    "low": float(d.get("low", 0)),
                })
        dfc = pd.DataFrame(registros)

        ordem = st.radio("Ordenar por:", ["Maior alta", "Maior queda", "Nome"], horizontal=True)
        if ordem == "Maior alta":
            dfc = dfc.sort_values("var", ascending=False)
        elif ordem == "Maior queda":
            dfc = dfc.sort_values("var", ascending=True)
        else:
            dfc = dfc.sort_values("nome")

        linhas = []
        for _, r in dfc.iterrows():
            cor = P["positivo"] if r["var"] >= 0 else P["negativo"]
            linhas.append([
                r["nome"],
                f"<b>{fmt_brl(r['bid'])}</b>",
                f'<span style="color:{cor};font-weight:700">{"▲" if r["var"] >= 0 else "▼"} {fmt_num(abs(r["var"]))}%</span>',
                fmt_brl(r["high"]),
                fmt_brl(r["low"]),
            ])
        st.markdown(tabela_html(["Moeda", "Compra", "Var. 24h", "Máxima", "Mínima"], linhas),
                    unsafe_allow_html=True)

        st.write("")
        barras = (
            alt.Chart(dfc)
            .mark_bar(cornerRadiusEnd=6)
            .encode(
                x=alt.X("var:Q", title="Variação 24h (%)"),
                y=alt.Y("nome:N", sort=list(dfc["nome"]), title=None),
                color=alt.condition(alt.datum.var >= 0, alt.value(P["positivo"]), alt.value(P["negativo"])),
                tooltip=[alt.Tooltip("nome:N", title="Moeda"), alt.Tooltip("var:Q", title="Variação %", format=".2f")],
            )
            .properties(height=max(260, 30 * len(dfc)))
            .configure(background=P["card"])
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=P["texto"], titleColor=P["texto"],
                            gridColor=rgba(P["texto"], 0.10), domainColor=rgba(P["texto"], 0.25))
        )
        st.altair_chart(barras, use_container_width=True, theme=None)

# ---------------------------------------------------------
# Aba 4 - Conversor
# ---------------------------------------------------------
with aba_conv:
    st.subheader(f"Conversor: BRL ⇄ {nome_moeda}")
    dados_c, erro = buscar_cotacoes((codigo_moeda,))
    if erro:
        st.error(f"❌ {erro}")
    else:
        d = dados_c.get(codigo_moeda.replace("-", ""))
        bid, ask = float(d["bid"]), float(d["ask"])
        sentido = st.radio("Sentido da conversão:", ["Moeda → BRL", "BRL → Moeda"], horizontal=True)
        valor = st.number_input("Valor a converter", min_value=0.0, value=100.0, step=10.0, format="%.2f")
        sigla = codigo_moeda.split("-")[0]
        casas = 8 if eh_cripto else 2

        if sentido == "Moeda → BRL":
            resultado = valor * bid
            texto_res = f"R$ {fmt_num(resultado, 2)}"
            detalhe = f"{fmt_num(valor, casas)} {sigla} × {fmt_brl(bid)} (compra)"
        else:
            resultado = valor / ask if ask else 0
            texto_res = f"{fmt_num(resultado, casas)} {sigla}"
            detalhe = f"R$ {fmt_num(valor)} ÷ {fmt_brl(ask)} (venda)"

        st.markdown(
            f'<div class="card hero"><div class="card-label">Resultado</div>'
            f'<div class="card-value">{texto_res}</div>'
            f'<div class="card-delta" style="opacity:.7">{detalhe}</div></div>',
            unsafe_allow_html=True,
        )
        st.caption("Valores de referência; spreads e taxas de corretoras podem alterar o valor final.")

st.divider()
st.caption("Dados fornecidos por AwesomeAPI · Feito com Streamlit 💚")