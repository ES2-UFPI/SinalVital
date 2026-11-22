# Login simples do protótipo — #74

Acesse `/pages/login.html` depois de executar o seed e iniciar o Uvicorn.
A tela reutiliza `base.css`, os controles A−/A+ e alto contraste do SinalVital.

`POST /auth/login` recebe `perfil` (`paciente` ou `medico`) e `identificador`
(string). Pacientes usam ID ou e-mail do cadastro. Médicos usam ID e devem estar
ativos. Retorna `{perfil, id, nome}` com status 200; identificação não encontrada
ou médico inativo retorna 401; dados inválidos retornam 422. Os IDs de médicos
podem ser consultados em `GET /medicos` pelo `/docs`.

O perfil fica no `sessionStorage` da aba. O botão **Sair / Trocar Perfil** limpa
o perfil e o ID de paciente legado. O cadastro continua disponível sem login.
No complemento da #75, pacientes já identificados veem **Meus dados** para
consulta do cadastro, e recebem uma saudação com seu nome na página inicial.

Esta é uma identificação sem senha para demonstração com dados fictícios.
Não cria token nem restringe o acesso direto à API. A navegação adaptada e os
filtros de visualização são a próxima entrega, na #75.

TDD: `tests/integration/test_auth.py` cobre os dois perfis, paciente por ID/e-mail,
identificação inválida, médico inativo, validação dos campos e a tela de login.
Execute `python -m pytest -q` para validar a suíte.
