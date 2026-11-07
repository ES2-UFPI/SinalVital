# SinalVital

## Matching de médicos — [008-02] (#41)

`MotorPriorizacao.escolher_medico(especialidade, medicos, carga_atual)`, em
`app/domain/queue/motor_priorizacao.py`, seleciona somente médicos ativos da
especialidade indicada, com carga inferior à capacidade simultânea. A menor
carga absoluta vence; em caso de empate, vence o menor ID, independentemente
da ordem da lista. A especialidade deve usar o mesmo identificador do modelo,
como `cardiologia`, `oftalmologia` ou `clinica_geral`.

`carga_atual` é um mapa `{id_medico: quantidade_atual}` de contagens não negativas.
IDs ausentes contam como zero; entradas referentes a outros médicos são ignoradas.
O método retorna o próprio médico selecionado ou `None` quando não há vaga.
Na integração dos endpoints da fila (#44), `None` deve ser apresentado como
`AGUARDANDO_VAGA_NA_ESPECIALIDADE`, cujo valor é `"Aguardando vaga na especialidade"`.

```python
from app.database.models import Medico
from app.domain.queue.motor_priorizacao import (
    MotorPriorizacao, AGUARDANDO_VAGA_NA_ESPECIALIDADE,
)

medicos = [
    Medico(id=1, nome="Helena", especialidade="cardiologia",
           capacidade_simultanea=2, ativo=True),
]
medico = MotorPriorizacao.escolher_medico("cardiologia", medicos, {1: 1})
estado = medico.nome if medico is not None else AGUARDANDO_VAGA_NA_ESPECIALIDADE
```

Esta operação não consulta o banco, modifica as cargas nem reserva vagas. A
camada que aloca o atendimento deve obter cargas atuais e controlar concorrência.
Nenhuma rota nova foi adicionada nesta issue. Os 15 cenários TDD estão em
`tests/unit/test_escolher_medico.py`, incluindo uso com o modelo SQLAlchemy,
capacidade atingida/excedida, menor carga, empate, inativos e ausência de vaga.
Para executá-los:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/test_escolher_medico.py -q
```

O workflow existente os executa junto à suíte nos PRs destinados à `dev`.

## Médicos — [008-01] (#40)

O modelo `Medico` está em `app/database/models/medico.py`. A tabela `medicos`
contém `id`, `nome`, `especialidade`, `capacidade_simultanea` e `ativo`.
Por padrão, a capacidade é 1 e o médico está ativo. A capacidade deve ser positiva.
A tabela é criada na inicialização da API ou na execução do seed; não é preciso
apagar o banco existente para acrescentá-la.

Para popular os pacientes e os três médicos fictícios de demonstração:

```powershell
.\venv\Scripts\python.exe -m app.seed
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

O seed inclui cardiologia, oftalmologia e clínica geral, com nomes fictícios e
capacidades de 2, 1 e 3 atendimentos simultâneos, respectivamente. Todos começam
ativos. A repetição do comando identifica cada médico de demonstração por nome
e especialidade, sem duplicar nem sobrescrever sua capacidade ou estado ativo.
Se nome ou especialidade forem alterados, o registro original da demonstração
será inserido novamente. Essa identificação é específica do seed, não uma regra
de unicidade para todos os médicos. Os pacientes continuam sendo incluídos.

Abra http://127.0.0.1:8000/medicos no navegador para consultar o JSON, ou use
`GET /medicos` em http://127.0.0.1:8000/docs. A resposta é `200` com uma lista
ordenada por nome (ID como desempate); sem médicos cadastrados, retorna `[]`.
Cada item contém `id`, `nome`, `especialidade`, `capacidade_simultanea` e `ativo`.
A listagem inclui tanto médicos ativos quanto inativos.

```json
{
  "id": 1,
  "nome": "Helena",
  "especialidade": "cardiologia",
  "capacidade_simultanea": 2,
  "ativo": true
}
```

O desenvolvimento seguiu TDD: cinco testes foram executados e falharam antes
da implementação; após a implementação, a suíte completa passou. Os testes em
`tests/integration/test_medicos.py` cobrem listagem vazia, ordenação e resposta,
persistência, capacidade positiva, valores padrão, médicos inativos, seed
repetível e preservação do seed de pacientes. Os testes foram ajustados em um
novo ciclo Red/Green após a confirmação da descrição completa da issue.
São descobertos pelo `python -m pytest -q` e pelo workflow existente em PRs
destinados à `dev`. Esta entrega não inclui cadastro HTTP ou tela de médicos.

Se você executou a primeira versão local da #40 (com CRM), a tabela `medicos`
antiga não é atualizada pelo `create_all`. Para testar sem alterar os dados
existentes, use `DATABASE_URL=sqlite:///./sinalvital-medicos-v2.db` no `.env`
antes de executar o seed e reinicie a API. Nenhum banco anterior é apagado.

Projeto da disciplina de Engenharia de Software. A aplicação principal está em
`app/`; `tutorial-demo/` é uma demonstração independente dos tutoriais.

## Executar no Windows (PowerShell)

Requer Python 3.10 ou superior. Execute os comandos na raiz do repositório:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -m app.seed
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

A API cria as tabelas ao iniciar. O seed também cria as tabelas e insere os
pacientes fictícios Raimundo Nonato e Juscélio. Pode ser executado novamente:
cadastros com os mesmos e-mails são preservados, sem duplicação ou atualização.
Os dados de demonstração são fictícios; a idade e a condição de Juscélio ficam
sem preenchimento. O banco padrão é `sinalvital.db` na pasta de execução;
para usar outro banco, configure `DATABASE_URL` no `.env`.

Abra http://127.0.0.1:8000/docs para testar o cadastro sem autenticação.

## Cadastro de pacientes — issue #11

`POST /pacientes` recebe, por exemplo:

```json
{
  "nome": "Ana Silva",
  "email": "ana@example.com",
  "idade": 65,
  "condicao_cronica": "Hipertensão"
}
```

Nome e e-mail são obrigatórios. Idade e condição crônica são opcionais.
Nome aceita até 120 caracteres, e-mail válido até 120, idade não negativa
e condição crônica até 200. Espaços nas extremidades são removidos.

- `201`: paciente criado; retorna `id`, os dados cadastrados e `criado_em`.
- `409`: e-mail já cadastrado.
- `422`: dados inválidos ou campos obrigatórios ausentes.

## Classificação de sintomas — issue #15 ([005-02])

`app/domain/triagem/strategies/classificador.py` implementa Strategy com a classe abstrata `Classificador`
e a implementação inicial `MockClassificador`. A `ClassificadorFactory` escolhe
a implementação lendo `MODO_IA` a cada chamada de `criar()`:

- Ausente ou `mock`: usa o mock.
- `real`: também usa o mock enquanto a implementação real não existir.
- Outro valor (inclusive vazio): gera `ValueError` para indicar configuração inválida.

O `.env` é carregado sem sobrescrever as variáveis do ambiente. O modo aceita
maiúsculas e espaços nas extremidades. Não são necessárias chave de API ou rede.

```python
from app.ia_service import ClassificadorFactory

classificador = ClassificadorFactory.criar()
resultado = classificador.classificar("dor no peito e falta de ar")
# {"urgencia": "emergencia", "especialidade": "cardiologia",
#  "justificativa": "Classificado como emergência por mencionar: dor no peito, falta de ar. "
#                   "Especialidade sugerida: cardiologia (termos: ...)"}
```

O mock delega para `app/triagem/regras.py` (issue #14): ignora caixa e acentos,
desconsidera termos negados ("sem dor no peito") e usa os níveis emergência, alta,
média e baixa (padrão). A estratégia `palavras_chave` da rota de triagem usa a mesma
busca de termos, mantendo as cores da dev. Retorna `urgencia`, `especialidade` e
`justificativa`; relatos vazios geram `ValueError`. É uma simulação didática.
A expansão das regras pertence à [005-03], e a exposição pelo endpoint
`POST /triagens` à [005-04]. Esta etapa não adiciona uma rota de classificação.

## Testes

Após a integração com a dev, `app/ia_service.py` mantém os imports anteriores
compatíveis. O cadastro e o histórico estão em `app/api/routes/pacientes.py`;
o ponto de entrada registra também a rota de triagem trazida pela dev,
`POST /pacientes/{paciente_id}/triagens`. A configuração SQLAlchemy é única
em `app/database/database.py`, reexportada por `app.database`.

Os contratos de classificação da dev (`TriageClassifierFactory`, cores e
prioridades) e da [005-02] (`ClassificadorFactory`, urgência e especialidade)
foram preservados. A rota de triagem usa o contrato de cores da dev.
O mock local continua disponível pelo exemplo acima.

Se já existir um banco criado pela versão anterior da tabela `triagens`,
`create_all` não altera suas colunas. Para testar a nova estrutura sem alterar
esse banco, configure `DATABASE_URL=sqlite:///./sinalvital-integrado.db` no `.env`
e execute o seed novamente. Migrações do banco existente precisam ser tratadas
separadamente.

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest -q
```

Os testes utilizam SQLite temporário, separado do banco da aplicação.
Cobrem cadastro, validação, duplicidade de e-mail e repetição do seed.

## Interface da Sprint 1 — issue #22

Com a API em execução, abra http://127.0.0.1:8000/.
O frontend é servido pelo próprio FastAPI, sem etapa de build ou dependências JavaScript.

- `frontend/index.html`: entrada e atalhos do paciente.
- `frontend/pages/`: cadastro, relato de sintomas e histórico.
- `frontend/assets/css/base.css`: tokens de cores, tipografia, componentes, responsividade e alto contraste compartilhados.
- `frontend/assets/js/app.js`: controles de leitura e integração com a API.

As páginas compartilham cabeçalho, navegação, foco visível e controles A−/A+
(18 a 24 px de tamanho base). O contraste e o tamanho são lembrados no navegador.
O número do paciente é mantido apenas na aba; dados clínicos não são gravados no
armazenamento do navegador. Também é possível informar `?paciente=ID` nas páginas
de triagem e histórico. Use o número devolvido pelo cadastro, sem presumir IDs do seed.

Roteiro de apresentação: cadastrar um paciente fictício, guardar o número,
continuar para a triagem, selecionar um sintoma e enviar. O resultado mostra a
classificação por cor **e texto**, prioridade e justificativa realmente devolvidas
pela API. Depois, consultar o histórico pelo mesmo número.

O histórico unifica os eventos de `eventos_historico` com as triagens salvas em
`triagens`, incluindo relatos anteriores à criação do frontend. A consulta não
altera o banco e evita repetir eventos de triagem já representados com o mesmo
relato e instante. A API mantém a ordem crescente; a interface mostra os mais
recentes primeiro e oferece filtros por tipo. O número do paciente deve ser o
mesmo no envio e na consulta. O endpoint de triagem não retorna especialidade;
o histórico exibe o valor disponível no registro, sem inferir uma especialidade.
A nova navegação utiliza `frontend/pages/historico.html` com dados reais da API.

A demonstração usa regras locais por palavras-chave e não realiza diagnóstico.

### Banco antigo: erro ao enviar sintomas

Se o SQLite foi criado antes da integração da triagem, execute uma vez:

```powershell
.\venv\Scripts\python.exe -m scripts.atualizar_banco
```

O comando utiliza o `DATABASE_URL` configurado, faz um backup SQLite consistente
(`*.backup-*.db`) e adiciona as colunas `estrategia`, `classificacao` e `prioridade`
ausentes. Registros anteriores são preservados. Pode ser executado novamente sem
duplicar alterações. Reinicie o servidor após a atualização e recarregue o navegador.

## Integração contínua — CI-01 (#39)

O workflow `.github/workflows/pytest.yml` executa a suíte em pushes na branch
`dev` e em pull requests destinados a `dev`. No GitHub, acompanhe
o resultado na aba **Actions**, no workflow **Testes Python**, ou nos checks do PR.

O job usa Ubuntu e Python 3.12, instala `requirements-dev.txt` (que também inclui
as dependências da aplicação) e executa `python -m pytest -q` na raiz do projeto.
O cache do pip considera ambos os arquivos de dependências. O ambiente usa
`MODO_IA=mock` e SQLite em memória, sem depender do `.env`, banco local ou chave
de API. Não é necessário iniciar o servidor nem executar o seed.

Falhas de instalação ou de testes interrompem o job e produzem um check de falha;
o limite de execução é de 10 minutos. O workflow tem permissão somente de leitura
do repositório e não publica código. Exigir o check para permitir merge depende
de uma regra de proteção da branch, configurada separadamente no GitHub.

Para reproduzir os testes no PowerShell:

```powershell
$env:MODO_IA = "mock"
$env:DATABASE_URL = "sqlite:///:memory:"
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest -q
```
