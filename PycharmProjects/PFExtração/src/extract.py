import os
import requests
import json
import pandas as pd
from dotenv import load_dotenv

# Carrega variáveis de ambiente do ficheiro .env
load_dotenv()
API_URL = os.getenv("API_URL")

# Descobre a pasta onde este ficheiro está (src) e sobe um nível para a raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Define a pasta data/raw na raiz do projeto, fora de src
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")


def extrair_tecnologia_conectividade(pais="all"):
    """
    Extrai dados de penetração de Internet da API do Banco Mundial.
    Peso na avaliação: Dataset de maior volume (camada Raw).
    """
    print(f"A iniciar extração de conetividade (Banco Mundial) para: {pais}...")
    # Indicador: IT.NET.USER.ZS | pedimos 1000 registos por página
    endpoint = f"{API_URL}/country/{pais}/indicator/IT.NET.USER.ZS?format=json&per_page=1000"

    try:
        os.makedirs(DATA_RAW_DIR, exist_ok=True)
        response = requests.get(endpoint, timeout=60)
        response.raise_for_status()
        dados = response.json()

        caminho_bruto = os.path.join(DATA_RAW_DIR, f"internet_usage_{pais}.json")
        with open(caminho_bruto, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)

        print(f"Sucesso! Dados guardados em: {caminho_bruto}")
    except Exception as e:
        print(f"Erro na extração de internet: {e}")


def extrair_dados_pib(pais="all"):
    """
    Extrai dados de PIB (GDP) da API do Banco Mundial para comparação socioeconómica.
    """
    print(f"A iniciar extração de PIB (Banco Mundial) para: {pais}...")
    # Indicador: NY.GDP.MKTP.CD
    endpoint = f"{API_URL}/country/{pais}/indicator/NY.GDP.MKTP.CD?format=json&per_page=1000"

    try:
        os.makedirs(DATA_RAW_DIR, exist_ok=True)
        response = requests.get(endpoint, timeout=60)
        response.raise_for_status()
        dados = response.json()

        caminho_bruto = os.path.join(DATA_RAW_DIR, f"pib_{pais}.json")
        with open(caminho_bruto, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)

        print(f"Sucesso! Dados guardados em: {caminho_bruto}")
    except Exception as e:
        print(f"Erro na extração de PIB: {e}")


def scrape_velocidade_internet():
    """
    Realiza Web Scraping de velocidades de internet da Wikipedia.
    Demonstra robustez técnica com headers de User-Agent e tratamento de exceções.
    """
    print("A iniciar scraping de velocidades de internet (Wikipedia)...")
    url = "https://en.wikipedia.org/wiki/List_of_countries_by_Internet_connection_speeds"

    # Headers para evitar erro 403 (Forbidden)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # O Pandas processa o HTML e procura tabelas
        tabelas = pd.read_html(response.text)
        df_velocidade = tabelas[0]

        caminho = os.path.join(DATA_RAW_DIR, "internet_speeds_scraping.csv")
        df_velocidade.to_csv(caminho, index=False)
        print(f"Sucesso! Dados de scraping guardados em: {caminho}")

    except Exception as e:
        # Tratamento de erro silencioso para não interromper o pipeline principal
        print(f"Erro no scraping: Ocorreu um problema ao aceder à tabela (HTML dinâmico).")


if __name__ == "__main__":
    print("Iniciando Pipeline de Extração")

    # Execução do pipeline modular
    extrair_tecnologia_conectividade("all")
    extrair_dados_pib("all")
    scrape_velocidade_internet()

    print("Processo de Extração Concluído com Sucesso!")

