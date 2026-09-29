import os
import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

st.set_page_config(page_title="Controle Mensal", layout="wide")

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL") or (st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None)
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or (st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None)
RENDA_FIXA = float(os.getenv("RENDA_MENSAL_FIXA") or (st.secrets.get("RENDA_MENSAL_FIXA", 3787.38) if hasattr(st, "secrets") else 3787.38))

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Credenciais do Supabase ausentes no arquivo .env!")
    st.stop()

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()
MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
mes_atual = MESES[datetime.now().month - 1]

def fmt(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- CSS COM ALINHAMENTO GEOMÉTRICO E CONTRASTE ABSOLUTO ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
    }

    /* ESTILIZAÇÃO DAS ABAS (TABS) - ALTO CONTRASTE */
    button[data-baseweb="tab"] {
        background-color: #E2E8F0 !important;
        color: #334155 !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 8px 20px !important;
        margin-right: 4px !important;
        border: 1px solid #CBD5E1 !important;
        border-bottom: none !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border-color: #0F172A !important;
    }

    /* TOP CAPSULE */
    .top-capsule {
        background-color: #FFFFFF !important;
        border-radius: 14px;
        padding: 16px 20px;
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 12px;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #CBD5E1;
    }
    .top-capsule-item {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .top-capsule span {
        font-size: 11px;
        font-weight: 800;
        color: #334155 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .top-capsule strong {
        color: #0F172A !important;
        font-size: 17px;
        font-weight: 800;
        font-variant-numeric: tabular-nums;
    }

    /* CARDS PADRONIZADOS COM MESMA ALTURA E MARGEM */
    .clean-card {
        background-color: #FFFFFF !important;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #CBD5E1;
    }

    .hero-neon-card {
        background: #DCFCE7 !important;
        border: 2px solid #86EFAC !important;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
        color: #14532D !important;
    }

    .reserva-card {
        background: #CCFBF1 !important;
        border: 2px solid #5EEAD4 !important;
        border-left: 6px solid #0F766E !important;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }

    .card-label-dark {
        font-size: 12px;
        font-weight: 800;
        color: #334155 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .card-label-light {
        font-size: 12px;
        font-weight: 800;
        color: #166534 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .val-large {
        font-size: 24px;
        font-weight: 800;
        letter-spacing: -0.5px;
        font-variant-numeric: tabular-nums;
        color: #0F172A !important;
    }

    /* BLOCOS DE ITENS */
    .block-card {
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1;
    }
    .block-moradia {
        border-left: 6px solid #D97706 !important;
        background-color: #FFFBEB !important;
    }
    .block-streaming {
        border-left: 6px solid #7C3AED !important;
        background-color: #F5F3FF !important;
    }
    .block-outros {
        border-left: 6px solid #2563EB !important;
        background-color: #EFF6FF !important;
    }
    .block-cobrado {
        border-left: 6px solid #64748B !important;
        background-color: #E2E8F0 !important;
        opacity: 0.75;
    }
    .badge-cobrado {
        background-color: #0F172A;
        color: #FFFFFF !important;
        font-size: 11px;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 5px;
        margin-right: 6px;
    }

    .clean-item-row {
        background-color: #FFFFFF !important;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #CBD5E1;
    }

    /* INPUTS & SELECTS */
    div[data-baseweb="select"] > div, input {
        background-color: #FFFFFF !important;
        border: 1px solid #94A3B8 !important;
        color: #0F172A !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }

    /* BOTÕES GERAIS */
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border: 1px solid #0F172A !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 6px 16px !important;
        height: 38px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
    }
    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
    }

    button:has(p:contains("↺")), button:has(div:contains("↺")) {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #94A3B8 !important;
    }

    button:has(p:contains("✕")), button:has(div:contains("✕")) {
        background-color: #FEE2E2 !important;
        color: #991B1B !important;
        border: 1px solid #FCA5A5 !important;
    }
    button:has(p:contains("✕")):hover, button:has(div:contains("✕")):hover {
        background-color: #DC2626 !important;
        color: #FFFFFF !important;
    }

    /* CORREÇÃO DO TÍTULO DE COLUNAS STREAMLIT PARA ALINHAMENTO PERFEITO */
    .block-header-align {
        font-size: 17px;
        font-weight: 800;
        color: #0F172A;
        margin: 0 0 14px 0;
        height: 28px;
        display: flex;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO / FILTRO DE MÊS ---
col_logo, col_mes = st.columns([4, 1])
with col_logo:
    st.markdown("<h2 style='color:#0F172A; font-weight:800; margin:0;'>Controle Mensal</h2>", unsafe_allow_html=True)
with col_mes:
    mes_selecionado = st.selectbox("", MESES, index=MESES.index(mes_atual), label_visibility="collapsed")

# --- LEITURA DE DADOS NO SUPABASE ---
try:
    pessoas_cadastradas = [p["nome"] for p in supabase.table("pessoas").select("nome").order("nome").execute().data]
except Exception:
    pessoas_cadastradas = ["EDUARDO", "GUSTAVO", "CAMILA"]

try:
    faturas_data = supabase.table("faturas_mensais").select("*").eq("mes_referencia", mes_selecionado).execute().data
    dict_faturas = {f["cartao_nome"]: float(f["valor_total_fatura"]) for f in faturas_data}
except Exception:
    dict_faturas = {}

fat_nu_total = dict_faturas.get("NUBANK", 0.0)
fat_itau_total = dict_faturas.get("ITAU SIGNATURE", 0.0)
fat_mp_total = dict_faturas.get("MERCADO PAGO", 0.0)
total_faturas_bruto = fat_nu_total + fat_itau_total + fat_mp_total

try:
    res_despesas = supabase.table("despesas").select("*").eq("mes_referencia", mes_selecionado).execute().data
    df = pd.DataFrame(res_despesas) if res_despesas else pd.DataFrame()
except Exception:
    df = pd.DataFrame()

if not df.empty and "valor_reembolso" in df.columns:
    reemb_nu = df[(df["cartao_nome"] == "NUBANK")]["valor_reembolso"].sum()
    reemb_itau = df[(df["cartao_nome"] == "ITAU SIGNATURE")]["valor_reembolso"].sum()
    reemb_mp = df[(df["cartao_nome"] == "MERCADO PAGO")]["valor_reembolso"].sum()
    total_reemb_cartoes = df["valor_reembolso"].sum()
else:
    reemb_nu = reemb_itau = reemb_mp = total_reemb_cartoes = 0.0

minha_parte_nu = max(0.0, fat_nu_total - reemb_nu)
minha_parte_itau = max(0.0, fat_itau_total - reemb_itau)
minha_parte_mp = max(0.0, fat_mp_total - reemb_mp)
meu_custo_cartoes = minha_parte_nu + minha_parte_itau + minha_parte_mp

try:
    fixas_res = supabase.table("despesas_recorrentes").select("*").order("descricao").execute().data
except Exception:
    fixas_res = []

try:
    streamings_res = supabase.table("streamings").select("*").order("nome_servico").execute().data
except Exception:
    streamings_res = []

try:
    efetivacoes_data = supabase.table("efetivacao_fixas_mensais").select("*").eq("mes_referencia", mes_selecionado).execute().data
    set_fixas_cobradas = {e["item_id"] for e in efetivacoes_data if e["item_tipo"] == "CONTA_FIXA" and e["efetivado"]}
    set_stream_cobrados = {e["item_id"] for e in efetivacoes_data if e["item_tipo"] == "STREAMING" and e["efetivado"]}
except Exception:
    set_fixas_cobradas = set()
    set_stream_cobrados = set()

# LEITURA DA RESERVA MENSAL
try:
    reserva_res = supabase.table("reserva_mensal").select("valor").eq("mes_referencia", mes_selecionado).execute().data
    valor_reserva = float(reserva_res[0]["valor"]) if reserva_res else 0.0
except Exception:
    valor_reserva = 0.0

total_fixas_bruto = sum(float(f["valor_estimado"]) for f in fixas_res)
total_fixas_minha_parte = sum(float(f.get("valor_meu") if f.get("valor_meu") is not None else f["valor_estimado"]) for f in fixas_res)
total_fixas_terceiros = sum(float(f.get("valor_reembolso") or 0.0) for f in fixas_res)

total_stream_bruto = sum(float(s["valor"]) for s in streamings_res)
total_stream_minha_parte = sum(float(s.get("valor_meu") if s.get("valor_meu") is not None else s["valor"]) for s in streamings_res)
total_stream_terceiros = sum(float(s.get("valor_reembolso") or 0.0) for s in streamings_res)

total_compromissos_fixos_bruto = total_fixas_bruto + total_stream_bruto
total_compromissos_fixos_meu = total_fixas_minha_parte + total_stream_minha_parte
total_compromissos_fixos_terceiros = total_fixas_terceiros + total_stream_terceiros

total_reembolso_geral = total_reemb_cartoes + total_compromissos_fixos_terceiros
sobra_final = RENDA_FIXA - total_compromissos_fixos_meu - meu_custo_cartoes - valor_reserva

# --- NAVBAR TOPO ---
st.markdown(f"""
<div class="top-capsule">
    <div class="top-capsule-item"><span>Salário Base</span><strong>{fmt(RENDA_FIXA)}</strong></div>
    <div class="top-capsule-item"><span>Faturas Brutas</span><strong>{fmt(total_faturas_bruto)}</strong></div>
    <div class="top-capsule-item"><span>Total Terceiros</span><strong style="color:#2563EB;">{fmt(total_reembolso_geral)}</strong></div>
    <div class="top-capsule-item"><span>Faturas Líquidas</span><strong>{fmt(meu_custo_cartoes)}</strong></div>
    <div class="top-capsule-item"><span>Fixas (Seu Custo)</span><strong>{fmt(total_compromissos_fixos_meu)}</strong></div>
    <div class="top-capsule-item"><span>Reserva</span><strong style="color:#0F766E;">{fmt(valor_reserva)}</strong></div>
    <div class="top-capsule-item"><span>Sobra Líquida</span><strong style="color:#15803D;">{fmt(sobra_final)}</strong></div>
</div>
""", unsafe_allow_html=True)

# --- ABAS DE NAVEGAÇÃO REESTILIZADAS ---
tab_faturas, tab_cobrancas, tab_fixas, tab_demonstrativo = st.tabs([
    "💳 Faturas & Fechamento", 
    "👥 Terceiros & Cobranças", 
    "⚡ Contas Fixas & Assinaturas",
    "📊 Demonstrativo & Migração"
])

# =========================================================================
# ABA 1: FATURAS & FECHAMENTO (ALINHAMENTO RIGOROSO)
# =========================================================================
with tab_faturas:
    col_cards_faturas, col_sobra = st.columns([1.8, 1.2], gap="large")
    
    with col_cards_faturas:
        st.markdown('<div class="block-header-align">Detalhamento por Cartão</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3, gap="small")
        
        def render_bloco_fatura(nome_cartao, label, valor_fatura, valor_terceiros, minha_parte):
            st.markdown(f"""
            <div class="clean-card" style="height: 195px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div class="card-label-dark">{label}</div>
                    <div class="val-large">{fmt(valor_fatura)}</div>
                    <div style="font-size:13px; color:#2563EB; font-weight:800; margin-top:2px;">
                        - {fmt(valor_terceiros)} (Terceiros)
                    </div>
                </div>
                <div>
                    <hr style="border:none; border-top:1px solid #CBD5E1; margin:8px 0;">
                    <div class="card-label-dark" style="margin:0;">Seu Custo Real:</div>
                    <div style="font-size:18px; font-weight:800; color:#0F172A;">{fmt(minha_parte)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"Ajustar {label}"):
                with st.form(f"form_fat_{nome_cartao}", clear_on_submit=False):
                    novo_val = st.number_input("Valor Fechado", value=float(valor_fatura), min_value=0.0, step=50.0)
                    submit_fat = st.form_submit_button("Salvar Fatura", use_container_width=True)
                    if submit_fat:
                        supabase.table("faturas_mensais").upsert({
                            "mes_referencia": mes_selecionado,
                            "cartao_nome": nome_cartao,
                            "valor_total_fatura": novo_val
                        }, on_conflict="mes_referencia,cartao_nome").execute()
                        st.rerun()

        with c1:
            render_bloco_fatura("NUBANK", "Nubank", fat_nu_total, reemb_nu, minha_parte_nu)
        with c2:
            render_bloco_fatura("ITAU SIGNATURE", "Itaú Signature", fat_itau_total, reemb_itau, minha_parte_itau)
        with c3:
            render_bloco_fatura("MERCADO PAGO", "Mercado Pago", fat_mp_total, reemb_mp, minha_parte_mp)

    with col_sobra:
        st.markdown('<div class="block-header-align">Resumo do Mês & Reserva</div>', unsafe_allow_html=True)
        
        # CARD SOBRA LÍQUIDA PERFEITAMENTE ALINHADO
        st.markdown(f"""
        <div class="hero-neon-card">
            <div class="card-label-light">Sobra Líquida Projetada</div>
            <div class="val-large" style="color:#14532D; font-size:32px;">{fmt(sobra_final)}</div>
            <div style="font-size:13px; font-weight:700; margin-top:10px; color:#166534; line-height:1.7;">
                (+) Salário Base: <strong>{fmt(RENDA_FIXA)}</strong><br>
                (-) Faturas Pessoais: <strong>{fmt(meu_custo_cartoes)}</strong><br>
                (-) Fixas + Streamings: <strong>{fmt(total_compromissos_fixos_meu)}</strong><br>
                (-) Reserva Mensal: <strong>{fmt(valor_reserva)}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="reserva-card">
            <span style="font-size:11px; font-weight:800; color:#0F766E; letter-spacing:0.5px; text-transform:uppercase;">🛡️ Reserva Mensal ({mes_selecionado})</span>
            <div class="val-large" style="color:#0F766E; margin-top:4px;">{fmt(valor_reserva)}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Definir Reserva do Mês"):
            with st.form("form_reserva_mensal", clear_on_submit=False):
                nova_reserva = st.number_input("Valor a Guardar (R$)", value=float(valor_reserva), min_value=0.0, step=50.0)
                submit_reserva = st.form_submit_button("Salvar Reserva", use_container_width=True)
                if submit_reserva:
                    try:
                        supabase.table("reserva_mensal").upsert({
                            "mes_referencia": mes_selecionado,
                            "valor": nova_reserva
                        }, on_conflict="mes_referencia").execute()
                    except Exception:
                        pass
                    st.rerun()

        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        st.markdown("##### ➕ Registrar Gasto de Terceiro no Cartão")
        
        with st.form("form_novo_gasto_terceiro", clear_on_submit=True):
            d_desc = st.text_input("Descrição da Compra", placeholder="Ex: Farmácia, Jantar, Uber")
            d_val = st.number_input("Valor da Compra (R$)", min_value=0.0, step=10.0, value=0.0)
            d_cartao = st.selectbox("Cartão Utilizado", ["NUBANK", "ITAU SIGNATURE", "MERCADO PAGO"])
            
            col_sub1, col_sub2 = st.columns(2)
            d_divisao = col_sub1.selectbox("Divisão", ["100% Terceiro", "Dividido 50/50"])
            d_pessoa = col_sub2.selectbox("Quem Paga?", pessoas_cadastradas)
            
            btn_cadastrar_gasto = st.form_submit_button("Abater da Fatura", use_container_width=True)
            if btn_cadastrar_gasto:
                if d_desc.strip() and d_val > 0:
                    v_meu = d_val / 2 if d_divisao == "Dividido 50/50" else 0.0
                    v_reemb = d_val / 2 if d_divisao == "Dividido 50/50" else d_val
                    
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
                    st.rerun()
                else:
                    st.warning("Preencha a descrição e um valor superior a zero.")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# ABA 2: TERCEIROS & COBRANÇAS (LEGIBILIDADE MÁXIMA)
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
        if float(f.get("valor_reembolso") or 0.0) > 0:
            lista_cobrancas.append({
                "origem": "CONTA FIXA",
                "id": f["id"],
                "descricao": f["descricao"],
                "pessoa_nome": f.get("pessoa_nome") or "OUTROS",
                "divisao": f.get("divisao") or "50/50",
                "cartao_ou_conta": "BOLETO / DÉBITO",
                "valor": float(f["valor_reembolso"])
            })

    for s in streamings_res:
        if float(s.get("valor_reembolso") or 0.0) > 0:
            lista_cobrancas.append({
                "origem": "STREAMING",
                "id": s["id"],
                "descricao": s["nome_servico"],
                "pessoa_nome": s.get("pessoa_nome") or "OUTROS",
                "divisao": s.get("divisao") or "50/50",
                "cartao_ou_conta": s.get("cartao_nome") or "CARTÃO",
                "valor": float(s["valor_reembolso"])
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
                    <div><strong style="color:#0F172A; font-size:15px;">{r['pessoa_nome']}</strong></div>
                    <div style="font-weight:800; color:#2563EB; font-size:16px;">{fmt(float(r['valor']))}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<hr style='border:none; border-top:1px solid #CBD5E1; margin:12px 0;'>", unsafe_allow_html=True)
            st.markdown(f"**Total a Receber:** <span style='font-size:18px; font-weight:800; color:#2563EB;'>{fmt(total_reembolso_geral)}</span>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#334155; font-weight:600;'>Nenhum reembolso pendente neste mês.</div>", unsafe_allow_html=True)
            
        with st.expander("+ Nova Pessoa"):
            with st.form("form_nova_pessoa", clear_on_submit=True):
                nova_p = st.text_input("Nome")
                btn_p = st.form_submit_button("Cadastrar Pessoa", use_container_width=True)
                if btn_p and nova_p.strip():
                    supabase.table("pessoas").upsert({"nome": nova_p.strip().upper()}, on_conflict="nome").execute()
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
                <div style="background:#F1F5F9; border-radius:10px; padding:12px; margin-bottom:12px; border:1px solid #CBD5E1;">
                    <div class='card-label-dark'>Subtotal ({filtro_p})</div>
                    <div class='val-large' style='color:#2563EB;'>{fmt(sub_filtro)}</div>
                </div>
                """, unsafe_allow_html=True)

                for _, item_c in df_filtro.iterrows():
                    c_txt, c_val, c_del = st.columns([3.5, 1.2, 0.4])
                    tipo_badge = f"<span style='background:#E0E7FF; color:#1E1B4B; font-size:11px; font-weight:800; padding:2px 7px; border-radius:4px;'>{item_c['origem']}</span>"
                    with c_txt:
                        st.markdown(f"""
                        <div style="font-weight:700; color:#0F172A; font-size:15px; line-height:1.2;">{item_c['descricao']} {tipo_badge}</div>
                        <div style="color:#334155; font-size:13px; font-weight:700; margin-top:2px;">
                            Responsável: <span style="color:#0F172A;">{item_c['pessoa_nome']}</span> ({item_c['divisao']}) • {item_c['cartao_ou_conta']}
                        </div>
                        """, unsafe_allow_html=True)
                    with c_val:
                        st.markdown(f"<div style='text-align:right; font-weight:800; color:#2563EB; font-size:17px; padding-top:4px;'>{fmt(float(item_c['valor']))}</div>", unsafe_allow_html=True)
                    with c_del:
                        if item_c["origem"] == "CARTÃO":
                            if st.button("✕", key=f"del_cobr_c_{item_c['id']}"):
                                supabase.table("despesas").delete().eq("id", item_c["id"]).execute()
                                st.rerun()
                        else:
                            st.caption("-")
                    st.markdown("<hr style='border:none; border-top:1px solid #E2E8F0; margin:6px 0;'>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#334155; font-weight:600;'>Nenhum lançamento ativo para {filtro_p}.</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# ABA 3: CONTAS FIXAS & STREAMINGS
# =========================================================================
with tab_fixas:
    st.markdown('<div class="block-header-align">Gestão de Contas Recorrentes & Assinaturas</div>', unsafe_allow_html=True)
    col_bloco1, col_bloco2 = st.columns([1.8, 1.2], gap="large")

    with col_bloco1:
        st.markdown(f"""
        <div class="clean-card" style="border-top: 5px solid #7C3AED;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#7C3AED; font-size:11px; font-weight:800; text-transform:uppercase;">Pacote Streaming</span>
                    <div class="val-large">{fmt(total_stream_bruto)}</div>
                </div>
                <div style="text-align:right;">
                    <span class="card-label-dark">Sua Parte Líquida</span>
                    <div style="font-size:20px; font-weight:800; color:#7C3AED;">{fmt(total_stream_minha_parte)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if streamings_res:
            for s_item in streamings_res:
                s_id = s_item["id"]
                s_cobrado = s_id in set_stream_cobrados
                s_val_tot = float(s_item["valor"])
                s_val_meu = float(s_item.get("valor_meu") if s_item.get("valor_meu") is not None else s_val_tot)
                s_val_reemb = float(s_item.get("valor_reembolso") or 0.0)
                s_div = s_item.get("divisao") or "MEU"
                s_p = s_item.get("pessoa_nome") or ""

                classe_css = "block-card block-cobrado" if s_cobrado else "block-card block-streaming"
                selo_html = "<span class='badge-cobrado'>✓ PAGO</span>" if s_cobrado else ""

                detalhe_div = f" | {s_div}"
                if s_div != "MEU" and s_p:
                    detalhe_div += f" ({s_p}: {fmt(s_val_reemb)})"

                st.markdown(f"""
                <div class="{classe_css}">
                    <div>
                        {selo_html}<strong style="color:#0F172A; font-size:15px;">{s_item['nome_servico']}</strong><br>
                        <div style="color:#334155; font-size:13px; font-weight:700; margin-top:2px;">
                            Cobrado em: {s_item.get('cartao_nome') or 'Nenhum'} | Total: {fmt(s_val_tot)}{detalhe_div}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:17px; font-weight:800; color:#0F172A;">{fmt(s_val_meu)}</span><br>
                        <small style="color:#334155; font-weight:700;">Sua parte</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_btn_efet, col_btn_del = st.columns([4, 1])
                with col_btn_efet:
                    if s_cobrado:
                        if st.button(f"↺ Reabrir {s_item['nome_servico']}", key=f"reabrir_str_{s_id}", use_container_width=True):
                            supabase.table("efetivacao_fixas_mensais").delete().eq("mes_referencia", mes_selecionado).eq("item_tipo", "STREAMING").eq("item_id", s_id).execute()
                            st.rerun()
                    else:
                        if st.button(f"Marcar como Pago ({s_item['nome_servico']})", key=f"efet_str_{s_id}", use_container_width=True):
                            supabase.table("efetivacao_fixas_mensais").upsert({
                                "mes_referencia": mes_selecionado,
                                "item_tipo": "STREAMING",
                                "item_id": s_id,
                                "efetivado": True
                            }, on_conflict="mes_referencia,item_tipo,item_id").execute()
                            st.rerun()
                with col_btn_del:
                    if st.button("✕", key=f"del_stream_{s_id}", use_container_width=True):
                        supabase.table("streamings").delete().eq("id", s_id).execute()
                        st.rerun()

                with st.expander(f"✏️ Editar Assinatura ({s_item['nome_servico']})"):
                    with st.form(f"form_ed_stream_{s_id}", clear_on_submit=False):
                        ed_s_nome = st.text_input("Nome do Serviço", value=s_item['nome_servico'])
                        ed_s_val = st.number_input("Valor Mensal (R$)", value=float(s_val_tot), min_value=0.0, step=2.0)
                        
                        opcoes_cartao = ["NUBANK", "ITAU SIGNATURE", "MERCADO PAGO", "PIX / DÉBITO"]
                        cartao_atual = s_item.get("cartao_nome") or "PIX / DÉBITO"
                        idx_cartao = opcoes_cartao.index(cartao_atual) if cartao_atual in opcoes_cartao else 0
                        ed_s_cart = st.selectbox("Cartão de Cobrança", opcoes_cartao, index=idx_cartao)
                        
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

                        btn_s_salvar = st.form_submit_button("Salvar Alterações", use_container_width=True)
                        if btn_s_salvar:
                            if ed_s_nome.strip() and ed_s_val > 0:
                                if ed_s_div == "100% Terceiro":
                                    n_meu, n_reemb, n_div = 0.0, ed_s_val, "TERCEIRO"
                                elif ed_s_div == "Dividido 50/50":
                                    n_meu, n_reemb, n_div = ed_s_val / 2, ed_s_val / 2, "50/50"
                                else:
                                    n_meu, n_reemb, n_div = ed_s_val, 0.0, "MEU"

                                supabase.table("streamings").update({
                                    "nome_servico": ed_s_nome.strip().upper(),
                                    "valor": ed_s_val,
                                    "cartao_nome": None if "PIX" in ed_s_cart else ed_s_cart,
                                    "divisao": n_div,
                                    "pessoa_nome": ed_s_pes if n_div != "MEU" else None,
                                    "valor_meu": n_meu,
                                    "valor_reembolso": n_reemb
                                }).eq("id", s_id).execute()
                                st.rerun()

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        else:
            st.caption("Nenhum serviço cadastrado.")

        # CONTAS FIXAS & MORADIA
        st.markdown(f"""
        <div class="clean-card" style="border-top: 5px solid #0F172A; margin-top:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#0F172A; font-size:11px; font-weight:800; text-transform:uppercase;">Contas Fixas & Moradia</span>
                    <div class="val-large">{fmt(total_fixas_bruto)}</div>
                </div>
                <div style="text-align:right;">
                    <span class="card-label-dark">Sua Parte Líquida</span>
                    <div style="font-size:20px; font-weight:800; color:#0F172A;">{fmt(total_fixas_minha_parte)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if fixas_res:
            for f_item in fixas_res:
                f_id = f_item["id"]
                f_cobrado = f_id in set_fixas_cobradas
                v_tot = float(f_item["valor_estimado"])
                v_meu = float(f_item.get("valor_meu") if f_item.get("valor_meu") is not None else v_tot)
                v_reemb = float(f_item.get("valor_reembolso") or 0.0)
                div_tipo = f_item.get("divisao") or "MEU"
                p_resp = f_item.get("pessoa_nome") or ""
                cat = f_item.get("categoria_nome") or "OUTROS"

                if f_cobrado:
                    classe_css = "block-card block-cobrado"
                else:
                    classe_css = "block-card block-moradia" if "APARTAMENTO" in cat else "block-card block-outros"

                selo_html = "<span class='badge-cobrado'>✓ PAGO</span>" if f_cobrado else ""

                detalhe_fx = f" | {div_tipo}"
                if div_tipo != "MEU" and p_resp:
                    detalhe_fx += f" ({p_resp}: {fmt(v_reemb)})"

                st.markdown(f"""
                <div class="{classe_css}">
                    <div>
                        {selo_html}<strong style="color:#0F172A; font-size:15px;">{f_item['descricao']}</strong><br>
                        <div style="color:#334155; font-size:13px; font-weight:700; margin-top:2px;">
                            {cat} | Total: {fmt(v_tot)}{detalhe_fx}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:17px; font-weight:800; color:#0F172A;">{fmt(v_meu)}</span><br>
                        <small style="color:#334155; font-weight:700;">Sua parte</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_btn_f_efet, col_btn_f_del = st.columns([4, 1])
                with col_btn_f_efet:
                    if f_cobrado:
                        if st.button(f"↺ Reabrir {f_item['descricao']}", key=f"reabrir_fx_{f_id}", use_container_width=True):
                            supabase.table("efetivacao_fixas_mensais").delete().eq("mes_referencia", mes_selecionado).eq("item_tipo", "CONTA_FIXA").eq("item_id", f_id).execute()
                            st.rerun()
                    else:
                        if st.button(f"Marcar como Pago ({f_item['descricao']})", key=f"efet_fx_{f_id}", use_container_width=True):
                            supabase.table("efetivacao_fixas_mensais").upsert({
                                "mes_referencia": mes_selecionado,
                                "item_tipo": "CONTA_FIXA",
                                "item_id": f_id,
                                "efetivado": True
                            }, on_conflict="mes_referencia,item_tipo,item_id").execute()
                            st.rerun()
                with col_btn_f_del:
                    if st.button("✕", key=f"del_fix_{f_id}", use_container_width=True):
                        supabase.table("despesas_recorrentes").delete().eq("id", f_id).execute()
                        st.rerun()

                with st.expander(f"✏️ Editar {f_item['descricao']}"):
                    with st.form(f"form_ed_fixa_{f_id}", clear_on_submit=False):
                        ed_nome = st.text_input("Nome da Conta", value=f_item['descricao'])
                        ed_val = st.number_input("Valor Estimado (R$)", value=float(v_tot), min_value=0.0, step=10.0)
                        
                        opcoes_cat = ["APARTAMENTO", "ALIMENTAÇÃO", "ASSINATURAS / STREAMING", "OUTROS"]
                        idx_cat = opcoes_cat.index(cat) if cat in opcoes_cat else 0
                        ed_cat = st.selectbox("Categoria", opcoes_cat, index=idx_cat)
                        
                        idx_div = 0
                        if div_tipo == "50/50":
                            idx_div = 1
                        elif div_tipo == "TERCEIRO":
                            idx_div = 2
                        ed_div = st.selectbox("Divisão da Conta", ["100% Meu", "Dividido 50/50", "100% Terceiro"], index=idx_div)
                        
                        idx_p = 0
                        if p_resp in pessoas_cadastradas:
                            idx_p = pessoas_cadastradas.index(p_resp)
                        ed_p = st.selectbox("Com quem dividir?", pessoas_cadastradas, index=idx_p)

                        btn_salvar_ed = st.form_submit_button("Salvar Alterações", use_container_width=True)
                        if btn_salvar_ed:
                            if ed_nome.strip() and ed_val > 0:
                                if ed_div == "100% Terceiro":
                                    n_meu, n_reemb, n_div = 0.0, ed_val, "TERCEIRO"
                                elif ed_div == "Dividido 50/50":
                                    n_meu, n_reemb, n_div = ed_val / 2, ed_val / 2, "50/50"
                                else:
                                    n_meu, n_reemb, n_div = ed_val, 0.0, "MEU"

                                supabase.table("despesas_recorrentes").update({
                                    "descricao": ed_nome.strip().upper(),
                                    "valor_estimado": ed_val,
                                    "categoria_nome": ed_cat,
                                    "divisao": n_div,
                                    "pessoa_nome": ed_p if n_div != "MEU" else None,
                                    "valor_meu": n_meu,
                                    "valor_reembolso": n_reemb
                                }).eq("id", f_id).execute()
                                st.rerun()

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        else:
            st.caption("Nenhuma despesa fixa cadastrada.")

    with col_bloco2:
        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        st.markdown("##### ➕ Nova Assinatura")
        with st.form("form_add_streaming", clear_on_submit=True):
            n_st = st.text_input("Serviço", placeholder="Ex: Netflix, Disney+")
            v_st = st.number_input("Valor Mensal (R$)", min_value=0.0, step=5.0, value=0.0)
            c_st = st.selectbox("Cartão", ["NUBANK", "ITAU SIGNATURE", "MERCADO PAGO", "PIX / DÉBITO"])
            
            c_div1, c_div2 = st.columns(2)
            d_st_div = c_div1.selectbox("Divisão", ["100% Meu", "Dividido 50/50", "100% Terceiro"])
            d_st_pes = c_div2.selectbox("Com quem?", pessoas_cadastradas)
            
            btn_salvar_st = st.form_submit_button("Cadastrar Assinatura", use_container_width=True)
            if btn_salvar_st:
                if n_st.strip() and v_st > 0:
                    if d_st_div == "100% Terceiro":
                        ns_meu, ns_reemb, ns_div = 0.0, v_st, "TERCEIRO"
                    elif d_st_div == "Dividido 50/50":
                        ns_meu, ns_reemb, ns_div = v_st / 2, v_st / 2, "50/50"
                    else:
                        ns_meu, ns_reemb, ns_div = v_st, 0.0, "MEU"

                    supabase.table("streamings").upsert({
                        "nome_servico": n_st.strip().upper(),
                        "valor": v_st,
                        "cartao_nome": None if "PIX" in c_st else c_st,
                        "divisao": ns_div,
                        "pessoa_nome": d_st_pes if ns_div != "MEU" else None,
                        "valor_meu": ns_meu,
                        "valor_reembolso": ns_reemb
                    }, on_conflict="nome_servico").execute()
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="clean-card">', unsafe_allow_html=True)
        st.markdown("##### ➕ Nova Conta Fixa")
        with st.form("form_add_conta_fixa", clear_on_submit=True):
            n_fx = st.text_input("Conta", placeholder="Ex: Sanepar, Claro, Condomínio")
            v_fx = st.number_input("Valor Estimado (R$)", min_value=0.0, step=10.0, value=0.0)
            c_fx = st.selectbox("Categoria", ["APARTAMENTO", "ALIMENTAÇÃO", "OUTROS"])
            
            c_fdiv1, c_fdiv2 = st.columns(2)
            d_fx_div = c_fdiv1.selectbox("Divisão", ["100% Meu", "Dividido 50/50", "100% Terceiro"])
            d_fx_pes = c_fdiv2.selectbox("Com quem?", pessoas_cadastradas)
            
            btn_salvar_fx = st.form_submit_button("Cadastrar Conta", use_container_width=True)
            if btn_salvar_fx:
                if n_fx.strip() and v_fx > 0:
                    if d_fx_div == "100% Terceiro":
                        nf_meu, nf_reemb, nf_div = 0.0, v_fx, "TERCEIRO"
                    elif d_fx_div == "Dividido 50/50":
                        nf_meu, nf_reemb, nf_div = v_fx / 2, v_fx / 2, "50/50"
                    else:
                        nf_meu, nf_reemb, nf_div = v_fx, 0.0, "MEU"

                    supabase.table("despesas_recorrentes").upsert({
                        "descricao": n_fx.strip().upper(),
                        "valor_estimado": v_fx,
                        "categoria_nome": c_fx,
                        "divisao": nf_div,
                        "pessoa_nome": d_fx_pes if nf_div != "MEU" else None,
                        "valor_meu": nf_meu,
                        "valor_reembolso": nf_reemb
                    }, on_conflict="descricao").execute()
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
        {"Item / Conta": "Total Bruto de Contas Fixas", "Tipo": "Subtotal", "Valor": fmt(total_fixas_bruto)},
        {"Item / Conta": "Total Bruto do Pacote Streaming", "Tipo": "Subtotal", "Valor": fmt(total_stream_bruto)},
        {"Item / Conta": "(-) Terceiros em Fixas + Streamings", "Tipo": "(-) Reembolso", "Valor": f"- {fmt(total_compromissos_fixos_terceiros)}"},
        {"Item / Conta": "(=) Sua Responsabilidade em Fixas + Streamings", "Tipo": "(-) Saída Fixas", "Valor": f"- {fmt(total_compromissos_fixos_meu)}"},
        {"Item / Conta": "(-) Reserva Mensal Guardada / Investida", "Tipo": "(-) Aporte Reserva", "Valor": f"- {fmt(valor_reserva)}"},
        {"Item / Conta": "(=) SOBRA LÍQUIDA PROJETADA", "Tipo": "(=) Saldo Final", "Valor": fmt(sobra_final)}
    ])
    st.dataframe(tabela_demonstrativo, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-header-align">🔄 Ferramenta de Migração de Dados</div>', unsafe_allow_html=True)
    st.markdown('<div class="clean-card">', unsafe_allow_html=True)
    st.caption("Mova lançamentos acidentais de um mês para outro.")
    
    col_mig1, col_mig2, col_mig3 = st.columns([1, 1, 1], gap="medium")
    origem_m = col_mig1.selectbox("De:", MESES, index=MESES.index("SET"))
    destino_m = col_mig2.selectbox("Para:", MESES, index=MESES.index("NOV"))
    
    if col_mig3.button("Transferir Dados", use_container_width=True):
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
                st.success(f"Dados transferidos de {origem_m} para {destino_m}!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro na migração: {e}")
    st.markdown('</div>', unsafe_allow_html=True)