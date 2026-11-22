# Painel administrativo do protótipo

Área separada em `/pages/admin.html`, sem atalho nos menus públicos. Reutiliza
a identidade visual, os controles de leitura e alto contraste do SinalVital.

## Executar

Defina uma senha escolhida por você no `.env`, sem compartilhar esse arquivo:

```env
ADMIN_PASSWORD=sua-senha-administrativa
```

Reinicie a API depois de alterar a configuração:

```powershell
.\venv\Scripts\python.exe -m app.seed
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/pages/admin.html e informe a senha. O campo vazio no
`.env.example` deixa os endpoints administrativos desabilitados (503).

O backend verifica `X-Admin-Password` em **todas** as operações administrativas.
Senha ausente ou inválida retorna 401. A senha fica apenas em memória na página,
não em `sessionStorage`, `localStorage`, HTML ou URL. Sair limpa a memória, o
formulário e os dados exibidos; recarregar exige nova entrada. As respostas usam
`Cache-Control: no-store`. Não há contas administrativas, edição ou exclusão
nesta entrega. A senha compartilhada atende à demonstração local, não substitui
uma autenticação administrativa completa para produção.

## Médicos

- `GET /admin/medicos`: lista completa, incluindo modalidade e dados de agenda.
- `POST /admin/medicos`: cadastra médico e retorna o ID com status 201.
- Campos: nome, especialidade, modalidade (`urgencia`, `agendamento`, `ambos`),
  capacidade positiva e estado ativo/inativo.
- Agendamento ou ambas as modalidades exigem dias válidos e limite diário
  positivo. Médicos exclusivos de urgência não recebem campos de agenda.
- A especialidade é normalizada para identificadores como `clinica_geral`.
- Nome e especialidade já cadastrados retornam 409 para evitar repetição
  acidental no protótipo. Dados inválidos retornam 422.
- O ID do novo médico ativo já pode ser utilizado no login clínico existente.

## Pacientes e atendimentos

`GET /admin/pacientes?nome=&etapa=todos` lista pacientes por nome e os vínculos
separados de urgência, agendamento e consultas registradas. Triagens ainda sem
vínculo também são exibidas. Nenhum paciente recebe um único status agregado.

O painel mostra nome, ID, tipo/etapa do vínculo, médico e data. Não expõe relato,
motivo clínico, diagnóstico, conduta ou anamnese nessas respostas. O conteúdo
clínico continua no prontuário do painel médico. Não existem operações para
editar ou excluir pacientes/atendimentos nesta área.

Filtros de etapa: `todos`, `sem_atendimento`, `triagem`, `aguardando`,
`em_atendimento`, `agendado`, `atendido`, `cancelado`. O filtro seleciona os
pacientes que possuem a etapa, mas preserva todos os seus vínculos no resultado.
Uma urgência concluída e sua consulta são registros distintos e podem aparecer
juntos. A leitura administrativa não recalcula scores nem aloca pacientes.

## Testes

- `tests/integration/test_admin.py`: senha, configuração ausente, validações,
  duplicidade, cadastro integrado ao login e vínculos simultâneos do paciente.
- `tests/frontend/admin-api.test.cjs`: header de acesso, limpeza da senha,
  resposta atrasada após sair e erro de configuração.
- O pytest executa os testes JavaScript através de `tests/test_auth_javascript.py`;
  requer Node.js no PATH, como os testes de perfil já existentes.

```powershell
.\venv\Scripts\python.exe -m pytest -q
node --test tests/frontend/admin-api.test.cjs
```

Esta branch parte de `feat/75-meus-dados-paciente`: a consulta de Meus dados e a
saudação do paciente são uma entrega anterior preservada nesta base.
