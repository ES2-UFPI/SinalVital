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

## Testes

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest -q
```

Os testes utilizam SQLite temporário, separado do banco da aplicação.
Cobrem cadastro, validação, duplicidade de e-mail e repetição do seed.
