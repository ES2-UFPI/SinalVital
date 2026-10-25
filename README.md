# SinalVital

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
