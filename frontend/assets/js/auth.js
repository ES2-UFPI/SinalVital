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
  function init() {
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
  return {current, logout};
})();
