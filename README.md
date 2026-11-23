# SinalVital

O **SinalVital** é um protótipo acadêmico de organização do atendimento em saúde, desenvolvido na disciplina de Engenharia de Software. Ele conecta o relato de sintomas do paciente, a classificação inicial, o encaminhamento ao médico e o registro da consulta em um histórico de acompanhamento.

O projeto possui três experiências: **paciente**, **médico** e **administração**. As funcionalidades descritas abaixo correspondem ao que está implementado nesta versão.

> Ambiente de demonstração: utilize dados fictícios. A classificação inicial serve para apresentar o fluxo do sistema; não constitui diagnóstico nem substitui avaliação médica.

## Conheça as funcionalidades

- [Perfis e entrada no sistema](#perfis-e-entrada-no-sistema)
- [Funcionalidades do paciente](#funcionalidades-do-paciente)
- [Organização e encaminhamento do atendimento](#organização-e-encaminhamento-do-atendimento)
- [Painel médico](#painel-médico)
- [Painel administrativo](#painel-administrativo)
- [Experiência de uso e acessibilidade](#experiência-de-uso-e-acessibilidade)
- [Roteiro para apresentação](#roteiro-para-apresentação)
- [Como abrir a demonstração](#como-abrir-a-demonstração)
- [Escopo e limitações atuais](#escopo-e-limitações-atuais)
- [Qualidade e documentação complementar](#qualidade-e-documentação-complementar)

## Perfis e entrada no sistema

A tela de entrada apresenta dois cartões de seleção. Cada um explica o que aquele perfil pode fazer. Ao trocar de perfil, a orientação de identificação e o botão de entrada acompanham a escolha.

| Perfil | Como entrar | O que encontra |
| --- | --- | --- |
| Paciente | Número do cadastro ou e-mail cadastrado | Relato de sintomas, agendamento, fila de espera, histórico e consulta dos próprios dados. |
| Médico | Número do cadastro profissional, com o médico ativo | Fila dos pacientes vinculados ao profissional, prontuário e registro de consultas. |
| Administração | Página separada e senha administrativa configurada | Cadastro e listagem de médicos, consulta de pacientes e acompanhamento dos vínculos de atendimento. |

O cadastro de paciente está disponível para visitantes. Depois da entrada, o paciente encontra **Meus dados** em lugar da opção de novo cadastro. O médico é direcionado ao painel clínico.

A identificação de paciente e médico vale para a aba utilizada. **Sair / Trocar Perfil** encerra essa identificação e retorna à tela de entrada. A administração possui entrada e saída próprias; recarregar a página exige informar sua senha novamente.

## Funcionalidades do paciente

### Cadastro

O paciente informa **nome completo** e **e-mail**. Pode acrescentar **idade** e **condição crônica**, utilizadas no contexto do atendimento e nas regras de prioridade de agendamentos.

O sistema valida o preenchimento e impede cadastros com e-mail já utilizado. Após salvar, apresenta o número do paciente. Esse número ou o e-mail pode ser utilizado para entrar no perfil de paciente.

### Página inicial personalizada

Após a entrada, a página inicial recebe o paciente pelo nome:

**“Olá, [nome]! Como você está hoje?”**

O destaque principal permite relatar sintomas. Os cartões de acesso levam a **Meus dados**, **Relatar sintomas**, **Agendar consulta**, **Meu histórico** e **Fila de espera**.

As ações do painel médico não aparecem como opções do paciente.

### Meus dados

Apresenta as informações do cadastro vinculado ao perfil identificado:

- Número do paciente.
- Nome completo e e-mail.
- Idade e condição crônica, quando informadas.

Campos opcionais ausentes são apresentados como não informados. Esta tela permite **consultar os dados**, sem edição nesta versão.

### Relato de sintomas e classificação inicial

O paciente descreve os sintomas com suas próprias palavras, incluindo quando começaram. Pode usar atalhos como **Dor no peito**, **Falta de ar**, **Dor de cabeça**, **Febre** e **Tontura** para acrescentar termos ao relato.

O relato aceita de **5 a 5.000 caracteres** e fica vinculado ao paciente identificado. Após o envio, o resultado apresenta:

- Nível de urgência, com cor e descrição textual.
- Justificativa da classificação.
- Especialidade recomendada.
- Prioridade, número e data do registro.
- Médico alocado e pontuação da fila, quando a inclusão na fila é concluída.

A tela tenta incluir automaticamente o paciente na fila de urgência após salvar a triagem. Se essa inclusão falhar, o relato salvo continua disponível no histórico; o registro de triagem e a entrada na fila são operações distintas.

O resultado oferece os atalhos **Consultar meu histórico** e **Ir para Agendamento**. Quando aplicável, também apresenta orientação de atendimento imediato. Não oferece acesso ao painel médico.

### Agendamento de consultas

O agendamento permite escolher **especialidade**, **profissional**, **dia disponível** e informar o **motivo da consulta**. Também permite indicar gestação para o cálculo de prioridade.

O fluxo funciona assim:

1. A especialidade selecionada determina quais profissionais disponíveis serão apresentados.
2. A escolha do profissional mostra os dias de atendimento e as vagas restantes.
3. Dias lotados ficam indisponíveis para seleção.
4. O paciente escolhe uma data, informa o motivo e confirma o agendamento.
5. O sistema apresenta um comprovante com os dados da consulta e a prioridade calculada.

Quando o paciente vem do resultado de uma triagem, o agendamento pode aproveitar o relato, a especialidade e o registro já existente. A página também mostra **Meus agendamentos**, com data, profissional, situação e posição na fila de consultas agendadas.

Se a avaliação identificar emergência ou urgência alta, a tela apresenta uma recomendação e permite escolher entre **entrar na fila de urgência** e **manter o agendamento**. A entrada na urgência cria um vínculo nessa fila; não cancela automaticamente a consulta agendada.

### Fila de espera

O paciente acompanha seus registros na fila de urgência, com informações como:

- Posição na fila e situação do atendimento.
- Urgência e pontuação de prioridade.
- Especialidade e médico vinculado, quando disponível.
- Motivo do encaminhamento e tempo de espera.

A lista permite busca por nome e filtro de situação. No perfil de paciente, a interface exibe somente seus registros e preserva a posição correspondente na fila original.

A página consulta a fila automaticamente a cada **30 segundos** e também oferece **Atualizar**. A posição pode mudar conforme as prioridades e a espera dos demais atendimentos; ela não representa um horário garantido de consulta.

### Histórico de saúde

O histórico reúne **triagens**, **consultas** e outros eventos de atendimento registrados para o paciente. A interface organiza os registros do mais recente para o mais antigo e permite filtrar pelo tipo.

Conforme o registro, apresenta o relato, a classificação de urgência, a especialidade, a justificativa e as informações da consulta, como médico, diagnóstico e conduta.

Uma nova triagem ou consulta passa a compor esse acompanhamento. O paciente pode consultar novamente o histórico para carregar registros recentes.

## Organização e encaminhamento do atendimento

### Duas filas com critérios diferentes

| Fila | Como a prioridade funciona | Como o profissional é definido |
| --- | --- | --- |
| Urgência | Considera o nível de urgência e acrescenta um bônus pelo tempo de espera, até um limite. A pontuação é recalculada ao consultar a fila. | Busca um médico ativo da especialidade recomendada, que atenda urgência e tenha capacidade disponível. |
| Consultas agendadas | Considera urgência, idade, gestação e condição crônica. A prioridade calculada não cresce com o tempo de espera. | O paciente escolhe um profissional que realize agendamentos e uma data com vagas. |

Na fila de urgência, uma pontuação maior corresponde a maior prioridade. A distribuição entre profissionais compatíveis favorece o médico com **menor número de pacientes vinculados**; em empate, utiliza o menor número de cadastro.

A **capacidade simultânea** é o limite de pacientes vinculados ao médico na fila de urgência, aguardando ou em atendimento. Por exemplo, um médico com capacidade 2 pode receber até dois vínculos ativos nessa fila. Esse limite é diferente da quantidade de consultas que ele oferece por dia no agendamento.

Quando não há profissional disponível, o sistema informa **“Aguardando vaga na especialidade”**. Novas consultas à fila tentam alocar os pacientes sem médico quando houver capacidade.

### Classificação dos sintomas

A demonstração funciona por padrão com **regras locais de palavras-chave**, sem depender de um serviço externo. O sistema retorna urgência, especialidade e justificativa para apoiar a apresentação do encaminhamento.

Também existe integração opcional com **Claude**, habilitada pela configuração do ambiente. Nesse modo, o relato é enviado ao serviço externo para classificação. Se a chave estiver ausente, ocorrer falha de comunicação ou a resposta for inválida, o sistema recorre ao classificador local. A integração externa depende de configuração e de crédito no serviço.

## Painel médico

O médico identificado encontra os pacientes vinculados ao seu cadastro, podendo alternar entre **urgência** e **consultas agendadas**. O painel organiza o trabalho em dois blocos: **selecionar o paciente** e **realizar o atendimento**.

### Fila de pacientes

A fila apresenta nome, identificação, prioridade, especialidade e motivo do atendimento, conforme os dados disponíveis. O botão **Atualizar fila** consulta novamente a lista.

Ao clicar em **Selecionar paciente**, o painel preenche a identificação e direciona o foco para o atendimento escolhido. O formulário clínico fica disponível para um paciente com vínculo válido.

### Prontuário evolutivo

Antes de preencher a consulta, o médico pode conferir:

- Nome e identificação do paciente.
- Idade e condições crônicas informadas.
- Especialidade e profissional alocado.
- Motivo do atendimento ou relato de sintomas.
- Urgência e justificativa da classificação.
- Histórico de triagens e consultas, inclusive registros de outros médicos.

O histórico fica em um bloco recolhível e pode ser filtrado por consultas ou triagens. Isso mantém o contexto clínico disponível sem ocupar permanentemente todo o espaço de trabalho.

### Registro e conclusão da consulta

O registro contém **anamnese e observações iniciais**, opcionais, além de **diagnóstico** e **conduta**, obrigatórios.

Ao escolher **Salvar e concluir atendimento**, o sistema valida os dados e a compatibilidade do vínculo com o médico, salva a consulta, acrescenta o evento ao histórico e conclui o vínculo ativo correspondente. O painel apresenta a confirmação e atualiza a fila.

**Limpar registro** permite recomeçar o preenchimento e a seleção. Essa ação não exclui consultas já salvas. Em caso de erro no envio, o painel apresenta a mensagem e mantém o conteúdo preenchido para correção.

## Painel administrativo

A administração é uma área separada, sem atalho nos menus públicos. O acesso depende de uma **senha administrativa configurada**, verificada pelo servidor em suas operações.

O painel possui duas abas: **Médicos** e **Pacientes e atendimentos**.

### Cadastro e listagem de médicos

O cadastro organiza as informações em identificação do profissional e configuração do atendimento:

| Informação | Finalidade |
| --- | --- |
| Nome e especialidade | Identificar o profissional e sua área de atendimento. |
| Modalidade | Definir atuação em urgência, consultas agendadas ou ambas. |
| Capacidade simultânea | Limitar vínculos ativos na fila de urgência. |
| Dias de atendimento | Informar em quais dias o profissional recebe consultas agendadas. |
| Limite diário | Definir quantas consultas podem ser agendadas para cada dia de atendimento. |
| Ativo | Indicar se o profissional está disponível para os fluxos que exigem médico ativo. |

Dias e limite diário são exigidos quando a modalidade inclui agendamento. O sistema valida os dados e impede repetição de nome e especialidade no cadastro administrativo.

Após o cadastro, o painel informa o número do médico. Um novo profissional ativo já pode utilizar esse número para entrar no painel médico. A lista permite conferir modalidade, capacidade e agenda, com atualização manual.

### Consulta de pacientes e atendimentos

A administração pode procurar pacientes pelo nome e combinar filtros de **tipo de atendimento** e **etapa**. Cada paciente possui um cartão expansível, pois uma mesma pessoa pode ter vários registros.

Dentro do cartão, cada vínculo informa **tipo**, **etapa**, **médico**, **especialidade do médico** e **data**. Relatos clínicos, diagnóstico e conduta não são exibidos nessa consulta administrativa.

Os tipos disponíveis são **Todos os tipos**, **Urgência**, **Agendamento**, **Consulta registrada** e **Triagem**. As etapas mostradas acompanham o tipo escolhido:

| Tipo selecionado | Etapas específicas disponíveis |
| --- | --- |
| Todos os tipos | Sem atendimento, Triagem realizada, Aguardando, Agendado, Atendido e Cancelado. |
| Urgência | Aguardando, Atendido e Cancelado. |
| Agendamento | Agendado, Atendido e Cancelado. |
| Consulta registrada | Atendido. |
| Triagem | Triagem realizada. |

Todos permitem a opção **Todas as etapas**. Etapas incompatíveis ficam ocultas; se a escolha anterior deixar de ser compatível, o filtro volta para Todas as etapas antes de consultar.

Tipo e etapa são aplicados ao selecionar; **Buscar pacientes** aplica também o nome informado. Os resultados exibem apenas os vínculos correspondentes à combinação escolhida. Para consultar todos os registros, selecione Todos os tipos e Todas as etapas.

Uma urgência concluída e a consulta registrada são vínculos distintos: ambos podem aparecer no histórico administrativo do mesmo paciente.

### Atualização automática

Na aba de pacientes, o painel consulta alterações automaticamente a cada **10 segundos após o término da consulta anterior**, preservando filtros aplicados e cartões abertos. O aviso mostra o horário da última atualização.

As consultas pausam ao sair da administração, trocar para a aba de médicos ou ocultar a página. Ao voltar à página visível, a atualização é retomada. Se houver falha temporária, os últimos dados continuam exibidos e o painel tenta novamente.

## Experiência de uso e acessibilidade

As telas compartilham a identidade visual do SinalVital, com azul-marinho, vermelho de destaque, superfícies claras e espaçamento entre informações e ações.

- **Layout responsivo:** formulários e cartões se reorganizam para celular; os painéis priorizam uma coluna quando necessário.
- **Controles de leitura:** A− e A+ ajustam o tamanho dos textos; o alto contraste oferece outra forma de leitura. Essas preferências são lembradas pelo navegador.
- **Navegação por teclado:** campos, botões, seleção de perfil e abas administrativas mantêm controles acessíveis e indicação de foco.
- **Informação além da cor:** classificações e situações possuem descrição textual.
- **Retorno das operações:** carregamento, confirmação, falha e ausência de resultados possuem mensagens próprias.
- **Ações separadas:** botões mantêm espaçamento e podem quebrar de linha em telas menores.
- **Identificação do paciente:** nos formulários de sintomas, histórico e agendamento, o perfil identificado preenche o número do paciente e o mantém somente para leitura.

## Roteiro para apresentação

### Jornada de urgência

1. Entre como paciente com um cadastro fictício existente ou crie um novo e faça a entrada.
2. Confira a saudação e as informações em Meus dados.
3. Relate sintomas e apresente a classificação, a especialidade e o encaminhamento.
4. Abra a fila de espera para mostrar posição, situação e profissional vinculado.
5. Troque para o perfil do médico ao qual o paciente foi alocado.
6. Selecione o paciente, consulte o prontuário e registre diagnóstico e conduta fictícios.
7. Volte ao perfil do paciente e consulte o histórico para mostrar a consulta registrada.

### Jornada de consulta agendada

1. Entre como paciente e abra Agendar consulta.
2. Escolha uma especialidade com profissional disponível, selecione o médico e uma data com vagas.
3. Informe o motivo e confirme para apresentar o comprovante e a lista de agendamentos.
4. Entre como o médico escolhido, alterne para a fila de consultas agendadas e selecione o paciente.
5. Registre a consulta e confira a conclusão do vínculo e o histórico.

### Acompanhamento administrativo

1. Abra a página administrativa e entre com a senha configurada.
2. Apresente os médicos cadastrados e o formulário de novo profissional.
3. Abra Pacientes e atendimentos e combine os filtros de tipo e etapa.
4. Expanda um paciente para mostrar seus vínculos e a especialidade do médico.
5. Conclua um atendimento em outra aba, pelo perfil médico, e aguarde o ciclo de atualização da administração para observar a mudança.

## Como abrir a demonstração

Se o projeto já estiver instalado, execute na pasta do repositório:

```powershell
.\venv\Scripts\python.exe -m app.seed
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

O primeiro comando prepara os cadastros fictícios de demonstração. O segundo inicia o sistema. Com o servidor ativo, os endereços são:

| Tela | Endereço local |
| --- | --- |
| Início | [Abrir SinalVital](http://127.0.0.1:8000/) |
| Seleção de perfil | [Entrar](http://127.0.0.1:8000/pages/login.html) |
| Relato de sintomas | [Relatar sintomas](http://127.0.0.1:8000/pages/triagem.html) |
| Agendamento | [Agendar consulta](http://127.0.0.1:8000/pages/agendamento.html) |
| Histórico | [Meu histórico](http://127.0.0.1:8000/pages/historico.html) |
| Fila de urgência | [Fila de espera](http://127.0.0.1:8000/pages/fila.html) |
| Dados do paciente | [Meus dados](http://127.0.0.1:8000/pages/meus-dados.html) |
| Painel médico | [Atendimento médico](http://127.0.0.1:8000/pages/medico.html) |
| Administração | [Painel administrativo](http://127.0.0.1:8000/pages/admin.html) |

O cadastro de paciente pode ser aberto pela tela de entrada. As telas de atendimento exigem a identificação do perfil correspondente.

Para a primeira instalação, são necessários **Python 3.12** e as dependências do projeto:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```

Copie o arquivo de exemplo **somente se ainda não existir um `.env`**, preservando configurações locais. Para a demonstração sem serviço externo, mantenha `MODO_IA=mock`. Para habilitar a administração, defina sua senha em `ADMIN_PASSWORD` e reinicie o servidor. Não publique o `.env`.

Os cadastros de demonstração incluem os pacientes Raimundo Nonato e Juscélio e médicos para urgência e consultas agendadas. Pacientes podem entrar com `raimundo@example.com` ou `juscelio@example.com`. Consulte os números dos médicos na administração; não presuma que os números sejam iguais em bancos já utilizados.

Se um banco antigo apresentar incompatibilidade na triagem, consulte o comando de atualização disponível no projeto, `python -m scripts.atualizar_banco`, que realiza backup antes das alterações suportadas. Essa atualização não substitui uma migração geral para qualquer versão do banco.

## Escopo e limitações atuais

- **Identificação de demonstração:** pacientes e médicos entram sem senha. A separação de telas e os filtros por perfil ocorrem na interface e não constituem autorização completa para acesso direto aos dados do servidor.
- **Administração separada:** utiliza senha compartilhada verificada pelo servidor. Ainda não há contas administrativas individuais ou gestão de permissões.
- **Cadastro administrativo:** permite criar e listar médicos; não oferece telas de edição, exclusão ou desativação de um cadastro existente.
- **Dados do paciente:** são consultáveis, mas ainda não podem ser editados pela tela Meus dados.
- **Agendamento por dia:** a escolha é de uma data com capacidade disponível; não há seleção de horário específico nem previsão garantida para o atendimento.
- **Situações exibidas:** a presença de uma situação em filtros, como Cancelado, não significa que exista uma ação para cancelar pela interface. Esta versão não oferece cancelamento ou reagendamento pelo paciente.
- **Múltiplos vínculos:** uma pessoa pode possuir triagens, urgências, agendamentos e consultas distintos. O sistema não resume todo o histórico em uma única situação do paciente.

## Qualidade e documentação complementar

O projeto utiliza testes automatizados para verificar cadastros, classificação, prioridades, distribuição de médicos, agendamentos, consultas, histórico, perfis e administração. Os comportamentos de JavaScript também são executados pela suíte de testes, e funcionalidades desenvolvidas com TDD possuem cenários definidos antes da implementação.

O GitHub Actions instala as dependências e executa os testes em **pushes para `dev` e `main`** e em **pull requests destinados a essas branches**. Os resultados ficam nos checks do PR e na aba Actions.

Para executar a validação local, é necessário Node.js disponível, além do ambiente Python:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

Documentação complementar:

- [Planejamento das iterações e documentação da equipe](https://github.com/ES2-UFPI/SinalVital/wiki/Plano-de-Itera%C3%A7%C3%B5es).
- [Configuração e operações administrativas](docs/painel-administrativo.md).
- [Identificação e separação de perfis](docs/login-perfis.md).
- [Documentação interativa da API, com o servidor ativo](http://127.0.0.1:8000/docs).
