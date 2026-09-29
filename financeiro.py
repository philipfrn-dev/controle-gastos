import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RENDA_FIXA = float(os.getenv("RENDA_MENSAL_FIXA", 3787.38))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Configurações do Supabase ausentes no arquivo .env!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def consultar_saldo(mes_ref="SET"):
    res = supabase.table("despesas").select("*").eq("mes_referencia", mes_ref.upper()).execute()
    despesas = res.data

    efetivadas = [d for d in despesas if d.get("status") == "EFETIVADO"]
    previstas = [d for d in despesas if d.get("status") == "PREVISTO"]

    # Valores Efetivados (Já no cartão/conta)
    fatura_efetivada = sum(float(d["valor_total"]) for d in efetivadas if d.get("cartao_nome"))
    reembolso_efetivado = sum(float(d["valor_reembolso"]) for d in efetivadas)
    custo_real_efetivado = sum(float(d["valor_meu"]) for d in efetivadas)
    sobra_atual = RENDA_FIXA - custo_real_efetivado

    # Valores Previstos (Aguardando cobrança)
    total_previsto = sum(float(d["valor_meu"]) for d in previstas)
    sobra_projetada = sobra_atual - total_previsto

    print("\n" + "=" * 60)
    print(f"       📊 BALANÇO FINANCEIRO - {mes_ref.upper()}")
    print("=" * 60)
    print(f"💵 Sua Renda Fixa:              {formatar_moeda(RENDA_FIXA)}")
    print("-" * 60)
    print(f"💳 Fatura Efetivada nos Cartões: {formatar_moeda(fatura_efetivada)}")
    print(f"👥 Reembolsos a Receber:         {formatar_moeda(reembolso_efetivado)}")
    print(f"👤 Custo Real Efetivado:         {formatar_moeda(custo_real_efetivado)}")
    print(f"💰 SOBRA ATUAL EM CAIXA:         {formatar_moeda(sobra_atual)}")
    print("-" * 60)
    print(f"⏳ Gastos Fixos Previstos:       {formatar_moeda(total_previsto)}")
    print(f"🎯 SOBRA LÍQUIDA PROJETADA:      {formatar_moeda(sobra_projetada)}")
    print("=" * 60)

def carregar_gastos_fixos_do_mes(mes_ref="SET"):
    # Busca despesas recorrentes cadastradas
    rec = supabase.table("despesas_recorrentes").select("*").execute().data
    if not rec:
        print("Nenhuma despesa fixa configurada na tabela 'despesas_recorrentes'.")
        return

    # Busca o que já existe no mês para não duplicar
    existentes = supabase.table("despesas").select("descricao").eq("mes_referencia", mes_ref.upper()).execute().data
    nomes_existentes = [d["descricao"].upper() for d in existentes]

    inseridos = 0
    for item in rec:
        if item["descricao"].upper() not in nomes_existentes:
            dados = {
                "mes_referencia": mes_ref.upper(),
                "descricao": item["descricao"],
                "valor_total": float(item["valor_estimado"]),
                "cartao_nome": item.get("cartao_sugerido"),
                "categoria_nome": item.get("categoria_nome"),
                "divisao": "MEU",
                "valor_meu": float(item["valor_estimado"]),
                "valor_reembolso": 0.0,
                "status": "PREVISTO"
            }
            supabase.table("despesas").insert(dados).execute()
            inseridos += 1

    print(f"\n✅ {inseridos} gastos fixos carregados como 'PREVISTO' para o mês de {mes_ref.upper()}!")
    consultar_saldo(mes_ref)

def efetivar_gasto_previsto(mes_ref="SET"):
    # Lista despesas que estão como PREVISTO
    res = supabase.table("despesas").select("*").eq("mes_referencia", mes_ref.upper()).eq("status", "PREVISTO").execute()
    previstos = res.data

    if not previstos:
        print("\nNenhum gasto previsto pendente para este mês!")
        return

    print(f"\n--- GASTOS PREVISTOS PENDENTES ({mes_ref.upper()}) ---")
    for i, item in enumerate(previstos, start=1):
        print(f"  {i} - {item['descricao']} (Estimado: {formatar_moeda(float(item['valor_total']))})")

    escolha = int(input("\nSelecione o número do item que foi cobrado: ").strip())
    if not (1 <= escolha <= len(previstos)):
        print("Opção inválida.")
        return

    item_selecionado = previstos[escolha - 1]

    # Confirmar ou ajustar o valor cobrado real
    val_input = input(f"Valor real cobrado [Enter para manter {formatar_moeda(float(item_selecionado['valor_total']))}]: ").strip()
    valor_real = float(val_input.replace(",", ".")) if val_input else float(item_selecionado["valor_total"])

    # Selecionar o cartão onde a cobrança caiu
    cartoes_res = supabase.table("cartoes").select("nome").order("nome").execute()
    cartoes = [c["nome"] for c in cartoes_res.data]
    print("\nEm qual cartão/conta caiu essa cobrança?")
    for i, c_nome in enumerate(cartoes, start=1):
        print(f"  {i} - {c_nome}")
    c_idx = int(input("Escolha o cartão: ").strip())
    cartao_nome = cartoes[c_idx - 1] if 1 <= c_idx <= len(cartoes) else None

    # Atualiza no Supabase para EFETIVADO
    supabase.table("despesas").update({
        "valor_total": valor_real,
        "valor_meu": valor_real,
        "cartao_nome": cartao_nome,
        "status": "EFETIVADO"
    }).eq("id", item_selecionado["id"]).execute()

    print(f"\n✅ {item_selecionado['descricao']} efetivado com sucesso no cartão {cartao_nome}!")
    consultar_saldo(mes_ref)

def lancar_gasto(mes_ref="SET"):
    print(f"\n==========================================")
    print(f"       NOVO LANÇAMENTO - {mes_ref.upper()}")
    print("==========================================")
    desc = input("Descrição do gasto: ").strip()
    valor_total = float(input("Valor TOTAL da compra (ex: 50.00): ").replace(",", "."))

    cartoes_res = supabase.table("cartoes").select("nome").order("nome").execute()
    cartoes = [c["nome"] for c in cartoes_res.data]
    print("\n💳 QUAL CARTÃO FOI USADO?")
    for i, c_nome in enumerate(cartoes, start=1):
        print(f"  {i} - {c_nome}")
    print(f"  {len(cartoes) + 1} - Outro / Sem Cartão")
    escolha_c = int(input("Escolha o cartão: ").strip())
    cartao_nome = cartoes[escolha_c - 1] if 1 <= escolha_c <= len(cartoes) else None

    cat_res = supabase.table("categorias").select("nome").order("nome").execute()
    categorias = [cat["nome"] for cat in cat_res.data]
    print("\n🏷️ CATEGORIA DO GASTO:")
    for i, cat_nome in enumerate(categorias, start=1):
        print(f"  {i} - {cat_nome}")
    escolha_cat = int(input("Escolha a categoria: ").strip())
    categoria_nome = categorias[escolha_cat - 1] if 1 <= escolha_cat <= len(categorias) else "OUTROS"

    print("\n👥 DE QUEM É ESSE GASTO?")
    print("  1 - 100% Meu")
    print("  2 - 100% de Terceiro (reembolso integral)")
    print("  3 - Dividido 50/50 com alguém")
    divisao_op = input("Escolha (1, 2 ou 3): ").strip()

    pessoa_nome = None
    if divisao_op in ["2", "3"]:
        pessoas_res = supabase.table("pessoas").select("nome").order("nome").execute()
        pessoas = [p["nome"] for p in pessoas_res.data]
        print("\nCom quem é essa despesa?")
        for i, p_nome in enumerate(pessoas, start=1):
            print(f"  {i} - {p_nome}")
        escolha_p = int(input("Escolha a pessoa: ").strip())
        pessoa_nome = pessoas[escolha_p - 1] if 1 <= escolha_p <= len(pessoas) else "EDUARDO"

    if divisao_op == "2":
        divisao_txt = "TERCEIRO"
        valor_meu = 0.0
        valor_reembolso = valor_total
    elif divisao_op == "3":
        divisao_txt = "50/50"
        valor_meu = valor_total / 2
        valor_reembolso = valor_total / 2
    else:
        divisao_txt = "MEU"
        valor_meu = valor_total
        valor_reembolso = 0.0

    dados = {
        "mes_referencia": mes_ref.upper(),
        "descricao": desc,
        "valor_total": valor_total,
        "cartao_nome": cartao_nome,
        "categoria_nome": categoria_nome,
        "pessoa_nome": pessoa_nome,
        "divisao": divisao_txt,
        "valor_meu": valor_meu,
        "valor_reembolso": valor_reembolso,
        "status": "EFETIVADO"
    }

    supabase.table("despesas").insert(dados).execute()
    print("\n✅ Despesa cadastrada com sucesso!")
    consultar_saldo(mes_ref)

def gerenciar_cadastros():
    while True:
        print("\n" + "=" * 45)
        print("       ⚙️ GERENCIADOR DE CADASTROS")
        print("=" * 45)
        print("1 - Cadastrar Novo Cartão")
        print("2 - Cadastrar Nova Pessoa")
        print("3 - Cadastrar Nova Categoria")
        print("4 - Adicionar Novo Gasto Recorrente Padrão")
        print("0 - Voltar ao Menu Principal")
        escolha = input("Selecione uma opção: ").strip()

        if escolha == "1":
            novo = input("Nome do novo cartão: ").strip().upper()
            if novo:
                supabase.table("cartoes").insert({"nome": novo}).execute()
                print(f"✅ Cartão '{novo}' cadastrado!")
        elif escolha == "2":
            nova_pessoa = input("Nome da pessoa: ").strip().upper()
            if nova_pessoa:
                supabase.table("pessoas").insert({"nome": nova_pessoa}).execute()
                print(f"✅ Pessoa '{nova_pessoa}' cadastrada!")
        elif escolha == "3":
            nova_cat = input("Nome da categoria: ").strip().upper()
            if nova_cat:
                supabase.table("categorias").insert({"nome": nova_cat}).execute()
                print(f"✅ Categoria '{nova_cat}' cadastrada!")
        elif escolha == "4":
            desc = input("Nome do gasto fixo (ex: INTERNET): ").strip().upper()
            val = float(input("Valor estimado (ex: 120.00): ").replace(",", "."))
            supabase.table("despesas_recorrentes").insert({"descricao": desc, "valor_estimado": val}).execute()
            print(f"✅ Recorrente '{desc}' cadastrado!")
        elif escolha == "0":
            break

if __name__ == "__main__":
    while True:
        print("\n" + "=" * 45)
        print("       💼 SISTEMA FINANCEIRO")
        print("=" * 45)
        print("1 - Consultar Balanço do Mês")
        print("2 - Lançar Novo Gasto")
        print("3 - Carregar Gastos Fixos do Mês (Previsão)")
        print("4 - Efetivar Cobrança de Gasto Previsto no Cartão")
        print("5 - Gerenciar Cadastros")
        print("0 - Sair")
        opcao = input("Opção: ").strip()

        if opcao == "1":
            consultar_saldo("SET")
        elif opcao == "2":
            lancar_gasto("SET")
        elif opcao == "3":
            carregar_gastos_fixos_do_mes("SET")
        elif opcao == "4":
            efetivar_gasto_previsto("SET")
        elif opcao == "5":
            gerenciar_cadastros()
        elif opcao == "0":
            break