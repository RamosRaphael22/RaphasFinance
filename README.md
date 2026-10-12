# Organizador financeiro pessoal

Aplicativo desktop pessoal em Python, com interface CustomTkinter e armazenamento local em CSV. O escopo é individual: receitas, despesas, contas e organização de objetivos pessoais. Não inclui recursos empresariais.

## Requisitos e execução

- Python 3.11 ou superior.
- Windows, macOS ou Linux com ambiente gráfico disponível.

Na raiz do projeto, crie e ative um ambiente virtual e instale o pacote:

```bash
python -m venv .venv
```

No Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e .
finance-app
```

Em macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -e .
finance-app
```

Também é possível iniciar com `python -m finance_app` após instalar o pacote.

## Dados

Os arquivos locais são gravados em `data/` na raiz do projeto. Esse diretório está excluído do Git. A aplicação não cria lançamentos de exemplo.

### Arquivos CSV

Todos usam UTF-8, delimitador vírgula e cabeçalho na primeira linha. Datas usam `YYYY-MM-DD`; valores de lançamento são decimais em texto sem símbolo monetário. Campos booleanos usam `true` ou `false`.

- `accounts.csv`: `name`, `kind` (`cash`, `bank`, `savings`, `credit_card`), `active`, `id`, `opening_balance`.
- `categories.csv`: `name`, `kind` (`income`, `expense`), `active`, `id`.
- `transactions.csv`: `kind`, `description`, `amount`, `date`, `category_id`, `account_id`, `notes`, `id`, `recurrence_id`, `recurrence_date`. Os dois últimos campos ficam vazios em lançamentos comuns.
- `transfers.csv`: `source_account_id`, `destination_account_id`, `amount`, `date`, `notes`, `id`.
- `wishes.csv`: `name`, `estimated_amount`, `saved_amount`, `priority`, `status`, `target_date`, `id`.
- `goals.csv`: `name`, `target_amount`, `saved_amount`, `deadline`, `priority`, `status`, `id`.
- `budgets.csv`: `category_id`, `period` (`AAAA-MM`), `limit_amount`, `id`.
- `recurrence_rules.csv`: `name`, `kind`, `description`, `amount`, `category_id`, `account_id`, `frequency`, `interval`, `start_date`, `end_date`, `active`, `id`.
- `recurrence_occurrences.csv`: `rule_id`, `occurrence_date`, `status` (`confirmed`, `skipped`), `id`.

Datas opcionais sem valor são armazenadas como campo vazio. Os demais campos seguem os tipos e valores permitidos por cada cadastro; IDs são as chaves das relações entre arquivos.

Arquivos ausentes são inicializados somente com o cabeçalho. Antes de alterar um CSV, a aplicação valida seus registros e grava o novo conteúdo em arquivo temporário no mesmo diretório para então substituí-lo. Contas e categorias com lançamentos associados não podem ser excluídas; desativá-las preserva as relações.

Na tela **Lançamentos**, informe valor positivo com até duas casas decimais e data em `DD/MM/AAAA`. A tela oferece busca por descrição ou observação e filtros por intervalo, tipo, categoria e conta. Excluir um lançamento pede confirmação; editar um registro mantém seu identificador.

### Saldos e cartões

O saldo inicial de uma conta comum representa o dinheiro existente no início do uso do app; o de um cartão representa a dívida já em aberto. Quando omitido, começa em zero. Para dinheiro, conta bancária e poupança, o saldo atual é saldo inicial + receitas − despesas + transferências recebidas − transferências enviadas. Para cartão, a fatura em aberto é dívida inicial + despesas no cartão − créditos/estornos − pagamentos recebidos.

Pagar a fatura é uma transferência da conta usada para pagamento para a conta do cartão. A compra continua sendo a despesa e o pagamento não cria outra despesa. Cartões não podem ser origem de transferência nesta versão. O arquivo de contas antigo, sem `opening_balance`, recebe saldo inicial zero na primeira abertura; os registros e IDs existentes são preservados.

O cálculo do cartão representa a dívida total registrada desde o saldo inicial. Ainda não há ciclo de fechamento, vencimento, juros, taxas ou parcelamento de fatura.

### Desejos, metas e orçamentos

Na área **Planejamento**, use as abas internas para gerenciar desejos, metas e orçamentos. Cada desejo ou meta pode ser criado, editado, acompanhado e excluído. O progresso compara o valor reservado ou acumulado com o valor estimado ou desejado; prioridade, situação e prazo opcional também ficam salvos. Nos orçamentos, defina um limite mensal para cada categoria de despesa e acompanhe o gasto realizado e o valor disponível (ou excedido). Os limites são informativos: despesas continuam sendo registradas mesmo quando ultrapassam o orçamento.

### Recorrências

As regras podem ser semanais, mensais ou anuais, com intervalo e datas inicial/final opcionais. O aplicativo não cria lançamentos automaticamente: cada ocorrência vencida precisa ser confirmada ou ignorada pela pessoa. Regras não alteram fins de semana. Em meses curtos, uma data como dia 31 cai no último dia daquele mês, voltando ao dia 31 quando o mês seguinte o tiver. Ocorrências vencidas continuam pendentes até confirmação ou ignorar. O par regra/data fica associado ao lançamento confirmado e também no histórico de ocorrências, protegendo contra duplicação após reprocessar ou reiniciar. O cabeçalho antigo de `transactions.csv` é migrado com os campos de recorrência vazios.

### Painel e relatórios

A **Visão geral** permite informar as datas inicial e final inclusivas em `DD/MM/AAAA`. Mostra receitas, despesas e resultado do intervalo, saldos de conta ao fim da data final, despesas por categoria e evolução mensal. Transferências não são receitas nem despesas. Saldos incluem o saldo inicial e todo o histórico disponível até a data final; valores mensais e por categoria incluem somente lançamentos do intervalo. Os gráficos mostram valores realizados, sem estimativas ou previsões.

### Previsões básicas

A seção **Previsões** oferece estimativas para 3, 6 ou 12 meses com base na média simples das receitas e despesas de seis meses-calendário encerrados antes do mês atual. O aplicativo só apresenta estimativas quando há lançamentos desde o primeiro mês da janela e atividade em ao menos quatro dos seis meses. Meses sem lançamentos contam como zero; o mês atual não entra no cálculo. A estimativa depende de registros completos no app, algo que o programa não consegue inferir. O método não modela sazonalidade, inflação ou eventos futuros, e não constitui aconselhamento financeiro. Valores projetados são identificados como estimativas e ficam separados dos realizados. O cálculo usa `Decimal` e a biblioteca padrão; Pandas não é necessário para esta média curta.

### Backup, restauração e exportação

Em **Dados e backup**, **Criar backup** gera um ZIP com todos os CSVs e um manifesto com versão, data e somas SHA-256. **Restaurar backup** aceita esse formato, confere os arquivos, cabeçalhos, registros e relações numa área temporária antes de substituir os CSVs atuais. Se a validação falhar, os arquivos atuais não são alterados. A tela pede confirmação antes de iniciar a substituição. **Exportar dados CSV** cria um ZIP com os arquivos individuais em UTF-8, que podem ser extraídos e abertos em planilhas; valores continuam como decimais normalizados e datas como `YYYY-MM-DD`. A exportação não é um backup restaurável pelo app. O diretório `data/` continua excluído do Git.

## Decisões iniciais

- Interface em português do Brasil com CustomTkinter.
- Separação entre interface, domínio, persistência CSV e análises.
- Identificadores estáveis, datas ISO e valores monetários com `Decimal`.
- CSV UTF-8 com delimitador vírgula; cabeçalhos e formatação serão centralizados na camada de armazenamento.
- Previsões básicas usam a média recente quando há histórico suficiente; valores projetados ficam identificados e separados dos realizados.
