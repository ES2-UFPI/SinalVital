"use strict";
// Identificação de demonstração. Não é uma credencial de autorização da API.
window.Auth = (() => {
  const key = "sv-profile";
  function current() {
    try {
      const perfil = JSON.parse(sessionStorage.getItem(key));
      return perfil && ["paciente", "medico"].includes(perfil.perfil) &&
        Number.isSafeInteger(perfil.id) && perfil.id > 0 && typeof perfil.nome === "string"
        ? perfil : null;
    } catch { return null; }
  }
  function save(perfil) {
    sessionStorage.setItem(key, JSON.stringify(perfil));
    sessionStorage.removeItem("sv-patient");
  }
  function logout() {
    sessionStorage.removeItem(key);
    sessionStorage.removeItem("sv-patient");
    location.assign("/pages/login.html");
  }
  function patientId(fallback = "") {
    const perfil = current();
    return perfil?.perfil === "paciente" ? String(perfil.id) : fallback;
  }
  function adaptResponse(path, body) {
    const perfil = current();
    if (!perfil || !Array.isArray(body)) return body;
    const route = path.split("?")[0];
    if (["/medicos", "/agendamentos/medicos"].includes(route) && perfil.perfil === "medico") {
      return body.filter(medico => medico.id === perfil.id);
    }
    if (route === "/fila") {
      if (perfil.perfil === "medico") return body.filter(item => item.medico_id === perfil.id);
      let posicao = 0;
      return body.map(item => ({...item,
        posicao_global: (item.status || "aguardando") === "aguardando" ? ++posicao : null,
      })).filter(item => item.paciente_id === perfil.id);
    }
    if (route === "/agendamentos" && perfil.perfil === "medico") {
      return body.filter(item => item.medico_id === perfil.id);
    }
    if (route === "/agendamentos" && perfil.perfil === "paciente") {
      return body.map((item, index) => ({...item, posicao_global: index + 1}))
        .filter(item => item.paciente_id === perfil.id);
    }
    return body;
  }
  function adaptView() {
    const perfil = current();
    const page = document.body.dataset.page;
    const publicPages = ["inicio", "login", "cadastro"];
    if (!perfil && !publicPages.includes(page)) {
      location.replace("/pages/login.html");
      return;
    }
    if (perfil?.perfil === "paciente" && page === "medico") {
      location.replace("/");
      return;
    }
    if (perfil?.perfil === "medico" && !["medico", "login"].includes(page)) {
      location.replace("/pages/medico.html");
      return;
    }
    document.querySelectorAll('[data-nav], a[href="/pages/medico.html"]').forEach(link => {
      const nav = link.dataset.nav || "medico";
      link.hidden = perfil?.perfil === "medico" ? nav !== "medico" : nav === "medico";
    });
    const heading = document.querySelector(".sidebar .eyebrow");
    if (heading && perfil) heading.textContent = perfil.perfil === "medico" ? "ESPAÇO DO MÉDICO" : "ESPAÇO DO PACIENTE";
    if (perfil?.perfil === "paciente") {
      const input = document.getElementById("paciente-id");
      if (input) { input.value = String(perfil.id); input.readOnly = true; }
    }
    if (perfil?.perfil === "medico") {
      const historicoPaciente = document.getElementById("prontuario-link-historico");
      if (historicoPaciente) historicoPaciente.hidden = true;
      for (const id of ["medico-id", "filtro-medico-fila"]) {
        const select = document.getElementById(id);
        if (select) select.disabled = true;
      }
      const titulo = document.querySelector(".page-heading h1");
      if (titulo && page === "medico") titulo.textContent = `Painel médico — ${perfil.nome}`;
      for (const id of ["medico-id-help", "filtro-medico-fila-help"]) {
        const ajuda = document.getElementById(id);
        if (ajuda) ajuda.textContent = "Exibindo o profissional identificado e os pacientes vinculados a ele.";
      }
    }
  }
  function init() {
    adaptView();
    const header = document.querySelector(".header");
    if (header) {
      const link = document.createElement("a");
      link.className = "button secondary";
      link.href = "/pages/login.html";
      link.textContent = current() ? "Sair / Trocar Perfil" : "Entrar";
      if (current()) link.addEventListener("click", event => { event.preventDefault(); logout(); });
      header.append(link);
    }
    const form = document.getElementById("login-form");
    if (!form) return;
    const feedback = document.getElementById("login-feedback");
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const button = form.querySelector('[type="submit"]');
      button.disabled = true;
      feedback.hidden = false;
      feedback.textContent = "Conferindo seu perfil…";
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 15000);
        let response;
        try {
          response = await fetch("/auth/login", {
            method: "POST", headers: {"Content-Type": "application/json"}, signal: controller.signal,
            body: JSON.stringify({perfil: form.elements.perfil.value,
              identificador: form.elements.identificador.value.trim()}),
          });
        } finally { clearTimeout(timer); }
        const perfil = await response.json();
        if (!response.ok) throw new Error(typeof perfil.detail === "string" ? perfil.detail : "Confira o perfil e o identificador.");
        save(perfil);
        location.assign(perfil.perfil === "medico" ? "/pages/medico.html" : "/");
      } catch (error) {
        feedback.setAttribute("role", "alert");
        feedback.textContent = error.name === "AbortError" ? "O serviço demorou a responder. Tente novamente." :
          error.message || "Não foi possível entrar. Tente novamente.";
      } finally { button.disabled = false; }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
  return {current, logout, patientId, adaptResponse};
})();
