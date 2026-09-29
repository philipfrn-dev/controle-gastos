import os
import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

st.set_page_config(page_title="Controle Mensal", layout="wide")

load_dotenv()

# Função auxiliar para ler secrets com segurança sem quebrar se o arquivo secrets.toml não existir
def get_secret(key: str, default=None):
    # 1. Tenta carregar de variável de ambiente / .env
    val = os.getenv(key)
    if val:
        return val
    # 2. Tenta carregar do Streamlit Secrets (nuvem / Render / Cloud)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default

# 100% Seguro (apenas lê de fora do código):
SENHA_ACESSO = get_secret("APP_PASSWORD")

if not SENHA_ACESSO:
    st.error("Variável de ambiente APP_PASSWORD não configurada no servidor!")
    st.stop()

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    col_lock1, col_lock2, col_lock3 = st.columns([1, 1.2, 1])
    with col_lock2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:24px; box-shadow:0 4px 6px rgba(0,0,0,0.05); text-align:center;">
            <h3 style="color:#0F172A; font-weight:800; margin-bottom:8px;">🔒 Acesso Restrito</h3>
            <p style="color:#64748B; font-size:13px; margin-bottom:16px;">Introduza a sua palavra-passe para aceder ao painel financeiro.</p>
        </div>
        """, unsafe_allow_html=True)
        pwd = st.text_input("Palavra-passe", type="password", label_visibility="collapsed")
        if st.button("Entrar no Sistema", use_container_width=True):
            if pwd == SENHA_ACESSO:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Palavra-passe incorreta.")
    st.stop()

# --- CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
RENDA_FIXA = float(get_secret("RENDA_MENSAL_FIXA", 3787.38))

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Credenciais do Supabase ausentes no arquivo .env ou Secrets!")
    st.stop()

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()
MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
OPCOES_CARTAO = ["NUBANK", "ITAU SIGNATURE", "MERCADO PAGO"]

if "mes_escolhido" not in st.session_state:
    st.session_state["mes_escolhido"] = MESES[datetime.now().month - 1]

def fmt(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_cache():
    st.cache_data.clear()

def calcular_cotas(valor_total: float, tipo_divisao: str):
    v = float(valor_total or 0.0)
    if tipo_divisao in ["50/50", "Dividido 50/50"]:
        minha_cota = round(v / 2.0, 2)
        terceiro_cota = round(v - minha_cota, 2)
        return minha_cota, terceiro_cota
    elif tipo_divisao in ["TERCEIRO", "100% Terceiro"]:
        return 0.0, round(v, 2)
    else:
        return round(v, 2), 0.0

CATEGORIAS_PADRAO = [
    "RESIDENCIAL",
    "ÁGUA",
    "COMPRAS APARTAMENTO",
    "FARMÁCIA",
    "ALIMENTAÇÃO",
    "ASSINATURAS / STREAMING",
    "OUTROS"
]

ICONES_CATEGORIAS = {
    "RESIDENCIAL": "🏠",
    "ÁGUA": "💧",
    "COMPRAS APARTAMENTO": "🛋️",
    "FARMÁCIA": "💊",
    "ALIMENTAÇÃO": "🛒",
    "ASSINATURAS / STREAMING": "🎬",
    "OUTROS": "📌"
}

@st.cache_data(ttl=300)
def carregar_categorias():
    try:
        cats_db_res = supabase.table("categorias").select("nome").execute().data
        cats_db = [c["nome"] for c in cats_db_res]
        for cat in CATEGORIAS_PADRAO:
            if cat not in cats_db:
                try:
                    supabase.table("categorias").insert({"nome": cat}).execute()
                except Exception:
                    pass
        return sorted(list(set(cats_db + CATEGORIAS_PADRAO)))
    except Exception:
        return CATEGORIAS_PADRAO

CATEGORIAS_FIXAS = carregar_categorias()

@st.cache_data(ttl=60)
def carregar_dados_mes(mes):
    try:
        pess = [p["nome"] for p in supabase.table("pessoas").select("nome").order("nome").execute().data]
    except Exception:
        pess = ["EDUARDO", "GUSTAVO", "CAMILA"]

    try:
        fats = supabase.table("faturas_mensais").select("*").eq("mes_referencia", mes).execute().data
    except Exception:
        fats = []

    try:
        desps = supabase.table("despesas").select("*").eq("mes_referencia", mes).execute().data
    except Exception:
        desps = []

    try:
        fixas = supabase.table("despesas_recorrentes").select("*").order("descricao").execute().data
    except Exception:
        fixas = []

    try:
        streams = supabase.table("streamings").select("*").order("nome_servico").execute().data
    except Exception:
        streams = []

    try:
        efetiv = supabase.table("efetivacao_fixas_mensais").select("*").eq("mes_referencia", mes).execute().data
    except Exception:
        efetiv = []

    try:
        reserva = supabase.table("reserva_mensal").select("valor").eq("mes_referencia", mes).execute().data
    except Exception:
        reserva = []

    return pess, fats, desps, fixas, streams, efetiv, reserva

# --- CSS MODERNO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }

    button[data-baseweb="tab"] {
        background-color: #E2E8F0 !important;
        color: #334155 !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 18px !important;
        margin-right: 4px !important;
        border: 1px solid #CBD5E1 !important;
        border-bottom: none !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border-color: #0F172A !important;
    }

    .top-capsule {
        background-color: #FFFFFF !important;
        border-radius: 12px;
        padding: 12px 16px;
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        align-items: center;
        margin-bottom: 18px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        border: 1px solid #E2E8F0;
    }
    .top-capsule-item {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .top-capsule span {
        font-size: 10px;
        font-weight: 800;
        color: #475569 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 1px;
    }
    .top-capsule strong {
        color: #0F172A !important;
        font-size: 15px;
        font-weight: 800;
        font-variant-numeric: tabular-nums;
    }

    .clean-card {
        background-color: #FFFFFF !important;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        border: 1px solid #E2E8F0;
    }

    .hero-neon-card {
        background: #F0FDF4 !important;
        border: 1px solid #86EFAC !important;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        color: #14532D !important;
    }

    .reserva-card {
        background: #F0FDFA !important;
        border: 1px solid #5EEAD4 !important;
        border-left: 3px solid #0F766E !important;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }

    .card-label-dark {
        font-size: 11px;
        font-weight: 800;
        color: #475569 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .card-label-light {
        font-size: 11px;
        font-weight: 800;
        color: #166534 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .val-large {
        font-size: 20px;
        font-weight: 800;
        letter-spacing: -0.5px;
        font-variant-numeric: tabular-nums;
        color: #0F172A !important;
    }

    .bento-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 122px;
        margin-bottom: 6px;
    }
    .bento-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
    }
    .bento-icon-title {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .bento-icon {
        font-size: 16px;
        background: #F1F5F9;
        border-radius: 6px;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .bento-title {
        font-size: 13px;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.2;
    }
    .bento-sub {
        font-size: 11px;
        color: #64748B;
        font-weight: 600;
    }
    .bento-badge-paid {
        background: #DCFCE7;
        color: #166534;
        font-size: 10px;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid #BBF7D0;
    }
    .bento-badge-open {
        background: #F1F5F9;
        color: #475569;
        font-size: 10px;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid #E2E8F0;
    }
    .bento-card-body {
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-top: 1px solid #F1F5F9;
        padding-top: 8px;
    }

    .clean-item-row {
        background-color: #FFFFFF !important;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #E2E8F0;
    }

    div[data-baseweb="select"] > div, input {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #0F172A !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
    }

    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border: 1px solid #0F172A !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        padding: 4px 12px !important;
        height: 34px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }

    button:has(p:contains("↺")), button:has(div:contains("↺")) {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
    }

    button:has(p:contains("✕")), button:has(div:contains("✕")) {
        background-color: #FEF2F2 !important;
        color: #991B1B !important;
        border: 1px solid #FECACA !important;
    }

    .block-header-align {
        font-size: 15px;
        font-weight: 800;
        color: #0F172A;
        margin: 0 0 10px 0;
        height: 24px;
        display: flex;
        align-items: center;
    }

    div[data-testid="stExpander"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        margin-top: -2px !important;
        margin-bottom: 12px !important;
        background: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO / FILTRO DE MÊS ---
col_logo, col_mes = st.columns([4, 1])
with col_logo:
    st.markdown("<h3 style='color:#0F172A; font-weight:800; margin:0;'>Controle Mensal</h3>", unsafe_allow_html=True)
with col_mes:
    mes_selecionado = st.selectbox(
        "", 
        MESES, 
        index=MESES.index(st.session_state["mes_escolhido"]), 
        label_visibility="collapsed",
        key="filtro_mes_selecao"
    )
    st.session_state["mes_escolhido"] = mes_selecionado

pessoas_cadastradas, faturas_data, res_despesas, fixas_res, streamings_res, efetivacoes_data, reserva_res = carregar_dados_mes(mes_selecionado)

# 1. FATURAS BRUTAS DOS CARTÕES
dict_faturas = {f["cartao_nome"]: float(f["valor_total_fatura"]) for f in faturas_data}
fat_nu_total = dict_faturas.get("NUBANK", 0.0)
fat_itau_total = dict_faturas.get("ITAU SIGNATURE", 0.0)
fat_mp_total = dict_faturas.get("MERCADO PAGO", 0.0)
total_faturas_bruto = fat_nu_total + fat_itau_total + fat_mp_total

# 2. GASTOS REGISTRADOS NA TABELA DESPESAS
df = pd.DataFrame(res_despesas) if res_despesas else pd.DataFrame()
if not df.empty and "valor_reembolso" in df.columns:
    reemb_nu = df[(df["cartao_nome"] == "NUBANK")]["valor_reembolso"].sum()
    reemb_itau = df[(df["cartao_nome"] == "ITAU SIGNATURE")]["valor_reembolso"].sum()
    reemb_mp = df[(df["cartao_nome"] == "MERCADO PAGO")]["valor_reembolso"].sum()
    total_reemb_cartoes = df["valor_reembolso"].sum()
else:
    reemb_nu = reemb_itau = reemb_mp = total_reemb_cartoes = 0.0

# 3. RECORRENTES & STREAMINGS
total_fixas_bruto = 0.0
total_stream_bruto = 0.0
fixas_minha_em_conta = 0.0
total_terceiros_fixas = 0.0

for f in fixas_res:
    v_tot = float(f.get("valor_estimado") or 0.0)
    div_t = f.get("divisao") or "MEU"
    meu, terc = calcular_cotas(v_tot, div_t)

    total_fixas_bruto += v_tot
    total_terceiros_fixas += terc
    fixas_minha_em_conta += meu

for s in streamings_res:
    v_tot = float(s.get("valor") or 0.0)
    div_t = s.get("divisao") or "MEU"
    meu, terc = calcular_cotas(v_tot, div_t)

    total_stream_bruto += v_tot
    total_terceiros_fixas += terc
    cartao_str = s.get("cartao_nome")
    if not cartao_str or "PIX" in cartao_str or "DÉBITO" in cartao_str:
        fixas_minha_em_conta += meu

set_fixas_cobradas = {e["item_id"] for e in efetivacoes_data if e["item_tipo"] == "CONTA_FIXA" and e["efetivado"]}
set_stream_cobrados = {e["item_id"] for e in efetivacoes_data if e["item_tipo"] == "STREAMING" and e["efetivado"]}
valor_reserva = float(reserva_res[0]["valor"]) if reserva_res else 0.0

# 4. SALDOS E FECHAMENTO
minha_parte_nu = max(0.0, fat_nu_total - reemb_nu)
minha_parte_itau = max(0.0, fat_itau_total - reemb_itau)
minha_parte_mp = max(0.0, fat_mp_total - reemb_mp)
meu_custo_cartoes = minha_parte_nu + minha_parte_itau + minha_parte_mp

total_compromissos_fixos_bruto = total_fixas_bruto + total_stream_bruto
total_reembolso_geral = total_reemb_cartoes + total_terceiros_fixas

sobra_final = RENDA_FIXA - fixas_minha_em_conta - meu_custo_cartoes - valor_reserva

# --- CAPSULE RESUMO TOPO ---
st.markdown(f"""
<div class="top-capsule">
    <div class="top-capsule-item"><span>Salário Base</span><strong>{fmt(RENDA_FIXA)}</strong></div>
    <div class="top-capsule-item"><span>Faturas Brutas</span><strong>{fmt(total_faturas_bruto)}</strong></div>
    <div class="top-capsule-item"><span>Total a Receber</span><strong style="color:#2563EB;">{fmt(total_reembolso_geral)}</strong></div>
    <div class="top-capsule-item"><span>Faturas Líquidas</span><strong>{fmt(meu_custo_cartoes)}</strong></div>
    <div class="top-capsule-item"><span>Fixas (em Conta)</span><strong>{fmt(fixas_minha_em_conta)}</strong></div>
    <div class="top-capsule-item"><span>Reserva</span><strong style="color:#0F766E;">{fmt(valor_reserva)}</strong></div>
    <div class="top-capsule-item"><span>Sobra Líquida</span><strong style="color:#15803D;">{fmt(sobra_final)}</strong></div>
</div>
""", unsafe_allow_html=True)

# --- ABAS DE NAVEGAÇÃO ---
tab_faturas, tab_cobrancas, tab_fixas, tab_demonstrativo = st.tabs([
    "💳 Faturas & Fechamento", 
    "👥 Terceiros & Cobranças", 
    "⚡ Contas Recorrentes & Assinaturas",
    "📊 Demonstrativo & Migração"
])

# =========================================================================
# ABA 1: FATURAS & FECHAMENTO
# =========================================================================
with tab_faturas:
    col_cards_faturas, col_sobra = st.columns([1.8, 1.2], gap="large")
    
    with col_cards_faturas:
        st.markdown('<div class="block-header-align">Detalhamento por Cartão</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3, gap="small")
        
        def render_bloco_fatura(nome_cartao, label, valor_fatura, valor_terceiros, minha_parte):
            st.markdown(f"""
            <div class="clean-card" style="height: 175px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div class="card-label-dark">{label}</div>
                    <div class="val-large">{fmt(valor_fatura)}</div>
                    <div style="font-size:12px; color:#2563EB; font-weight:800; margin-top:2px;">
                        - {fmt(valor_terceiros)} (Terceiros)
                    </div>
                </div>
                <div>
                    <hr style="border:none; border-top:1px solid #E2E8F0; margin:6px 0;">
                    <div class="card-label-dark" style="margin:0;">Seu Custo Real:</div>
                    <div style="font-size:16px; font-weight:800; color:#0F172A;">{fmt(minha_parte)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"Ajustar {label}"):
                with st.form(f"form_fat_{nome_cartao}", clear_on_submit=False):
                    novo_val = st.number_input("Valor Fechado", value=float(valor_fatura), min_value=0.0, step=50.0)
                    submit_fat = st.form_submit_button("Salvar Fatura")
                    if submit_fat:
                        supabase.table("faturas_mensais").upsert({
                            "mes_referencia": mes_selecionado,
                            "cartao_nome": nome_cartao,
                            "valor_total_fatura": novo_val
                        }, on_conflict="mes_referencia,cartao_nome").execute()
                        limpar_cache()
                        st.rerun()

        with c1:
            render_bloco_fatura("NUBANK", "Nubank", fat_nu_total, reemb_nu, minha_parte_nu)
        with c2:
            render_bloco_fatura("ITAU SIGNATURE", "Itaú Signature", fat_itau_total, reemb_itau, minha_parte_itau)
        with c3:
            render_bloco_fatura("MERCADO PAGO", "Mercado Pago", fat_mp_total, reemb_mp, minha_parte_mp)

    with col_sobra:
        st.markdown('<div class="block-header-align">Resumo do Mês & Reserva</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="hero-neon-card">
            <div class="card-label-light">Sobra Líquida Projetada</div>
            <div class="val-large" style="color:#14532D; font-size:28px;">{fmt(sobra_final)}</div>
            <div style="font-size:12px; font-weight:700; margin-top:6px; color:#166534; line-height:1.6;">
                (+) Salário Base: <strong>{fmt(RENDA_FIXA)}</strong><br>
                (-) Faturas Pessoais: <strong>{fmt(meu_custo_cartoes)}</strong><br>
                (-) Fixas em Boleto/Conta: <strong>{fmt(fixas_minha_em_conta)}</strong><br>
                (-) Reserva Mensal: <strong>{fmt(valor_reserva)}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="reserva-card">
            <span style="font-size:10px; font-weight:800; color:#0F766E; letter-spacing:0.5px; text-transform:uppercase;">🛡 Reserva Mensal ({mes_selecionado})</span>
            <div class="val-large" style="color:#0F766E; margin-top:2px;">{fmt(valor_reserva)}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Definir Reserva do Mês"):
            with st.form("form_reserva_mensal", clear_on_submit=False):
                nova_reserva = st.number_input("Valor a Guardar (R$)", value=float(valor_reserva), min_value=0.0, step=50.0)
                submit_reserva = st.form_submit_button("Salvar Reserva")
                if submit_reserva:
                    try:
                        supabase.table("reserva_mensal").upsert({
                            "mes_referencia": mes_selecionado,
                            "valor": nova_reserva
                        }, on_conflict="mes_referencia").execute()
                        limpar_cache()
                    except Exception:
                        pass
                    st.rerun()

        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        st.markdown("##### ➕ Registrar Gasto de Terceiro no Cartão")
        
        with st.form("form_novo_gasto_terceiro", clear_on_submit=True):
            d_desc = st.text_input("Descrição", placeholder="Ex: Farmácia, Jantar, Uber")
            d_val = st.number_input("Valor (R$)", min_value=0.0, step=10.0, value=0.0)
            d_cartao = st.selectbox("Cartão Utilizado", OPCOES_CARTAO)
            
            col_sub1, col_sub2 = st.columns(2)
            d_divisao = col_sub1.selectbox("Divisão", ["100% Terceiro", "Dividido 50/50"])
            d_pessoa = col_sub2.selectbox("Quem Paga?", pessoas_cadastradas)
            
            btn_cadastrar_gasto = st.form_submit_button("Abater da Fatura")
            if btn_cadastrar_gasto:
                if d_desc.strip() and d_val > 0:
                    v_meu, v_reemb = calcular_cotas(d_val, "50/50" if d_divisao == "Dividido 50/50" else "TERCEIRO")
                    
                    supabase.table("despesas").insert({
                        "mes_referencia": mes_selecionado,
                        "descricao": d_desc.strip(),
                        "valor_total": d_val,
                        "cartao_nome": d_cartao,
                        "pessoa_nome": d_pessoa,
                        "divisao": "50/50" if d_divisao == "Dividido 50/50" else "TERCEIRO",
                        "valor_meu": v_meu,
                        "valor_reembolso": v_reemb,
                        "status": "EFETIVADO"
                    }).execute()
                    limpar_cache()
                    st.rerun()
                else:
                    st.warning("Preencha a descrição e um valor superior a zero.")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# ABA 2: TERCEIROS & COBRANÇAS
# =========================================================================
with tab_cobrancas:
    col_res_terc, col_lista_terc = st.columns([1, 2], gap="large")
    
    lista_cobrancas = []
    if not df.empty and "valor_reembolso" in df.columns:
        for _, row in df[df["valor_reembolso"] > 0].iterrows():
            lista_cobrancas.append({
                "origem": "CARTÃO",
                "id": row["id"],
                "descricao": row["descricao"],
                "pessoa_nome": row.get("pessoa_nome") or "OUTROS",
                "divisao": row["divisao"],
                "cartao_ou_conta": row.get("cartao_nome") or "PIX",
                "valor": float(row["valor_reembolso"])
            })
            
    for f in fixas_res:
        v_tot = float(f.get("valor_estimado") or 0.0)
        div_t = f.get("divisao") or "MEU"
        _, f_reemb = calcular_cotas(v_tot, div_t)
        if f_reemb > 0:
            lista_cobrancas.append({
                "origem": "CONTA",
                "id": f["id"],
                "descricao": f["descricao"],
                "pessoa_nome": f.get("pessoa_nome") or "OUTROS",
                "divisao": div_t,
                "cartao_ou_conta": "BOLETO / CONTA",
                "valor": f_reemb
            })

    for s in streamings_res:
        v_tot = float(s.get("valor") or 0.0)
        div_t = s.get("divisao") or "MEU"
        _, s_reemb = calcular_cotas(v_tot, div_t)
        if s_reemb > 0:
            lista_cobrancas.append({
                "origem": "STREAMING",
                "id": s["id"],
                "descricao": s["nome_servico"],
                "pessoa_nome": s.get("pessoa_nome") or "OUTROS",
                "divisao": div_t,
                "cartao_ou_conta": s.get("cartao_nome") or "CARTÃO",
                "valor": s_reemb
            })
            
    df_cobrancas_total = pd.DataFrame(lista_cobrancas) if lista_cobrancas else pd.DataFrame()

    with col_res_terc:
        st.markdown('<div class="block-header-align">Saldo por Pessoa</div>', unsafe_allow_html=True)
        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        if not df_cobrancas_total.empty:
            resumo_p = df_cobrancas_total.groupby("pessoa_nome")["valor"].sum().reset_index()
            for _, r in resumo_p.iterrows():
                st.markdown(f"""
                <div class="clean-item-row">
                    <div><strong style="color:#0F172A; font-size:13px;">{r['pessoa_nome']}</strong></div>
                    <div style="font-weight:800; color:#2563EB; font-size:14px;">{fmt(float(r['valor']))}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<hr style='border:none; border-top:1px solid #E2E8F0; margin:8px 0;'>", unsafe_allow_html=True)
            st.markdown(f"**Total a Receber:** <span style='font-size:16px; font-weight:800; color:#2563EB;'>{fmt(total_reembolso_geral)}</span>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#475569; font-weight:600; font-size:13px;'>Nenhum reembolso pendente neste mês.</div>", unsafe_allow_html=True)
            
        with st.expander("+ Nova Pessoa"):
            with st.form("form_nova_pessoa", clear_on_submit=True):
                nova_p = st.text_input("Nome")
                btn_p = st.form_submit_button("Cadastrar Pessoa")
                if btn_p and nova_p.strip():
                    supabase.table("pessoas").upsert({"nome": nova_p.strip().upper()}, on_conflict="nome").execute()
                    limpar_cache()
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_lista_terc:
        st.markdown('<div class="block-header-align">Detalhamento das Cobranças</div>', unsafe_allow_html=True)
        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        filtro_p = st.selectbox("Filtrar por Pessoa:", ["TODOS"] + pessoas_cadastradas)
        
        if not df_cobrancas_total.empty:
            df_filtro = df_cobrancas_total if filtro_p == "TODOS" else df_cobrancas_total[df_cobrancas_total["pessoa_nome"] == filtro_p]
            if not df_filtro.empty:
                sub_filtro = df_filtro["valor"].sum()
                st.markdown(f"""
                <div style="background:#F1F5F9; border-radius:6px; padding:8px 12px; margin-bottom:10px; border:1px solid #E2E8F0;">
                    <div class='card-label-dark'>Subtotal ({filtro_p})</div>
                    <div class='val-large' style='color:#2563EB; font-size:18px;'>{fmt(sub_filtro)}</div>
                </div>
                """, unsafe_allow_html=True)

                for _, item_c in df_filtro.iterrows():
                    c_txt, c_val, c_del = st.columns([3.5, 1.2, 0.4])
                    tipo_badge = f"<span style='background:#E0E7FF; color:#1E1B4B; font-size:9px; font-weight:800; padding:1px 5px; border-radius:3px;'>{item_c['origem']}</span>"
                    with c_txt:
                        st.markdown(f"""
                        <div style="font-weight:700; color:#0F172A; font-size:13px; line-height:1.2;">{item_c['descricao']} {tipo_badge}</div>
                        <div style="color:#475569; font-size:11px; font-weight:700; margin-top:1px;">
                            Responsável: <span style="color:#0F172A;">{item_c['pessoa_nome']}</span> ({item_c['divisao']}) • {item_c['cartao_ou_conta']}
                        </div>
                        """, unsafe_allow_html=True)
                    with c_val:
                        st.markdown(f"<div style='text-align:right; font-weight:800; color:#2563EB; font-size:15px; padding-top:2px;'>{fmt(float(item_c['valor']))}</div>", unsafe_allow_html=True)
                    with c_del:
                        if item_c["origem"] == "CARTÃO":
                            if st.button("✕", key=f"del_cobr_c_{item_c['id']}"):
                                supabase.table("despesas").delete().eq("id", item_c["id"]).execute()
                                limpar_cache()
                                st.rerun()
                        else:
                            st.caption("-")
                    st.markdown("<hr style='border:none; border-top:1px solid #F1F5F9; margin:3px 0;'>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#475569; font-weight:600; font-size:13px;'>Nenhum lançamento ativo para {filtro_p}.</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# ABA 3: CONTAS RECORRENTES & ASSINATURAS (CARDS GRID MODERNOS)
# =========================================================================
with tab_fixas:
    st.markdown('<div class="block-header-align">Painel de Contas & Assinaturas</div>', unsafe_allow_html=True)
    col_main_grid, col_cadastros = st.columns([2.2, 1], gap="large")

    with col_main_grid:
        # PACOTE STREAMING
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 8px;">
            <div>
                <span style="color:#7C3AED; font-size:11px; font-weight:800; text-transform:uppercase;">Pacote Streaming</span>
                <div style="font-size:14px; font-weight:800; color:#0F172A;">Total Bruto: {fmt(total_stream_bruto)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if streamings_res:
            cols_str = st.columns(2)
            for i, s_item in enumerate(streamings_res):
                s_id = s_item["id"]
                s_cobrado = s_id in set_stream_cobrados
                s_val_tot = float(s_item.get("valor") or 0.0)
                s_div = s_item.get("divisao") or "MEU"
                s_cart = s_item.get("cartao_nome") or "PIX / DÉBITO"
                s_val_meu, s_val_reemb = calcular_cotas(s_val_tot, s_div)
                s_p = s_item.get("pessoa_nome") or ""

                tag_status = '<span class="bento-badge-paid">✓ PAGO</span>' if s_cobrado else '<span class="bento-badge-open">EM ABERTO</span>'

                with cols_str[i % 2]:
                    st.markdown(f"""
                    <div class="bento-card">
                        <div class="bento-card-header">
                            <div class="bento-icon-title">
                                <div class="bento-icon">🎬</div>
                                <div>
                                    <div class="bento-title">{s_item['nome_servico']}</div>
                                    <div class="bento-sub" style="color:#2563EB;">💳 {s_cart}</div>
                                </div>
                            </div>
                            {tag_status}
                        </div>
                        <div class="bento-card-body">
                            <div>
                                <div style="font-size:10px; color:#64748B; font-weight:700;">TOTAL: {fmt(s_val_tot)}</div>
                                <div style="font-size:11px; color:#2563EB; font-weight:700;">{s_div} {f'({s_p}: {fmt(s_val_reemb)})' if s_p and s_div != 'MEU' else ''}</div>
                            </div>
                            <div style="text-align:right;">
                                <span style="font-size:10px; font-weight:800; color:#64748B; text-transform:uppercase;">Sua Cota</span>
                                <div style="font-size:15px; font-weight:800; color:#0F172A;">{fmt(s_val_meu)}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.expander(f"Gerenciar {s_item['nome_servico']}"):
                        ca1, ca2 = st.columns([2, 1])
                        with ca1:
                            if s_cobrado:
                                if st.button("↺ Reabrir", key=f"reabrir_str_{s_id}"):
                                    supabase.table("efetivacao_fixas_mensais").delete().eq("mes_referencia", mes_selecionado).eq("item_tipo", "STREAMING").eq("item_id", s_id).execute()
                                    limpar_cache()
                                    st.rerun()
                            else:
                                if st.button("Marcar Pago", key=f"efet_str_{s_id}"):
                                    supabase.table("efetivacao_fixas_mensais").upsert({
                                        "mes_referencia": mes_selecionado,
                                        "item_tipo": "STREAMING",
                                        "item_id": s_id,
                                        "efetivado": True
                                    }, on_conflict="mes_referencia,item_tipo,item_id").execute()
                                    limpar_cache()
                                    st.rerun()
                        with ca2:
                            if st.button("Excluir", key=f"del_stream_{s_id}"):
                                supabase.table("streamings").delete().eq("id", s_id).execute()
                                limpar_cache()
                                st.rerun()

                        with st.form(f"form_ed_stream_{s_id}", clear_on_submit=False):
                            ed_s_nome = st.text_input("Nome", value=s_item['nome_servico'])
                            ed_s_val = st.number_input("Valor Mensal Total (R$)", value=float(s_val_tot), min_value=0.0, step=2.0)
                            
                            opcoes_c_str = ["PIX / DÉBITO"] + OPCOES_CARTAO
                            idx_cartao = opcoes_c_str.index(s_cart) if s_cart in opcoes_c_str else 0
                            ed_s_cart = st.selectbox("Cartão de Cobrança", opcoes_c_str, index=idx_cartao)
                            
                            idx_s_div = 0
                            if s_div == "50/50":
                                idx_s_div = 1
                            elif s_div == "TERCEIRO":
                                idx_s_div = 2
                            ed_s_div = st.selectbox("Divisão", ["100% Meu", "Dividido 50/50", "100% Terceiro"], index=idx_s_div)
                            
                            idx_s_pes = 0
                            if s_p in pessoas_cadastradas:
                                idx_s_pes = pessoas_cadastradas.index(s_p)
                            ed_s_pes = st.selectbox("Dividir com quem?", pessoas_cadastradas, index=idx_s_pes)

                            if st.form_submit_button("Salvar Alterações"):
                                if ed_s_nome.strip() and ed_s_val > 0:
                                    n_div_bd = "50/50" if ed_s_div == "Dividido 50/50" else ("TERCEIRO" if ed_s_div == "100% Terceiro" else "MEU")
                                    n_meu, n_reemb = calcular_cotas(ed_s_val, n_div_bd)

                                    supabase.table("streamings").update({
                                        "nome_servico": ed_s_nome.strip().upper(),
                                        "valor": ed_s_val,
                                        "cartao_nome": ed_s_cart,
                                        "divisao": n_div_bd,
                                        "pessoa_nome": ed_s_pes if n_div_bd != "MEU" else None,
                                        "valor_meu": n_meu,
                                        "valor_reembolso": n_reemb
                                    }).eq("id", s_id).execute()
                                    limpar_cache()
                                    st.rerun()
        else:
            st.caption("Nenhum serviço de streaming cadastrado.")

        # CONTAS RECORRENTES & MORADIA
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-top:22px; margin-bottom: 8px;">
            <div>
                <span style="color:#0F172A; font-size:11px; font-weight:800; text-transform:uppercase;">Contas Fixas & Moradia</span>
                <div style="font-size:14px; font-weight:800; color:#0F172A;">Total Bruto: {fmt(total_fixas_bruto)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if fixas_res:
            cols_fix = st.columns(2)
            for j, f_item in enumerate(fixas_res):
                f_id = f_item["id"]
                f_cobrado = f_id in set_fixas_cobradas
                v_tot = float(f_item.get("valor_estimado") or 0.0)
                div_tipo = f_item.get("divisao") or "MEU"
                v_meu, v_reemb = calcular_cotas(v_tot, div_tipo)
                p_resp = f_item.get("pessoa_nome") or ""
                cat = f_item.get("categoria_nome") or "OUTROS"
                icone_cat = ICONES_CATEGORIAS.get(cat, "📌")

                tag_status_fx = '<span class="bento-badge-paid">✓ PAGO</span>' if f_cobrado else '<span class="bento-badge-open">EM ABERTO</span>'

                with cols_fix[j % 2]:
                    st.markdown(f"""
                    <div class="bento-card">
                        <div class="bento-card-header">
                            <div class="bento-icon-title">
                                <div class="bento-icon">{icone_cat}</div>
                                <div>
                                    <div class="bento-title">{f_item['descricao']}</div>
                                    <div class="bento-sub">{cat}</div>
                                </div>
                            </div>
                            {tag_status_fx}
                        </div>
                        <div class="bento-card-body">
                            <div>
                                <div style="font-size:10px; color:#64748B; font-weight:700;">TOTAL: {fmt(v_tot)}</div>
                                <div style="font-size:11px; color:#2563EB; font-weight:700;">{div_tipo} {f'({p_resp}: {fmt(v_reemb)})' if p_resp and div_tipo != 'MEU' else ''}</div>
                            </div>
                            <div style="text-align:right;">
                                <span style="font-size:10px; font-weight:800; color:#64748B; text-transform:uppercase;">Sua Cota</span>
                                <div style="font-size:15px; font-weight:800; color:#0F172A;">{fmt(v_meu)}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.expander(f"Gerenciar {f_item['descricao']}"):
                        ca1, ca2 = st.columns([2, 1])
                        with ca1:
                            if f_cobrado:
                                if st.button("↺ Reabrir", key=f"reabrir_fx_{f_id}"):
                                    supabase.table("efetivacao_fixas_mensais").delete().eq("mes_referencia", mes_selecionado).eq("item_tipo", "CONTA_FIXA").eq("item_id", f_id).execute()
                                    limpar_cache()
                                    st.rerun()
                            else:
                                if st.button("Marcar Pago", key=f"efet_fx_{f_id}"):
                                    supabase.table("efetivacao_fixas_mensais").upsert({
                                        "mes_referencia": mes_selecionado,
                                        "item_tipo": "CONTA_FIXA",
                                        "item_id": f_id,
                                        "efetivado": True
                                    }, on_conflict="mes_referencia,item_tipo,item_id").execute()
                                    limpar_cache()
                                    st.rerun()
                        with ca2:
                            if st.button("Excluir", key=f"del_fix_{f_id}"):
                                supabase.table("despesas_recorrentes").delete().eq("id", f_id).execute()
                                limpar_cache()
                                st.rerun()

                        # Enviar conta para fatura de cartão específica neste mês
                        st.markdown("<div style='font-size:11px; font-weight:800; color:#475569; margin:6px 0 2px 0;'>LANÇAR NESTE MÊS NA FATURA:</div>", unsafe_allow_html=True)
                        col_c1, col_c2 = st.columns([2, 1])
                        cartao_destino = col_c1.selectbox("Cartão", OPCOES_CARTAO, key=f"sel_cart_des_{f_id}", label_visibility="collapsed")
                        if col_c2.button("Lançar", key=f"btn_lancar_{f_id}"):
                            supabase.table("despesas").insert({
                                "mes_referencia": mes_selecionado,
                                "descricao": f_item['descricao'],
                                "valor_total": v_tot,
                                "cartao_nome": cartao_destino,
                                "pessoa_nome": p_resp if div_tipo != "MEU" else None,
                                "divisao": div_tipo,
                                "valor_meu": v_meu,
                                "valor_reembolso": v_reemb,
                                "status": "EFETIVADO"
                            }).execute()
                            limpar_cache()
                            st.success(f"Enviado para fatura {cartao_destino}!")
                            st.rerun()

                        st.markdown("<hr style='border:none; border-top:1px solid #E2E8F0; margin:6px 0;'>", unsafe_allow_html=True)

                        with st.form(f"form_ed_fixa_{f_id}", clear_on_submit=False):
                            ed_nome = st.text_input("Nome da Conta", value=f_item['descricao'])
                            ed_val = st.number_input("Valor Total da Conta (R$)", value=float(v_tot), min_value=0.0, step=10.0)

                            idx_cat = CATEGORIAS_FIXAS.index(cat) if cat in CATEGORIAS_FIXAS else CATEGORIAS_FIXAS.index("RESIDENCIAL")
                            ed_cat = st.selectbox("Categoria", CATEGORIAS_FIXAS, index=idx_cat)
                            
                            idx_div = 0
                            if div_tipo == "50/50":
                                idx_div = 1
                            elif div_tipo == "TERCEIRO":
                                idx_div = 2
                            ed_div = st.selectbox("Divisão", ["100% Meu", "Dividido 50/50", "100% Terceiro"], index=idx_div)
                            
                            idx_p = 0
                            if p_resp in pessoas_cadastradas:
                                idx_p = pessoas_cadastradas.index(p_resp)
                            ed_p = st.selectbox("Com quem dividir?", pessoas_cadastradas, index=idx_p)

                            if st.form_submit_button("Salvar Alterações"):
                                if ed_nome.strip() and ed_val > 0:
                                    n_div_bd = "50/50" if ed_div == "Dividido 50/50" else ("TERCEIRO" if ed_div == "100% Terceiro" else "MEU")
                                    n_meu, n_reemb = calcular_cotas(ed_val, n_div_bd)

                                    supabase.table("despesas_recorrentes").update({
                                        "descricao": ed_nome.strip().upper(),
                                        "valor_estimado": ed_val,
                                        "categoria_nome": ed_cat,
                                        "divisao": n_div_bd,
                                        "pessoa_nome": ed_p if n_div_bd != "MEU" else None,
                                        "valor_meu": n_meu,
                                        "valor_reembolso": n_reemb
                                    }).eq("id", f_id).execute()
                                    limpar_cache()
                                    st.rerun()
        else:
            st.caption("Nenhuma conta recorrente cadastrada.")

    with col_cadastros:
        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        st.markdown("##### ➕ Nova Assinatura")
        with st.form("form_add_streaming", clear_on_submit=True):
            n_st = st.text_input("Serviço", placeholder="Ex: Netflix, Disney+")
            v_st = st.number_input("Valor Mensal Total (R$)", min_value=0.0, step=5.0, value=0.0)
            c_st = st.selectbox("Cartão de Cobrança", ["PIX / DÉBITO"] + OPCOES_CARTAO)
            
            c_div1, c_div2 = st.columns(2)
            d_st_div = c_div1.selectbox("Divisão", ["100% Meu", "Dividido 50/50", "100% Terceiro"])
            d_st_pes = c_div2.selectbox("Com quem?", pessoas_cadastradas)
            
            btn_salvar_st = st.form_submit_button("Cadastrar Assinatura")
            if btn_salvar_st:
                if n_st.strip() and v_st > 0:
                    n_div_bd = "50/50" if d_st_div == "Dividido 50/50" else ("TERCEIRO" if d_st_div == "100% Terceiro" else "MEU")
                    ns_meu, ns_reemb = calcular_cotas(v_st, n_div_bd)

                    supabase.table("streamings").upsert({
                        "nome_servico": n_st.strip().upper(),
                        "valor": v_st,
                        "cartao_nome": c_st,
                        "divisao": n_div_bd,
                        "pessoa_nome": d_st_pes if n_div_bd != "MEU" else None,
                        "valor_meu": ns_meu,
                        "valor_reembolso": ns_reemb
                    }, on_conflict="nome_servico").execute()
                    limpar_cache()
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        st.markdown("##### ➕ Nova Conta Recorrente")
        with st.form("form_add_conta_fixa", clear_on_submit=True):
            n_fx = st.text_input("Descrição", placeholder="Ex: Sanepar, Claro, Enxoval")
            v_fx = st.number_input("Valor Total da Conta (R$)", min_value=0.0, step=10.0, value=0.0)
            c_fx = st.selectbox("Categoria", CATEGORIAS_FIXAS)
            
            c_fdiv1, c_fdiv2 = st.columns(2)
            d_fx_div = c_fdiv1.selectbox("Divisão", ["100% Meu", "Dividido 50/50", "100% Terceiro"])
            d_fx_pes = c_fdiv2.selectbox("Com quem?", pessoas_cadastradas)
            
            btn_salvar_fx = st.form_submit_button("Cadastrar Conta")
            if btn_salvar_fx:
                if n_fx.strip() and v_fx > 0:
                    n_div_bd = "50/50" if d_fx_div == "Dividido 50/50" else ("TERCEIRO" if d_fx_div == "100% Terceiro" else "MEU")
                    nf_meu, nf_reemb = calcular_cotas(v_fx, n_div_bd)

                    supabase.table("despesas_recorrentes").upsert({
                        "descricao": n_fx.strip().upper(),
                        "valor_estimado": v_fx,
                        "categoria_nome": c_fx,
                        "divisao": n_div_bd,
                        "pessoa_nome": d_fx_pes if n_div_bd != "MEU" else None,
                        "valor_meu": nf_meu,
                        "valor_reembolso": nf_reemb
                    }, on_conflict="descricao").execute()
                    limpar_cache()
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# ABA 4: DEMONSTRATIVO & MIGRAÇÃO
# =========================================================================
with tab_demonstrativo:
    st.markdown('<div class="block-header-align">Balanço Detalhado do Mês</div>', unsafe_allow_html=True)
    st.markdown('<div class="clean-card">', unsafe_allow_html=True)
    
    tabela_demonstrativo = pd.DataFrame([
        {"Item / Conta": "Renda Mensal Fixa (Salário Base)", "Tipo": "(+) Entrada", "Valor": fmt(RENDA_FIXA)},
        {"Item / Conta": "Fatura Total Nubank", "Tipo": "Bruto", "Valor": fmt(fat_nu_total)},
        {"Item / Conta": "Fatura Total Itaú Signature", "Tipo": "Bruto", "Valor": fmt(fat_itau_total)},
        {"Item / Conta": "Fatura Total Mercado Pago", "Tipo": "Bruto", "Valor": fmt(fat_mp_total)},
        {"Item / Conta": "Total Bruto dos Cartões", "Tipo": "Subtotal", "Valor": fmt(total_faturas_bruto)},
        {"Item / Conta": "(-) Terceiros em Cartões Abatidos", "Tipo": "(-) Reembolso", "Valor": f"- {fmt(total_reemb_cartoes)}"},
        {"Item / Conta": "(=) Sua Responsabilidade nos Cartões", "Tipo": "(-) Saída Cartões", "Valor": f"- {fmt(meu_custo_cartoes)}"},
        {"Item / Conta": "Total Bruto de Contas Recorrentes", "Tipo": "Subtotal", "Valor": fmt(total_fixas_bruto)},
        {"Item / Conta": "Total Bruto do Pacote Streaming", "Tipo": "Subtotal", "Valor": fmt(total_stream_bruto)},
        {"Item / Conta": "(-) Terceiros em Fixas + Streamings", "Tipo": "(-) Reembolso", "Valor": f"- {fmt(total_terceiros_fixas)}"},
        {"Item / Conta": "(=) Sua Cota Paga em Boleto / Débito Conta", "Tipo": "(-) Saída Direta", "Valor": f"- {fmt(fixas_minha_em_conta)}"},
        {"Item / Conta": "(-) Reserva Mensal Guardada / Investida", "Tipo": "(-) Aporte Reserva", "Valor": f"- {fmt(valor_reserva)}"},
        {"Item / Conta": "(=) SOBRA LÍQUIDA PROJETADA", "Tipo": "(=) Saldo Final", "Valor": fmt(sobra_final)}
    ])
    st.dataframe(tabela_demonstrativo, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-header-align">🔄 Ferramenta de Migração de Dados</div>', unsafe_allow_html=True)
    st.markdown('<div class="clean-card">', unsafe_allow_html=True)
    st.caption("Mova lançamentos de um mês para outro.")
    
    col_mig1, col_mig2, col_mig3 = st.columns([1, 1, 1], gap="medium")
    origem_m = col_mig1.selectbox("De:", MESES, index=MESES.index("SET"))
    destino_m = col_mig2.selectbox("Para:", MESES, index=MESES.index("NOV"))
    
    if col_mig3.button("Transferir Dados"):
        if origem_m == destino_m:
            st.warning("Selecione meses diferentes.")
        else:
            try:
                supabase.table("despesas").update({"mes_referencia": destino_m}).eq("mes_referencia", origem_m).execute()
                fats_origem = supabase.table("faturas_mensais").select("*").eq("mes_referencia", origem_m).execute().data
                for fo in fats_origem:
                    supabase.table("faturas_mensais").upsert({
                        "mes_referencia": destino_m,
                        "cartao_nome": fo["cartao_nome"],
                        "valor_total_fatura": fo["valor_total_fatura"]
                    }, on_conflict="mes_referencia,cartao_nome").execute()
                
                supabase.table("faturas_mensais").delete().eq("mes_referencia", origem_m).execute()
                limpar_cache()
                st.success(f"Dados transferidos de {origem_m} para {destino_m}!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro na migração: {e}")
    st.markdown('</div>', unsafe_allow_html=True)