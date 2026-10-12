# Estado do projeto

## Etapas concluídas

- ETAPA 1 OK — Inspeção concluída; repositório estava vazio, sem `AGENTS.md` local. Estrutura, tecnologias, escopo e decisões iniciais documentados em `README.md` e `pyproject.toml`.
- ETAPA 2 OK — Pacote, ponto de entrada, janela-base com navegação visual e diretório de dados local implementados. Com CustomTkinter 5.2.2 instalado, o processo de inicialização permaneceu ativo no loop da interface sem erro por 10 segundos.
- ETAPA 3 OK — Esquemas centralizados e persistência CSV com leitura, criação, atualização, exclusão, validação de IDs relacionados e substituição atômica. Seis testes passaram com arquivos temporários e dados fictícios.
- ETAPA 4 OK — Contas e categorias podem ser criadas, editadas, listadas e ativadas/desativadas pela interface. Verifiquei persistência ao reabrir a janela e confirmei que os IDs são preservados.
- ETAPA 5 OK — Receitas e despesas podem ser criadas, editadas e excluídas pela interface, com busca e filtros por período, tipo, categoria e conta. Verifiquei o ciclo e a persistência após reabrir o app com registros fictícios temporários.
- ETAPA 6 OK — Saldos por conta, transferências pessoais e pagamentos de cartão implementados. Onze testes passaram; fluxos de interface e reinício foram verificados com dados temporários.
- ETAPA 7 OK — Desejos, metas e orçamentos mensais implementados com CRUD, CSVs próprios e acompanhamento de progresso/gasto. A tela e a persistência foram verificadas com dados temporários; os 11 testes existentes e a compilação passaram.
- ETAPA 8 OK — Recorrências semanais, mensais e anuais com confirmação manual, ignorar ocorrência, pausa/reativação, tratamento de meses curtos e proteção contra duplicatas. Dezesseis testes passaram; compilação e montagem da tela com dados temporários foram verificadas.
- ETAPA 9 OK — Painel com seleção de período, totais de receitas/despesas/resultado, saldos no fim do período, despesas por categoria e gráficos mensais. Dezoito testes passaram; compilação e renderização do painel com dados temporários foram verificadas.
- ETAPA 10 OK — Previsão mensal por média simples dos seis últimos meses completos; exige histórico iniciado até a janela e atividade em pelo menos quatro dos seis meses. O mês atual fica fora; previsões são separadas do histórico e mostram período e limitações. Vinte e um testes passaram; compilação e montagem da tela com dados temporários foram verificadas.
- ETAPA 11 OK — Backup ZIP com manifesto SHA-256, restauração após validação em área temporária, exportação ZIP dos CSVs UTF-8 e tela de gerenciamento. Vinte e quatro testes passaram; montagem da interface e fluxos de backup/restauração/exportação com dados fictícios foram verificados. `data/` permanece excluído pelo `.gitignore`.
- ETAPA 12 OK — Revisão final de arquitetura, nomes, escopo e documentação. Vinte e quatro testes existentes passaram, compilação concluída e as dez áreas de navegação foram abertas em sequência com CSVs temporários vazios. Nenhuma funcionalidade empresarial foi encontrada. A pasta `data/` está em `.gitignore`; o diretório do projeto não contém metadados Git para inspeção adicional de arquivos rastreados.

## Estado final

- Roadmap concluído até a Etapa 12; sem próxima etapa pendente no roteiro atual.
- Recorrências criam lançamentos apenas após confirmação; ocorrências vencidas ficam listadas até confirmação ou ignorar. Fins de semana não são deslocados; datas de meses curtos são limitadas ao último dia do mês.
- As categorias de orçamento precisam ser de despesa. Cada categoria pode ter um único orçamento por mês. Ultrapassar o limite não bloqueia lançamentos.
- Os testes cobrem cálculos de saldo, persistência, migração de transações e calendário/idempotência de recorrências. O fluxo da etapa 7 também foi verificado com dados temporários, incluindo gasto por categoria/mês e persistência.
- O painel aceita intervalo inclusivo em `DD/MM/AAAA`. Totais e evolução incluem apenas receitas e despesas registradas nesse intervalo; transferências ficam fora. Saldos incluem saldos iniciais e todo o histórico até a data final. Projeções aparecem separadas na área própria.
- Previsões usam os seis meses-calendário encerrados antes do mês corrente, incluindo zero para meses sem lançamentos, e só aparecem com atividade em pelo menos quatro desses meses. A média projetada é uniforme para cada mês futuro, arredondada a centavos e limitada a 12 meses. Não estima sazonalidade, inflação ou mudanças futuras. Não foi adicionada Pandas: a média sobre agregados pequenos é simples e reproduzível com `Decimal` e a biblioteca padrão.
- Backup ZIP contém manifesto e hashes SHA-256; restauração valida todos os CSVs e relações numa pasta temporária antes de substituir os arquivos atuais. Exportação ZIP contém somente CSVs UTF-8 e não é um pacote restaurável. `data/` permanece ignorado pelo Git.
- Backup/exportação usam somente os CSVs reconhecidos pelo app. A exportação é um pacote ZIP com tabelas separadas; backup inclui versão e manifesto verificado e é o formato aceito para restauração.
- A qualidade dos relatórios e previsões depende de os lançamentos no app refletirem os movimentos reais; o app não verifica dados ausentes fora dos registros salvos.

## Decisões importantes

- Python >= 3.11 e CustomTkinter >= 5.2, < 6.
- Os dados ficam em `data/` dentro do projeto durante o desenvolvimento; `data/` está no `.gitignore`.
- Nenhum lançamento fictício ou dado pessoal é criado.
- Os CSVs usam UTF-8, delimitador vírgula, datas ISO `YYYY-MM-DD` e valores monetários `Decimal` normalizados como texto.
- Contas e categorias relacionadas a lançamentos não podem ser excluídas; podem ser desativadas para preservar o histórico.
- Valores informados na interface usam no máximo duas casas decimais; o CSV mantém o valor como decimal sem formatação de moeda.
- Transferências ficam em `transfers.csv`; não são receitas nem despesas. Cartão de crédito é exibido como fatura devida e não pode ser conta de origem de transferência.
- O esquema anterior de `accounts.csv` é migrado com saldo inicial zero, mantendo os IDs e registros existentes.
- A fatura do cartão é o total devido registrado desde o saldo inicial; ciclo de fechamento, vencimento, juros, taxas e parcelamentos ainda não são modelados.

## Execução

Instale com `python -m pip install -e .` em ambiente virtual e execute `finance-app` (ou `python -m finance_app`). Requer Python 3.11+ e ambiente gráfico. A dependência CustomTkinter 5.2.2 foi instalada no ambiente de execução usado para validar a inicialização.
