"use strict";
(() => {
  function iniciar() {
    const form = document.getElementById("login-form");
    if (!form) return;
    function atualizar() {
      const medico = form.elements.perfil.value === "medico";
      const input = document.getElementById("identificador");
      input.inputMode = medico ? "numeric" : "text";
      input.placeholder = medico ? "Número do cadastro profissional" : "Seu número ou e-mail cadastrado";
      document.getElementById("identificador-label").textContent = medico
        ? "Número do cadastro profissional *" : "Número do cadastro ou e-mail *";
      document.getElementById("login-ajuda").textContent = medico
        ? "Use o número informado pela equipe administrativa ao cadastrar seu perfil médico."
        : "Use o número recebido no cadastro ou o e-mail cadastrado.";
      document.getElementById("login-submit").textContent = medico
        ? "Entrar no painel médico →" : "Entrar no meu espaço →";
      document.getElementById("login-cadastro").hidden = medico;
    }
    form.addEventListener("change", event => {
      if (event.target.name === "perfil") atualizar();
    });
    atualizar();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
