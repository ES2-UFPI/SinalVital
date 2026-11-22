"use strict";

(async function carregarMeusDados() {
  const perfil = Auth.current();
  if (perfil?.perfil !== "paciente") return;
  const feedback = document.getElementById("dados-feedback");
  const painel = document.getElementById("dados-paciente");
  feedback.textContent = "Carregando seus dados…";
  painel.setAttribute("aria-busy", "true");
  try {
    // O ID vem exclusivamente do perfil, nunca da URL ou de um campo editável.
    const paciente = await api(`/pacientes/${perfil.id}`);
    const campos = [
      ["Número de paciente", paciente.id], ["Nome completo", paciente.nome],
      ["E-mail", paciente.email],
      ["Idade", paciente.idade == null ? "Não informada" : `${paciente.idade} anos`],
      ["Condição crônica", paciente.condicao_cronica || "Não informada"],
    ];
    const lista = document.createElement("dl");
    lista.className = "profile-data";
    for (const [rotulo, valor] of campos) {
      const grupo = document.createElement("div");
      const titulo = document.createElement("dt");
      const conteudo = document.createElement("dd");
      titulo.textContent = rotulo;
      conteudo.textContent = String(valor);
      grupo.append(titulo, conteudo);
      lista.append(grupo);
    }
    painel.replaceChildren(lista);
    feedback.textContent = "Seus dados foram carregados.";
  } catch (error) {
    feedback.setAttribute("role", "alert");
    feedback.textContent = error.message || "Não foi possível carregar seus dados. Tente novamente.";
  } finally {
    painel.removeAttribute("aria-busy");
  }
})();
