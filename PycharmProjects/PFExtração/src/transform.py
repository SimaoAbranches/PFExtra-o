import os
import json
import pandas as pd

#Caminhos 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DATA_STAGING_DIR = os.path.join(BASE_DIR, "data", "staging")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

# FIX PRINCIPAL: Mapeamento de nomes entre Wikipedia e Banco Mundial
# O Banco Mundial usa nomes oficiais/formais que diferem dos nomes comuns
# usados na Wikipedia. Sem este mapeamento, o Left Join produz 0 matches.
# Formato: "NOME_WIKIPEDIA_UPPERCASE" -> "NOME_BANCO_MUNDIAL_UPPERCASE"
MAPA_NOMES_WIKI_PARA_BANCO_MUNDIAL = {
    "RUSSIA": "RUSSIAN FEDERATION",
    "SOUTH KOREA": "KOREA, REP.",
    "TURKEY": "TURKIYE",  
    "EGYPT": "EGYPT, ARAB REP.",
    "IRAN": "IRAN, ISLAMIC REP.",
    "VENEZUELA": "VENEZUELA, RB",
    "SYRIA": "SYRIAN ARAB REPUBLIC",
    "LAOS": "LAO PDR",
    "VIETNAM": "VIET NAM",
    "CZECH REPUBLIC": "CZECHIA",
}


def carregar_json_banco_mundial(nome_ficheiro: str) -> list:
    """Carrega JSON do Banco Mundial e retorna a lista de registos."""
    caminho = os.path.join(DATA_RAW_DIR, nome_ficheiro)
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Ficheiro não encontrado: {caminho}")
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if isinstance(dados, list) and len(dados) > 1:
        return dados[1]
    return []


def processar_banco_mundial(dados_lista: list, nome_coluna_valor: str) -> pd.DataFrame:
    """
    Converte a lista raw do Banco Mundial num DataFrame limpo.

    FIX: Agora também filtra entidades do tipo 'Aggregates' (regiões),
    garantindo que só ficam países individuais no pipeline.
    O campo 'region' do Banco Mundial tem valor {'id': 'NA', 'value': 'Aggregates'}
    para entidades não-país.
    """
    registos = []
    ignorados_agregados = 0

    for item in dados_lista:
        # remover agregados regionais
        regiao = item.get("region", {})
        if isinstance(regiao, dict) and regiao.get("value") == "Aggregates":
            ignorados_agregados += 1
            continue

        pais_nome = item.get("country", {}).get("value") if item.get("country") else None
        pais_id = item.get("countryiso3code")
        ano = item.get("date")
        valor = item.get("value")

        if pais_nome and ano:
            registos.append({
                "country_code": str(pais_id).strip().upper() if pais_id else "N/A",
                "country_name": str(pais_nome).strip(),
                "year": str(ano).strip(),
                nome_coluna_valor: valor
            })

    if ignorados_agregados:
        print(f"  [DQ] {ignorados_agregados} agregados regionais removidos.")

    return pd.DataFrame(registos)


def aplicar_regras_qualidade(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    """
    Aplica as regras de qualidade:
      1. Remover nulos analíticos
      2. Forçar intervalos plausíveis
      3. Garantir integridade (PIB não negativo)
    """
    n_inicial = len(df)
    coluna_valor = [c for c in df.columns if c not in ("country_code", "country_name", "year")][0]

    # Regra 1: Remover nulos analíticos
    df = df.dropna(subset=[coluna_valor])

    # Regra 2 & 3: Intervalos plausíveis
    if "internet_usage_pct" in df.columns:
        df = df[(df["internet_usage_pct"] >= 0) & (df["internet_usage_pct"] <= 100)]
    if "gdp_usd" in df.columns:
        df = df[df["gdp_usd"] > 0]

    # Regra 4: Remover duplicados
    n_dup = df.duplicated(subset=["country_name", "year"]).sum()
    df = df.drop_duplicates(subset=["country_name", "year"])

    print(f"  [DQ] {nome}: {n_inicial} → {len(df)} linhas "
          f"(removidos {n_inicial - len(df)} nulos/inválidos, {n_dup} duplicados)")
    return df


def transformar_e_integrar():
    print("\n" + "=" * 60)
    print("PIPELINE DE TRANSFORMAÇÃO — VERSÃO CORRIGIDA")
    print("=" * 60)
    os.makedirs(DATA_STAGING_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. CARREGAR DADOS BRUTOS
    print("\n[1/6] A carregar dados brutos...")
    dados_raw_internet = carregar_json_banco_mundial("internet_usage_all.json")
    dados_raw_pib = carregar_json_banco_mundial("pib_all.json")
    caminho_wiki = os.path.join(DATA_RAW_DIR, "internet_speeds_scraping.csv")
    df_wiki_raw = pd.read_csv(caminho_wiki)

    print(f"  Raw internet: {len(dados_raw_internet)} registos JSON")
    print(f"  Raw PIB:      {len(dados_raw_pib)} registos JSON")
    print(f"  Raw Wikipedia:{len(df_wiki_raw)} países")

    # 2. PROCESSAR E LIMPAR BANCO MUNDIAL
    print("\n[2/6] A processar e limpar dados do Banco Mundial...")
    df_internet = processar_banco_mundial(dados_raw_internet, "internet_usage_pct")
    df_pib = processar_banco_mundial(dados_raw_pib, "gdp_usd")

    # Alinhamento de tipos
    for df in (df_internet, df_pib):
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["country_name"] = df["country_name"].astype(str).str.strip().str.upper()

    # Aplicar regras de qualidade
    df_internet = aplicar_regras_qualidade(df_internet, "Internet")
    df_pib = aplicar_regras_qualidade(df_pib, "PIB")

    # 3. INNER JOIN: Banco Mundial (Internet × PIB)
    print("\n[3/6] A cruzar Internet × PIB (Inner Join por país e ano)...")
    df_banco_mundial = pd.merge(
        df_internet[["country_code", "country_name", "year", "internet_usage_pct"]],
        df_pib[["country_name", "year", "gdp_usd"]],
        on=["country_name", "year"],
        how="inner"
    )
    print(f"  Resultado: {len(df_banco_mundial)} linhas | "
          f"{df_banco_mundial['country_name'].nunique()} países únicos")

    # 4. PREPARAR DADOS DA WIKIPEDIA
    #    FIX: aplicar mapeamento de nomes antes do join
    print("\n[4/6] A preparar dados da Wikipedia com mapeamento de nomes...")
    df_wiki = df_wiki_raw.copy()

    # Normalizar nome da coluna de país
    coluna_pais = df_wiki.columns[0]
    df_wiki.rename(columns={coluna_pais: "wiki_country_original"}, inplace=True)
    df_wiki["wiki_country"] = df_wiki["wiki_country_original"].astype(str).str.strip().str.upper()

    # Normalizar nome da coluna de velocidade
    colunas_velocidade = [c for c in df_wiki.columns if "speed" in c.lower() or "mbit" in c.lower()]
    if colunas_velocidade:
        df_wiki.rename(columns={colunas_velocidade[0]: "avg_connection_speed_mbit"}, inplace=True)

    # Aplicar mapeamento de nomes
    df_wiki["wiki_country_mapped"] = df_wiki["wiki_country"].replace(MAPA_NOMES_WIKI_PARA_BANCO_MUNDIAL)

    matches_aplicados = (df_wiki["wiki_country"] != df_wiki["wiki_country_mapped"]).sum()
    print(f"  Mapeamentos de nomes aplicados: {matches_aplicados}")
    for _, row in df_wiki[df_wiki["wiki_country"] != df_wiki["wiki_country_mapped"]].iterrows():
        print(f"    '{row['wiki_country']}' → '{row['wiki_country_mapped']}'")

    # 5. LEFT JOIN: Banco Mundial ← Wikipedia
    #    Usa a coluna mapeada para garantir matches correctos
    print("\n[5/6] A acoplar velocidades da Wikipedia (Left Join)...")
    colunas_wiki = ["wiki_country_mapped", "wiki_country_original", "avg_connection_speed_mbit"]
    colunas_wiki_existentes = [c for c in colunas_wiki if c in df_wiki.columns]

    df_final = pd.merge(
        df_banco_mundial,
        df_wiki[colunas_wiki_existentes],
        left_on="country_name",
        right_on="wiki_country_mapped",
        how="left"
    )

    # Limpar coluna auxiliar de mapeamento
    df_final.drop(columns=["wiki_country_mapped"], errors="ignore", inplace=True)

    # Estatísticas de matching
    n_com_velocidade = df_final["avg_connection_speed_mbit"].notna().sum()
    paises_com_vel = df_final[df_final["avg_connection_speed_mbit"].notna()]["country_name"].nunique()
    print(f"  Linhas COM velocidade: {n_com_velocidade} ({paises_com_vel} países)")
    print(f"  Linhas SEM velocidade: {df_final['avg_connection_speed_mbit'].isna().sum()} (aceitável — Left Join)")

    # Formatação final
    df_final["country_name"] = df_final["country_name"].str.title()
    df_final["pipeline_processed_at"] = pd.Timestamp.now()
    df_final.sort_values(by=["country_name", "year"], inplace=True)
    df_final.reset_index(drop=True, inplace=True)

    # 6. GRAVAR STAGING
    print("\n[6/6] A guardar camada staging...")
    caminho_saida = os.path.join(DATA_STAGING_DIR, "fact_economy_internet_staging.csv")
    df_final.to_csv(caminho_saida, index=False, encoding="utf-8")
    print(f"  [OK] {len(df_final)} linhas guardadas em: {caminho_saida}")
    print(f"  [OK] Países únicos: {df_final['country_name'].nunique()}")
    print(f"  [OK] Anos cobertos: {int(df_final['year'].min())} – {int(df_final['year'].max())}")

    # GERAR RELATÓRIO
    gerar_relatorio(df_final, df_internet, df_pib, df_wiki, paises_com_vel)

    return df_final


def gerar_relatorio(df_final, df_internet, df_pib, df_wiki, paises_com_vel):
    """Gera automaticamente o relatório de qualidade de dados."""
    caminho = os.path.join(DOCS_DIR, "relatorio_qualidade_semana2.md")
    n_total = len(df_final)
    n_paises = df_final["country_name"].nunique()
    n_com_vel = df_final["avg_connection_speed_mbit"].notna().sum()

    relatorio = f"""# Relatório de Qualidade de Dados — Semana 2

## Sumário da Validação

| Métrica | Valor |
|---|---|
| Países únicos em staging | {n_paises} |
| Total de linhas (país × ano) | {n_total} |
| Linhas com velocidade Wikipedia | {n_com_vel} |
| Países com dados de velocidade | {paises_com_vel} |
| Anos cobertos | {int(df_final['year'].min())} – {int(df_final['year'].max())} |

## Fontes Processadas

- **Internet (Banco Mundial):** {len(df_internet)} linhas após limpeza
- **PIB (Banco Mundial):** {len(df_pib)} linhas após limpeza
- **Velocidades (Wikipedia):** {len(df_wiki)} países carregados

## Regras de Qualidade Aplicadas

1. **Remoção de nulos analíticos** — registos sem valor de indicador descartados
2. **Intervalo plausível** — `internet_usage_pct` restrita a [0, 100]%
3. **Integridade do PIB** — `gdp_usd` deve ser > 0
4. **Deduplicação** — pares (país, ano) duplicados removidos
5. **Filtro de agregados regionais** — entidades do Banco Mundial do tipo "Aggregates" excluídas (regiões como "East Asia & Pacific" não são países)

## Estratégia de Matching (Wikipedia × Banco Mundial)

O cruzamento usa Left Join por nome de país (uppercase), com mapeamento explícito
para os casos em que o Banco Mundial usa nomes oficiais distintos dos nomes comuns:

| Wikipedia | Banco Mundial |
|---|---|
| Russia | Russian Federation |
| South Korea | Korea, Rep. |
| Turkey | Turkiye |
| Egypt | Egypt, Arab Rep. |

## Decisões Técnicas

- **Inner Join** entre Internet e PIB: preserva apenas registos com ambos os indicadores disponíveis para o mesmo país e ano.
- **Left Join** com Wikipedia: preserva todo o histórico económico, aceitando nulos nas velocidades para países sem dados de velocidade.
- **Filtro ISO3 na extracção**: a versão corrigida do `extract.py` usa códigos ISO3 explícitos para garantir que a API retorna apenas países individuais, não agregados regionais.
"""

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(relatorio)
    print(f"\n  [OK] Relatório gerado em: {caminho}")


if __name__ == "__main__":
    transformar_e_integrar()
    print("\nTransformação concluída com sucesso!\n")
