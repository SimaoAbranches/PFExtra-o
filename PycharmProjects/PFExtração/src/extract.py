import os
import json
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO  # 🌟 Adicionado para corrigir o bug do read_html

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(DATA_RAW_DIR, exist_ok=True)

# =============================================================================
# CONFIGURAÇÃO: os 30 países que existem na Wikipedia CSV
# Chaves ISO3 do Banco Mundial → nomes exatos que o Banco Mundial usa
# =============================================================================
PAISES_ALVO_ISO3 = [
    "USA", "CAN", "MEX", "BRA", "ARG", "CHL",
    "GBR", "FRA", "DEU", "ITA", "ESP", "PRT", "NLD", "CHE",
    "KOR", "JPN", "CHN", "IND", "SGP", "IDN",
    "SAU", "ZAF", "EGY", "NGA", "KEN", "MAR",
    "AUS", "NZL", "RUS", "TUR"
]

# URL base da API do Banco Mundial
API_BASE = "https://api.worldbank.org/v2"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# =============================================================================
# FUNÇÃO: Extrair indicador do Banco Mundial para países específicos
# =============================================================================
def extrair_indicador_banco_mundial(indicador: str, nome_ficheiro: str):
    codigos = ";".join(PAISES_ALVO_ISO3)
    url = (
        f"{API_BASE}/country/{codigos}/indicator/{indicador}"
        f"?format=json&per_page=1000&date=2000:2024"
    )

    print(f"\n[EXTRACT] Indicador: {indicador}")
    print(f"[EXTRACT] URL: {url}")

    todos_os_registos = []
    pagina = 1

    while True:
        url_paginada = f"{url}&page={pagina}"
        try:
            resposta = requests.get(url_paginada, headers=HEADERS, timeout=30)
            resposta.raise_for_status()
            dados = resposta.json()
        except Exception as e:
            print(f"[ERRO] Falha na página {pagina}: {e}")
            break

        meta = dados[0]
        registos = dados[1] if len(dados) > 1 else []

        if not registos:
            print(f"[WARN] Sem registos na página {pagina}.")
            break

        todos_os_registos.extend(registos)
        print(f"[OK] Página {pagina}/{meta.get('pages')} — {len(registos)} registos")

        if pagina >= meta.get("pages", 1):
            break

        pagina += 1
        time.sleep(0.5)  # respeitar rate limit

    print(f"[EXTRACT] Total recolhido: {len(todos_os_registos)} registos para '{indicador}'")

    caminho = os.path.join(DATA_RAW_DIR, nome_ficheiro)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump([{"total": len(todos_os_registos)}, todos_os_registos], f, ensure_ascii=False, indent=2)

    print(f"[SAVE] Guardado em: {caminho}")
    return todos_os_registos


# =============================================================================
# FUNÇÃO: Scraping da Wikipedia (CORRIGIDA)
# =============================================================================
def extrair_velocidades_wikipedia():
    url = "https://en.wikipedia.org/wiki/List_of_countries_by_Internet_connection_speeds"
    print(f"\n[SCRAPING] Wikipedia: {url}")

    try:
        resposta = requests.get(url, headers=HEADERS, timeout=30)
        resposta.raise_for_status()
    except Exception as e:
        print(f"[ERRO] Scraping falhou: {e}")
        return

    soup = BeautifulSoup(resposta.text, "html.parser")
    tabelas = soup.find_all("table", {"class": "wikitable"})

    if not tabelas:
        print("[WARN] Nenhuma tabela wikitable encontrada.")
        return

    for tabela in tabelas:
        colunas_verificar = [str(th.text).lower() for th in tabela.find_all("th")]
        if any("speed" in c or "mbit" in c or "country" in c for c in colunas_verificar):
            # 🌟 CORREÇÃO: Converter a string HTML num stream em memória com StringIO
            html_stream = StringIO(str(tabela))
            df = pd.read_html(html_stream)[0]

            caminho = os.path.join(DATA_RAW_DIR, "internet_speeds_scraping.csv")
            df.to_csv(caminho, index=False, encoding="utf-8")
            print(f"[OK] {len(df)} países guardados em: {caminho}")
            print(f"[OK] Colunas: {df.columns.tolist()}")
            return

    print("[WARN] Nenhuma tabela com colunas de velocidade encontrada.")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE DE EXTRAÇÃO — VERSÃO CORRIGIDA")
    print("Objetivo: extrair dados a nível de PAÍSES INDIVIDUAIS")
    print("============================================================")

    # 1. Internet usage
    extrair_indicador_banco_mundial(
        indicador="IT.NET.USER.ZS",
        nome_ficheiro="internet_usage_all.json"
    )

    # 2. PIB
    extrair_indicador_banco_mundial(
        indicador="NY.GDP.MKTP.CD",
        nome_ficheiro="pib_all.json"
    )

    # 3. Velocidades de internet (Wikipedia)
    extrair_velocidades_wikipedia()

    print("\n" + "=" * 60)
    print("Extração concluída com sucesso!")
    print("=" * 60)

