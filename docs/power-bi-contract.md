# Contrato para Power BI

A view `analytics.vw_employee_commute` é a interface recomendada para o modelo semântico.

## Dimensões

- funcionário;
- filial;
- departamento e centro de custo;
- município e UF;
- modal de transporte.

## Métricas sugeridas

- quantidade de funcionários por filial;
- distância média e mediana;
- tempo declarado médio;
- participação de cada modal;
- pessoas sem coordenadas;
- diferença entre distância de rota informada e distância geodésica;
- distribuição por município e departamento.

Dados de funcionários são sensíveis. Em produção, aplique RLS, controle de acesso, política de retenção e mascaramento quando necessário.
