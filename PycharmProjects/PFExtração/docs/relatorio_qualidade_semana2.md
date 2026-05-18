# Relatório Curto de Qualidade de Dados (Semana 2)

## Sumário da Validação de Dados

* **Filtro de Alinhamento Geopolítico:**
  * O pipeline preservou o histórico macroeconómico completo do Banco Mundial.
  * **Total de Países e Entidades Geográficas em Staging:** 266 entidades.
  * **Nota de Integração (Wikipedia):** Devido à disparidade linguística entre os dois datasets analíticos (Wikipedia em Português e Banco Mundial em Inglês), os dados de velocidade foram acoplados via Left Join, preservando a integridade dos dados económicos e aceitando valores nulos nas velocidades para evitar a perda de histórico.

* **Registos Brutos Processados:**
  * Internet (Banco Mundial): 1000 linhas histórico
  * PIB (Banco Mundial): 1000 linhas histórico
  * Velocidades (Wikipedia): 30 países carregados
