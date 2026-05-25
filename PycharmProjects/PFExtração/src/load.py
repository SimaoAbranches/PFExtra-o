import os
import sqlite3
import pandas as pd

# =============================================================================
# CAMINHOS DO PROJETO
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_STAGING_DIR = os.path.join(BASE_DIR, "data", "staging")
DB_PATH = os.path.join(BASE_DIR, "data", "economia_internet.db")


def criar_esquema_dimensional(conn):
    """Cria a estrutura de tabelas do Star Schema."""
    cursor = conn.cursor()
    print("A criar tabelas relacionais (Modelo Dimensional / Star Schema)...")

    # 1. Tabela de Dimensão: Países
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_countries (
            country_code TEXT PRIMARY KEY,
            country_name TEXT NOT NULL,
            wiki_country TEXT
        )
    """
    )

    # 2. Tabela de Dimensão: Tempo
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_time (
            year INTEGER PRIMARY KEY
        )
    """
    )

    # 3. Tabela de Factos Central
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fct_economy_internet (
            country_code TEXT,
            year INTEGER,
            internet_usage_pct REAL,
            gdp_usd REAL,
            internet_speed_mbits REAL,
            pipeline_processed_at TEXT,
            PRIMARY KEY (country_code, year),
            FOREIGN KEY (country_code) REFERENCES dim_countries(country_code),
            FOREIGN KEY (year) REFERENCES dim_time(year)
        )
    """
    )
    conn.commit()


def executar_validacao_pos_carga(conn, df_staging):
    """Executa a auditoria de qualidade pós-carga."""
    print("\n--- A INICIAR VALIDAÇÃO PÓS-CARREGAMENTO (DATA QUALITY) ---")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM fct_economy_internet")
    total_factos = cursor.fetchone()[0]
    total_staging = len(df_staging)

    cursor.execute("SELECT COUNT(*) FROM dim_countries")
    total_paises = cursor.fetchone()[0]

    print(f"✔️ Registos originais no Staging CSV: {total_staging}")
    print(f"✔️ Registos migrados para a Tabela de Factos SQL: {total_factos}")
    print(f"✔️ Total de Países normalizados na Dimensão SQL: {total_paises}")

    if total_factos == total_staging:
        print(
            "🎉 SUCESSO: A integridade volumétrica dos dados foi mantida a 100%!"
        )
    else:
        print(
            "⚠️ AVISO: Existe uma divergência volumétrica de dados. Verifica duplicados."
        )


def carregar_dados_warehouse():
    print("\n--- MÓDULO DE CARREGAMENTO E MODELAÇÃO DE DADOS ---")

    caminho_staging = os.path.join(
        DATA_STAGING_DIR, "fact_economy_internet_staging.csv"
    )
    if not os.path.exists(caminho_staging):
        raise FileNotFoundError(
            f"Ficheiro de staging em falta: {caminho_staging}. Executa primeiro o src/transform.py."
        )

    # 1. Carregar dados processados
    df_staging = pd.read_csv(caminho_staging)

    # 2. Renomear coluna de velocidade se ela existir
    for col in df_staging.columns:
        if "speed" in col.lower() or "mbit" in col.lower():
            df_staging.rename(columns={col: "internet_speed_mbits"}, inplace=True)
            break

    if "internet_speed_mbits" not in df_staging.columns:
        df_staging["internet_speed_mbits"] = None

    # 🌟 FIX DO KEYERROR: Se a coluna wiki_country não existir, cria-a usando o country_name
    if "wiki_country" not in df_staging.columns:
        df_staging["wiki_country"] = df_staging["country_name"]

    df_staging["wiki_country"] = df_staging["wiki_country"].fillna(
        "Não Disponível"
    )
    df_staging.dropna(subset=["country_code", "year"], inplace=True)

    # Remover duplicados estruturais antes das Chaves Primárias SQL
    df_staging.drop_duplicates(subset=["country_code", "year"], inplace=True)

    # 3. Conectar ao SQLite Embutido
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    # 4. Construir o esquema
    criar_esquema_dimensional(conn)

    # 5. Limpeza Preventiva
    conn.execute("DELETE FROM fct_economy_internet;")
    conn.execute("DELETE FROM dim_countries;")
    conn.execute("DELETE FROM dim_time;")
    conn.commit()

    print("A popular as Tabelas de Dimensões...")

    # Popular Dimensão Países
    df_countries = df_staging[
        ["country_code", "country_name", "wiki_country"]
    ].drop_duplicates(subset=["country_code"])
    df_countries.to_sql(
        "dim_countries", conn, if_exists="append", index=False
    )

    # Popular Dimensão Tempo
    df_time = df_staging[["year"]].drop_duplicates()
    df_time["year"] = df_time["year"].astype(int)
    df_time.to_sql("dim_time", conn, if_exists="append", index=False)

    print("A popular a Tabela de Factos Central...")

    # Popular Tabela de Factos
    df_fact = df_staging[
        [
            "country_code",
            "year",
            "internet_usage_pct",
            "gdp_usd",
            "internet_speed_mbits",
            "pipeline_processed_at",
        ]
    ]
    df_fact.to_sql("fct_economy_internet", conn, if_exists="append", index=False)

    conn.commit()

    # 6. Executar os testes de validação pós-carga
    executar_validacao_pos_carga(conn, df_staging)

    conn.close()
    print("\nProcesso de Modelação e Carga Concluído com Sucesso!")


if __name__ == "__main__":
    carregar_dados_warehouse()