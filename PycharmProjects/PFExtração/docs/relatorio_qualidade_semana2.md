# Relatório de Qualidade de Dados — Semana 2

## Sumário da Validação

| Métrica | Valor |
|---|---|
| Países únicos em staging | 30 |
| Total de linhas (país × ano) | 747 |
| Linhas com velocidade Wikipedia | 747 |
| Países com dados de velocidade | 30 |
| Anos cobertos | 2000 – 2024 |

## Fontes Processadas

- **Internet (Banco Mundial):** 747 linhas após limpeza
- **PIB (Banco Mundial):** 750 linhas após limpeza
- **Velocidades (Wikipedia):** 153 países carregados

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
