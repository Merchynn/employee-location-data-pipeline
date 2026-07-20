# Employee Location Data Pipeline

Pipeline público de **Analytics Engineering** que transforma um Excel de deslocamento em uma camada analítica para SQLite, PostgreSQL e Power BI.

Esta é uma reconstrução sanitizada de um projeto real. A versão pública usa somente dados sintéticos e configurações genéricas.

## Fluxo

```text
Excel local ou SharePoint
        ↓
Extração Python / Microsoft Graph
        ↓
Validação e normalização com pandas
        ↓
Cálculo geodésico residência → filial
        ↓
CSV de auditoria + staging
        ↓
SQLite demo ou PostgreSQL snapshot
        ↓
View analítica para Power BI
```

## O que o projeto demonstra

- integração opcional com SharePoint usando MSAL;
- configuração via YAML e variáveis de ambiente;
- aliases para cabeçalhos legados;
- normalização de CEP, tempo, datas, coordenadas e modais;
- validação de chaves duplicadas;
- distância de Haversine sem API paga;
- lock contra execuções simultâneas;
- staging e full refresh transacional no PostgreSQL;
- auditoria de cargas;
- execução offline e testes automatizados.

## Estrutura

```text
src/employee_location_pipeline/
  config.py      configuração tipada
  extract.py     Excel local e SharePoint
  transform.py   validações e regras analíticas
  load.py        SQLite e PostgreSQL
  pipeline.py    orquestração e lock
  sample.py      geração de dados sintéticos
  cli.py         interface de execução
tests/
docs/
sql/
```

## Executar a demonstração

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
pip install -e '.[dev]'
python -m employee_location_pipeline demo
```

No Windows PowerShell, ative o ambiente com:

```powershell
.\.venv\Scripts\Activate.ps1
```

O comando gera automaticamente um Excel sintético e cria:

```text
output/employee_locations.db
output/employee_locations_clean.csv
```

## Validar sem carregar

```bash
python -m employee_location_pipeline validate
```

## PostgreSQL opcional

```bash
docker compose up -d
cp .env.example .env
python -m employee_location_pipeline run --postgres
```

Depois, execute `sql/001_create_power_bi_view.sql`.

## SharePoint opcional

Altere `source.mode` para `sharepoint` no `config.example.yaml` e configure no ambiente:

```dotenv
SHAREPOINT_TENANT_ID=
SHAREPOINT_CLIENT_ID=
SHAREPOINT_CLIENT_SECRET=
```

## Contrato analítico

A saída representa o snapshot atual, com uma linha por pessoa. Entre os campos disponíveis estão filial, departamento, município, UF, coordenadas, tempo declarado, distância de rota, distância geodésica e indicadores de modal.

## Testes

```bash
pytest -q
```

Os cinco testes cobrem transformação, aliases, duplicidade, Haversine, link compartilhado do SharePoint e repetibilidade do snapshot SQLite.

## Segurança

- dados de demonstração são sintéticos;
- segredos, bancos locais, logs, Excel real e arquivos Power BI são ignorados;
- a demonstração não exige credenciais;
- nomes e endereços do ambiente original não fazem parte deste repositório.

## Limitações e evolução

A rota permanece como entrada manual; o cálculo automático cobre apenas a distância em linha reta. Evoluções naturais incluem histórico SCD, qualidade com Great Expectations, orquestração, alertas, RLS e uma tabela de rotas por modal.
