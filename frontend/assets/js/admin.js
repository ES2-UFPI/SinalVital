"use strict";
(() => {
  const byId = id => document.getElementById(id);
  const loginForm = byId("admin-login");
  const medicoForm = byId("admin-medico-form");
  const feedback = byId("admin-feedback");
  const tipoLabel = {urgencia:"Urgência",agendamento:"Agendamento",ambos:"Ambos",
    triagem:"Triagem",consulta:"Consulta registrada"};
  const etapaLabel = {triagem:"Triagem realizada",aguardando:"Aguardando",em_atendimento:"Em atendimento",
    agendado:"Agendado",atendido:"Atendido",cancelado:"Cancelado"};
  function node(tag, text, classe) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (classe) element.className = classe;
    return element;
  }
  function aviso(message, erro = false) {
    feedback.textContent = message;
    feedback.hidden = !message;
    feedback.classList.toggle("error", erro);
    feedback.setAttribute("role", erro ? "alert" : "status");
  }
  function sair() {
    AdminAPI.logout();
    byId("admin-area").hidden = true;
    loginForm.hidden = false;
    byId("admin-medicos-lista").replaceChildren();
    byId("admin-pacientes-lista").replaceChildren();
    medicoForm.reset(); loginForm.reset();
    byId("admin-filtros").reset();
    ajustarAgenda();
    aviso(""); byId("admin-password").focus();
  }
  async function executar(button, action) {
    button.disabled = true;
    aviso("Carregando…");
    try { await action(); }
    catch (error) {
      if (!AdminAPI.isAuthenticated()) sair();
      aviso(error.message, true);
    }
    finally { button.disabled = false; }
  }
  function renderMedicos(medicos) {
    const lista = byId("admin-medicos-lista"); lista.replaceChildren();
    if (!medicos.length) { lista.append(node("p", "Nenhum médico cadastrado.")); return; }
    for (const medico of medicos) {
      const card = node("li", undefined, "admin-card");
      card.append(node("h3", `${medico.nome} · #${medico.id}`),
        node("p", `${medico.especialidade.replace(/_/g," ")} · ${tipoLabel[medico.tipo_atendimento]} · ${medico.ativo ? "Ativo" : "Inativo"}`),
        node("p", `Capacidade simultânea: ${medico.capacidade_simultanea}`));
      if (medico.tipo_atendimento !== "urgencia") {
        card.append(node("p", `Dias: ${medico.dias_atendimento || "Não informados"} · Limite diário: ${medico.limite_diario ?? "Não informado"}`));
      }
      lista.append(card);
    }
  }
  function formatarData(value) {
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value.split("-").reverse().join("/");
    const date = new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : value + "Z");
    return isNaN(date) ? "Data não informada" : date.toLocaleString("pt-BR");
  }
  function renderPacientes(pacientes) {
    const lista = byId("admin-pacientes-lista"); lista.replaceChildren();
    if (!pacientes.length) { lista.append(node("p","Nenhum paciente encontrado para os filtros.")); return; }
    for (const paciente of pacientes) {
      const card = node("details", undefined, "admin-card");
      card.append(node("summary", `${paciente.nome} · #${paciente.id} · ${paciente.atendimentos.length} registro(s)`));
      if (!paciente.atendimentos.length) card.append(node("p","Sem atendimentos registrados."));
      else {
        const itens = node("ul", undefined, "admin-vinculos");
        for (const item of paciente.atendimentos) {
          const registro = node("li");
          registro.append(node("strong",`${tipoLabel[item.tipo]} · ${etapaLabel[item.etapa] || item.etapa}`),
            node("p",`${item.medico_nome || "Sem médico vinculado"} · ${formatarData(item.data)}`));
          itens.append(registro);
        }
        card.append(itens);
      }
      lista.append(card);
    }
  }
  async function carregarPacientes() {
    const params = new URLSearchParams({nome:byId("admin-busca").value.trim(), etapa:byId("admin-etapa").value});
    renderPacientes(await AdminAPI.request(`/admin/pacientes?${params}`));
    aviso("Pacientes atualizados.");
  }
  function ajustarAgenda() {
    const agenda = byId("admin-tipo").value !== "urgencia";
    byId("admin-agenda").hidden = !agenda;
    byId("admin-limite").disabled = !agenda;
    byId("admin-limite").required = agenda;
  }
  function selecionarAba(nome) {
    for (const id of ["medicos","pacientes"]) {
      const ativa = nome === id;
      byId(`aba-${id}`).setAttribute("aria-selected", String(ativa));
      byId(`aba-${id}`).tabIndex = ativa ? 0 : -1;
      byId(`painel-${id}`).hidden = !ativa;
    }
  }
  loginForm.addEventListener("submit", event => {
    event.preventDefault();
    executar(loginForm.querySelector('[type="submit"]'), async () => {
      const password = byId("admin-password").value;
      byId("admin-password").value = "";
      const medicos = await AdminAPI.login(password);
      renderMedicos(medicos);
      loginForm.hidden = true; byId("admin-area").hidden = false;
      selecionarAba("medicos"); aviso("Acesso administrativo liberado.");
      byId("aba-medicos").focus();
    });
  });
  medicoForm.addEventListener("submit", event => {
    event.preventDefault();
    executar(medicoForm.querySelector('[type="submit"]'), async () => {
      const agenda = byId("admin-tipo").value !== "urgencia";
      const dados = {nome:byId("admin-nome").value.trim(), especialidade:byId("admin-especialidade").value.trim(),
        tipo_atendimento:byId("admin-tipo").value, capacidade_simultanea:Number(byId("admin-capacidade").value),
        ativo:byId("admin-ativo").checked};
      if (agenda) {
        dados.dias_atendimento = Array.from(medicoForm.querySelectorAll('[name="dia"]:checked')).map(c=>c.value).join(",");
        dados.limite_diario = Number(byId("admin-limite").value);
      }
      const medico = await AdminAPI.request("/admin/medicos",{method:"POST",body:JSON.stringify(dados)});
      medicoForm.reset(); ajustarAgenda();
      aviso(`Médico ${medico.nome} cadastrado com o número ${medico.id}.`);
      // Falha ao atualizar a lista não apaga a confirmação do cadastro já realizado.
      try { renderMedicos(await AdminAPI.request("/admin/medicos")); }
      catch { aviso(`Médico cadastrado com o número ${medico.id}. Use Atualizar médicos para recarregar a lista.`); }
    });
  });
  byId("admin-sair").addEventListener("click", sair);
  byId("admin-tipo").addEventListener("change", ajustarAgenda);
  byId("admin-atualizar-medicos").addEventListener("click", event => executar(event.currentTarget, async()=>{
    renderMedicos(await AdminAPI.request("/admin/medicos")); aviso("Médicos atualizados.");
  }));
  byId("admin-filtros").addEventListener("submit", event=>{
    event.preventDefault(); executar(event.currentTarget.querySelector('[type="submit"]'),carregarPacientes);
  });
  for (const nome of ["medicos","pacientes"]) {
    byId(`aba-${nome}`).addEventListener("click",event=>{
      selecionarAba(nome);
      if (nome === "pacientes") executar(event.currentTarget,carregarPacientes);
    });
    byId(`aba-${nome}`).addEventListener("keydown",event=>{
      if (["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) {
        event.preventDefault();
        const outra=event.key === "Home" ? "medicos" : event.key === "End" ? "pacientes" : nome === "medicos" ? "pacientes" : "medicos";
        byId(`aba-${outra}`).focus(); byId(`aba-${outra}`).click();
      }
    });
  }
  ajustarAgenda();
})();
