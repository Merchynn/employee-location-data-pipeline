# Arquitetura pública

```text
Excel local ou SharePoint
          ↓
Extração parametrizada
          ↓
Validação de contrato e normalização
          ↓
Cálculo geodésico residência → filial
          ↓
CSV de auditoria + staging
          ↓
SQLite para demonstração ou PostgreSQL em produção
          ↓
View analítica para Power BI
```

## Decisões

- **Manual first:** latitude, longitude e rota podem ser preenchidas pelo RH sem depender de API paga.
- **Distância reproduzível:** a distância em linha reta é calculada pelo algoritmo de Haversine.
- **Snapshot atômico:** o PostgreSQL recebe dados primeiro em staging; a tabela consumida pelo BI é substituída dentro de uma transação curta.
- **Contrato explícito:** nomes e tipos analíticos não dependem do arquivo corporativo original.
- **Execução concorrente protegida:** `filelock` impede duas cargas simultâneas na mesma máquina.
