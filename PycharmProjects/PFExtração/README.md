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

Como Executar:
Instalar dependências:
pip install -r requirements.txt

Configurar o ficheiro .env na raiz com:
Fragmento do código:
API_URL=https://api.worldbank.org/v2

Executar o pipeline de extração:
python src/extract.py
