"use strict";
// Senha somente em memória: não persiste em localStorage/sessionStorage ou URL.
window.AdminAPI = (() => {
  let password = "";
  let revision = 0;
  function logout() { password = ""; revision += 1; }
  function isAuthenticated() { return Boolean(password); }
  async function request(path, options = {}) {
    if (!password) throw new Error("Entre com a senha administrativa.");
    if (!path.startsWith('/admin/')) throw new Error("Destino administrativo inválido.");
    const attempt = revision;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, {
        ...options, cache: "no-store", signal: controller.signal,
        headers: {"Content-Type": "application/json", "X-Admin-Password": password},
      });
      let body;
      try { body = await response.json(); }
      catch { throw new Error("O serviço não retornou uma resposta válida. Tente novamente."); }
      if (attempt !== revision) throw new Error("Sessão encerrada. Entre novamente.");
      if (response.status === 401 || response.status === 503) logout();
      if (!response.ok) {
        const mensagem = typeof body.detail === "string" ? body.detail :
          "Confira os campos do formulário, os dias de atendimento e o limite diário.";
        throw new Error(response.status >= 500 && response.status !== 503 ?
          "O servidor não conseguiu concluir a operação. Verifique o serviço antes de repetir um cadastro." : mensagem);
      }
      return body;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("O serviço demorou a responder. Confira a listagem antes de repetir um cadastro.");
      if (error instanceof TypeError) throw new Error("Não foi possível conectar ao serviço.");
      throw error;
    } finally { clearTimeout(timer); }
  }
  async function login(value) {
    logout();
    password = value;
    const attempt = revision;
    try { return await request("/admin/medicos"); }
    catch (error) { if (attempt === revision) logout(); throw error; }
  }
  return {login, logout, request, isAuthenticated};
})();
