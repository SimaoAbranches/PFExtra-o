import os
import json
import pandas as pd

# Definição de caminhos dinâmicos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DATA_STAGING_DIR = os.path.join(BASE_DIR, "data", "staging")


def carregar_json_banco_mundial(nome_ficheiro):
    caminho = os.path.join(DATA_RAW_DIR, nome_ficheiro)
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Ficheiro não encontrado: {caminho}")
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if isinstance(dados, list) and len(dados) > 1:
        return dados[1]
    return []


def processar_banco_mundial(dados_lista, nome_coluna_valor):
    registos = []
    for item in dados_lista:
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
    df = pd.DataFrame(registos)
    return df


def transformar_e_integrar():
    print("\nIniciando Pipeline com Alinhamento Estrito de Tipos...")
    os.makedirs(DATA_STAGING_DIR, exist_ok=True)

    # 1. Carregar dados brutos
    dados_raw_internet = carregar_json_banco_mundial("internet_usage_all.json")
    dados_raw_pib = carregar_json_banco_mundial("pib_all.json")

    caminho_wiki = os.path.join(DATA_RAW_DIR, "internet_speeds_scraping.csv")
    df_wiki_raw = pd.read_csv(caminho_wiki)

    # 2. Processar tabelas do Banco Mundial
    df_internet = processar_banco_mundial(dados_raw_internet, "internet_usage_pct")
    df_pib = processar_banco_mundial(dados_raw_pib, "gdp_usd")

    # Limpar nulos analíticos nas colunas numéricas
    df_internet.dropna(subset=["internet_usage_pct"], inplace=True)
    df_pib.dropna(subset=["gdp_usd"], inplace=True)

    # Alinhamento de tipos:
    df_internet["year"] = pd.to_numeric(df_internet["year"], errors="coerce")
    df_pib["year"] = pd.to_numeric(df_pib["year"], errors="coerce")
    df_internet["country_name"] = df_internet["country_name"].astype(str).str.strip().str.upper()
    df_pib["country_name"] = df_pib["country_name"].astype(str).str.strip().str.upper()

    # 3. Cruzamento do Banco Mundial por Nome e Ano (Inner)
    print("A realizar o cruzamento interno do Banco Mundial...")
    df_banco_mundial = pd.merge(
        df_internet[["country_code", "country_name", "year", "internet_usage_pct"]],
        df_pib[["country_name", "year", "gdp_usd"]],
        on=["country_name", "year"],
        how="inner"
    )

    print(f"Linhas unificadas do Banco Mundial encontradas: {len(df_banco_mundial)}")

    # 4. Preparar dados da Wikipedia
    df_wiki_limpo = df_wiki_raw.copy()
    coluna_pais_wiki = df_wiki_limpo.columns[0]
    df_wiki_limpo.rename(columns={coluna_pais_wiki: "wiki_country"}, inplace=True)
    df_wiki_limpo["wiki_country"] = df_wiki_limpo["wiki_country"].astype(str).str.strip().str.upper()

    # 5. Cruzamento Final (Left Join)
    print("A acoplar dados de velocidade da Wikipedia...")
    df_final = pd.merge(
        df_banco_mundial,
        df_wiki_limpo,
        left_on="country_name",
        right_on="wiki_country",
        how="left"
    )

    # Formatação final
    df_final["country_name"] = df_final["country_name"].str.title()
    df_final["pipeline_processed_at"] = pd.Timestamp.now()

    # Ordenar por País e Ano de forma limpa
    df_final.sort_values(by=["country_name", "year"], ascending=[True, True], inplace=True)

    # 6. Gravar em Staging
    caminho_saida = os.path.join(DATA_STAGING_DIR, "fact_economy_internet_staging.csv")
    df_final.to_csv(caminho_saida, index=False, encoding="utf-8")
    print(f"Sucesso! Ficheiro guardado com {len(df_final)} linhas em: {caminho_saida}")


if __name__ == "__main__":
    transformar_e_integrar()
    print("Processo de Transformação Concluído com Sucesso!\n")