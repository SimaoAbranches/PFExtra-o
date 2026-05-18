Projeto ETD: Engenharia de Dados & Visualização Analítica

O objetivo é analisar a relação entre o desenvolvimento económico (PIB) e a infraestrutura digital (Internet).

Estado do Projeto: Semana 1 (Extract)
Nesta fase, estabelecemos a fundação do pipeline, focando na recolha de dados brutos (Raw) e na organização do ambiente de trabalho.

Fontes de Dados:
A extração foca-se em três pilares, garantindo a rastreabilidade e integridade:
- API Banco Mundial (JSON): Recolha dos indicadores de Penetração de Internet (IT.NET.USER.ZS) e PIB (NY.GDP.MKTP.CD). Implementada com paginação (1000 registos/página) para eficiência.
- Wikipedia (Scraping/CSV): Extração de Velocidades de Internet via scraping da lista global de países. Implementado com User-Agent para garantir acessibilidade e evitar bloqueios.
- Licenciamento: Dados públicos sob a licença World Bank Dataset Terms of Use (CC-BY 4.0).

Estrutura do Repositório:
Plaintext
├── data/raw/          # Dados brutos imutáveis (JSON/CSV)
├── src/               # Código fonte
│   └── extract.py     # Script de extração, scraping e logging
├── .env               # Configurações de API (excluído do Git por segurança)
├── requirements.txt   # Dependências (pandas, requests, lxml, python-dotenv)
└── README.md          # Documentação

Decisões Técnicas e Implementação:
- Ficheiros salvos com prefixos claros por indicador e formato original (pib_all.json).
- Implementado registo visual na consola para monitorizar o estado de cada chamada à API e sucesso do scraping.
- Os dados são guardados sem alterações na camada raw, garantindo que o pipeline possa ser reexecutado de forma determinística.

Logs de Desenvolvimento:
- Desafio: Bloqueio 403 no scraping da Wikipedia.
- Solução: Adição de Request Headers simulando um navegador real.
- Uso de IA: Utilizada para acelerar a criação do fluxo de diretórios dinâmico e estruturar o tratamento de exceções nos pedidos HTTP.

##  Fase 2: Transformação e Qualidade de Dados (Semana 2)
Nesta fase, o pipeline processa os dados brutos da camada `raw` e consolida-os na camada `staging`.

### O que é feito:
1. **Limpeza e Tipificação:** Conversão de strings e campos aninhados do Banco Mundial para tipos numéricos apropriados (`float` e `int`).
2. **Data Quality (Regras de Validação):**
   - Remoção de registos com indicadores analíticos nulos.
   - Forçamento de intervalos plausíveis (Percentagem de utilizadores de internet restrita a [0, 100]).
   - Garantia de integridade (PIB não pode ser negativo).
3. **Estratégia de Matching (Cruzamento):** Resolução de divergências de nomes de países entre a API do Banco Mundial e o Scraping (ex: mapeamento de "Russia" para "Russian Federation").


Como Executar:
Instalar dependências:

pip install -r requirements.txt
```bash
Configurar o ficheiro .env na raiz com:
```
Fragmento do código:
```bash
API_URL=https://api.worldbank.org/v2
```
Executar o pipeline de extração:
```bash
python src/extract.py
```
Executar o pipeline de transformação:
```bash
python src/transform.py
```
