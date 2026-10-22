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
#  "justificativa": "Classificado como emergencia por mencionar: dor no peito, falta de ar."}
```

O mock aplica regras iniciais por palavras-chave, priorizando emergência sobre
alta e usando baixa como padrão. Retorna `urgencia`, `especialidade` e
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
