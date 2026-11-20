"use strict";

// ── Estado da tela de agendamento ──────────────────────────────────────────
let especialidadeSelecionada = "";
let medicoSelecionado = null;
let dataSelecionada = null;
let triagemPreviaId = null;
let agendamentoCriadoAtual = null;

// ── Elementos do DOM ───────────────────────────────────────────────────────
const $id = (id) => document.getElementById(id);

const formAgendamento = $id("agendamento-form");
const inputPacienteId = $id("paciente-id");
const selectEspecialidade = $id("select-especialidade");
const containerMedicos = $id("container-medicos");
const listaMedicosEl = $id("lista-medicos");
const containerDatas = $id("container-datas");
const gradeDatasEl = $id("grade-datas");
const inputMotivo = $id("motivo-agendamento");
const checkGestante = $id("check-gestante");
const campoTriagemId = $id("triagem-id-oculto");
const avisoTriagemPrevia = $id("aviso-triagem-previa");
const feedbackEl = $id("feedback");
const painelUrgenciaEl = $id("painel-recomendacao-urgencia");
const confirmacaoAgendamentoEl = $id("confirmacao-agendamento");
const listaFilaAgendadaEl = $id("fila-agendada-lista");
const filaAgendadaVaziaEl = $id("fila-agendada-vazia");
const btnAtualizarFilaAgendada = $id("btn-atualizar-fila-agendada");

// ── Utilitários ─────────────────────────────────────────────────────────────
function mostrarFeedback(msg, tipo = "info") {
  if (!feedbackEl) return;
  feedbackEl.textContent = msg;
  feedbackEl.className = "feedback" + (tipo === "error" ? " error" : tipo === "success" ? " success" : "");
  feedbackEl.hidden = !msg;
  feedbackEl.setAttribute("role", tipo === "error" ? "alert" : "status");
}

function ocultarFeedback() {
  if (feedbackEl) feedbackEl.hidden = true;
}

function formatarDataBR(dataISO) {
  if (!dataISO) return "—";
  const partes = String(dataISO).split("-");
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
  }
  return dataISO;
}

function formatarEspecialidadeNome(valor) {
  if (!valor) return "Clínica Geral";
  const mapa = {
    cardiologia: "Cardiologia",
    clinica_geral: "Clínica Geral",
    oftalmologia: "Oftalmologia",
    pediatria: "Pediatria",
    neurologia: "Neurologia",
    ortopedia: "Ortopedia",
  };
  const chave = String(valor).toLowerCase().trim();
  return mapa[chave] || chave.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

// ── 1. Leitura de parâmetros da URL (Triagem Prévia) ───────────────────────
function inicializarParametrosURL() {
  const urlParams = new URLSearchParams(location.search);
  const paramPaciente = urlParams.get("paciente");
  const paramTriagemId = urlParams.get("triagem_id");
  const paramMotivo = urlParams.get("motivo") || urlParams.get("justificativa");
  const paramEspecialidade = urlParams.get("especialidade");

  // Preenche ID do paciente da sessão ou da URL
  if (inputPacienteId) {
    if (paramPaciente && /^[1-9]\d*$/.test(paramPaciente)) {
      inputPacienteId.value = paramPaciente;
    } else {
      const sessaoPaciente = sessionStorage.getItem("sv-patient");
      if (sessaoPaciente) inputPacienteId.value = sessaoPaciente;
    }
  }

  // Se veio de triagem prévia
  if (paramTriagemId && /^[1-9]\d*$/.test(paramTriagemId)) {
    triagemPreviaId = Number(paramTriagemId);
    if (campoTriagemId) campoTriagemId.value = String(triagemPreviaId);

    if (inputMotivo && paramMotivo) {
      inputMotivo.value = paramMotivo;
    }

    if (avisoTriagemPrevia) {
      avisoTriagemPrevia.hidden = false;
      avisoTriagemPrevia.textContent =
        "✓ Motivo e dados pré-preenchidos a partir da sua triagem anterior (sem cobrança de nova análise de IA).";
    }
  }

  if (paramEspecialidade && selectEspecialidade) {
    especialidadeSelecionada = paramEspecialidade.toLowerCase().trim();
  }
}

// ── 2. Carregar Médicos por Especialidade ──────────────────────────────────
async function carregarMedicosDaEspecialidade(especialidade) {
  if (!containerMedicos || !listaMedicosEl) return;
  medicoSelecionado = null;
  dataSelecionada = null;
  if (containerDatas) containerDatas.hidden = true;

  if (!especialidade) {
    containerMedicos.hidden = true;
    listaMedicosEl.replaceChildren();
    return;
  }

  listaMedicosEl.replaceChildren();
  const loading = document.createElement("p");
  loading.textContent = "Procurando médicos disponíveis...";
  listaMedicosEl.appendChild(loading);
  containerMedicos.hidden = false;

  try {
    const medicos = await api(`/agendamentos/medicos?especialidade=${encodeURIComponent(especialidade)}`);
    listaMedicosEl.replaceChildren();

    if (!Array.isArray(medicos) || medicos.length === 0) {
      const semMedico = document.createElement("p");
      semMedico.className = "hint";
      semMedico.textContent = `Nenhum médico de agendamento disponível para ${formatarEspecialidadeNome(especialidade)} no momento.`;
      listaMedicosEl.appendChild(semMedico);
      return;
    }

    medicos.forEach((medico) => {
      const card = document.createElement("div");
      card.className = "medico-opcao-card";
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.setAttribute(
        "aria-label",
        `Selecionar ${medico.nome}, atende em: ${medico.dias_atendimento || "dias da semana"}`
      );

      const nomeEl = document.createElement("strong");
      nomeEl.textContent = `Dr(a). ${medico.nome}`;

      const diasEl = document.createElement("span");
      diasEl.className = "medico-dias";
      diasEl.textContent = `Atende: ${medico.dias_atendimento || "Segunda a sexta"}`;

      const limiteEl = document.createElement("span");
      limiteEl.className = "medico-limite";
      limiteEl.textContent = `Capacidade: até ${medico.limite_diario || 1} pacientes/dia`;

      card.append(nomeEl, diasEl, limiteEl);

      function selecionarEsteMedico() {
        document.querySelectorAll(".medico-opcao-card").forEach((c) => c.classList.remove("selecionado"));
        card.classList.add("selecionado");
        medicoSelecionado = medico;
        carregarDatasDisponiveis(medico.id);
      }

      card.addEventListener("click", selecionarEsteMedico);
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selecionarEsteMedico();
        }
      });

      listaMedicosEl.appendChild(card);
    });
  } catch (err) {
    listaMedicosEl.replaceChildren();
    mostrarFeedback(`Erro ao carregar médicos: ${err.message}`, "error");
  }
}

// ── 3. Carregar e Exibir Datas (com bloqueio visual de dias lotados) ────────
async function carregarDatasDisponiveis(medicoId) {
  if (!containerDatas || !gradeDatasEl) return;
  dataSelecionada = null;
  gradeDatasEl.replaceChildren();

  const loading = document.createElement("p");
  loading.textContent = "Carregando calendário de vagas...";
  gradeDatasEl.appendChild(loading);
  containerDatas.hidden = false;

  try {
    const disponibilidades = await api(`/agendamentos/disponibilidade?medico_id=${medicoId}&dias=21`);
    gradeDatasEl.replaceChildren();

    if (!Array.isArray(disponibilidades) || disponibilidades.length === 0) {
      const semDatas = document.createElement("p");
      semDatas.textContent = "Não há dias de atendimento disponíveis nas próximas semanas.";
      gradeDatasEl.appendChild(semDatas);
      return;
    }

    disponibilidades.forEach((disp) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "dia-opcao-btn";

      const dataFormatada = formatarDataBR(disp.data);
      const diaSemana = disp.dia_semana || "";

      if (!disp.disponivel) {
        // Bloqueio visual para dia lotado
        btn.classList.add("dia-lotado");
        btn.disabled = true;
        btn.setAttribute("aria-disabled", "true");
        btn.setAttribute(
          "aria-label",
          `${diaSemana}, ${dataFormatada}: DIA LOTADO, sem vagas disponíveis`
        );
        btn.innerHTML = `
          <span class="dia-nome">${diaSemana}</span>
          <span class="dia-data">${dataFormatada}</span>
          <span class="dia-vagas tag-lotado">LOTADO (0 vagas)</span>
        `;
      } else {
        // Dia com vagas abertas
        btn.classList.add("dia-disponivel");
        btn.setAttribute(
          "aria-label",
          `${diaSemana}, ${dataFormatada}: ${disp.vagas_restantes} vaga(s) disponível(is)`
        );
        btn.innerHTML = `
          <span class="dia-nome">${diaSemana}</span>
          <span class="dia-data">${dataFormatada}</span>
          <span class="dia-vagas tag-livre">${disp.vagas_restantes} vaga(s) livre(s)</span>
        `;

        btn.addEventListener("click", () => {
          document.querySelectorAll(".dia-opcao-btn").forEach((b) => b.classList.remove("selecionado"));
          btn.classList.add("selecionado");
          dataSelecionada = disp.data;
          ocultarFeedback();
        });
      }

      gradeDatasEl.appendChild(btn);
    });
  } catch (err) {
    gradeDatasEl.replaceChildren();
    mostrarFeedback(`Erro ao verificar disponibilidade: ${err.message}`, "error");
  }
}

// ── 4. Submissão do Agendamento ────────────────────────────────────────────
async function submeterAgendamento(e) {
  e.preventDefault();
  ocultarFeedback();
  if (painelUrgenciaEl) painelUrgenciaEl.hidden = true;
  if (confirmacaoAgendamentoEl) confirmacaoAgendamentoEl.hidden = true;

  const pacienteIdVal = inputPacienteId ? inputPacienteId.value.trim() : "";
  if (!pacienteIdVal || !/^[1-9]\d*$/.test(pacienteIdVal)) {
    mostrarFeedback("Por favor, informe seu número de paciente.", "error");
    inputPacienteId?.focus();
    return;
  }

  if (!medicoSelecionado) {
    mostrarFeedback("Por favor, escolha um médico de agendamento.", "error");
    return;
  }

  if (!dataSelecionada) {
    mostrarFeedback("Por favor, selecione uma data disponível no calendário.", "error");
    return;
  }

  const motivoVal = inputMotivo ? inputMotivo.value.trim() : "";
  if (!motivoVal || motivoVal.length < 3) {
    mostrarFeedback("Descreva brevemente o motivo da consulta.", "error");
    inputMotivo?.focus();
    return;
  }

  const payload = {
    paciente_id: Number(pacienteIdVal),
    medico_id: Number(medicoSelecionado.id),
    data_agendamento: dataSelecionada,
    motivo: motivoVal,
    triagem_id: triagemPreviaId || null,
    gestante: checkGestante ? Boolean(checkGestante.checked) : false,
  };

  const btnSalvar = formAgendamento.querySelector('button[type="submit"]');
  if (btnSalvar) btnSalvar.disabled = true;
  const fecharLoading = Feedback.carregando("Analisando motivo e agendando consulta...");

  try {
    const agendamento = await api("/agendamentos", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    agendamentoCriadoAtual = agendamento;

    // Se a IA recomendar urgência
    if (agendamento.recomenda_urgencia) {
      exibirRecomendacaoUrgencia(agendamento);
    } else {
      exibirSucessoAgendamento(agendamento);
    }

    carregarFilaAgendamentos();
  } catch (err) {
    mostrarFeedback(err.message, "error");
    Feedback.erro(err.message);
  } finally {
    fecharLoading();
    if (btnSalvar) btnSalvar.disabled = false;
  }
}

// ── 5. Exibir Recomendação de Urgência da IA com Escolha ────────────────────
function exibirRecomendacaoUrgencia(agendamento) {
  if (!painelUrgenciaEl) return;

  const textoJustificativa = agendamento.justificativa_urgencia || "Seus sintomas indicam que você pode precisar de atendimento imediato.";
  const dataFormatada = formatarDataBR(agendamento.data_agendamento);

  painelUrgenciaEl.innerHTML = `
    <div class="alerta-urgencia-box" role="alert">
      <span class="alerta-icone" aria-hidden="true">⚠️</span>
      <h2>Atenção: A avaliação clínica identificou sintomas de urgência</h2>
      <p class="alerta-motivo"><strong>Justificativa da IA:</strong> ${textoJustificativa}</p>
      <p>Sua consulta foi agendada para <strong>${dataFormatada}</strong>, mas você pode optar por atendimento prioritário agora.</p>
      
      <div class="alerta-acoes">
        <button type="button" id="btn-ir-urgencia-imediata" class="button primary btn-urgencia">
          🚨 Ir direto para a Fila de Urgência agora
        </button>
        <button type="button" id="btn-manter-agendamento" class="button secondary">
          Manter agendamento para ${dataFormatada}
        </button>
      </div>
    </div>
  `;

  painelUrgenciaEl.hidden = false;
  painelUrgenciaEl.scrollIntoView({ behavior: "smooth" });

  $id("btn-ir-urgencia-imediata")?.addEventListener("click", async () => {
    await migrarParaFilaUrgencia(agendamento);
  });

  $id("btn-manter-agendamento")?.addEventListener("click", () => {
    exibirSucessoAgendamento(agendamento);
  });
}

async function migrarParaFilaUrgencia(agendamento) {
  const fecharLoading = Feedback.carregando("Encaminhando para a Fila de Urgência...");
  try {
    // Insere na fila de urgência reutilizando a triagem existente sem gastar tokens!
    await api("/fila", {
      method: "POST",
      body: JSON.stringify({
        triagem_id: agendamento.triagem_id,
        paciente_id: agendamento.paciente_id,
      }),
    });

    Feedback.sucesso("Você foi inserido na Fila de Urgência com prioridade!");
    setTimeout(() => {
      location.href = `/pages/fila.html?paciente=${encodeURIComponent(agendamento.paciente_id)}`;
    }, 1200);
  } catch (err) {
    mostrarFeedback(`Não foi possível transferir para a fila de urgência: ${err.message}`, "error");
  } finally {
    fecharLoading();
  }
}

function exibirSucessoAgendamento(agendamento) {
  if (painelUrgenciaEl) painelUrgenciaEl.hidden = true;
  if (!confirmacaoAgendamentoEl) return;

  const dataFormatada = formatarDataBR(agendamento.data_agendamento);
  const nomeMedico = agendamento.medico_nome || (medicoSelecionado ? medicoSelecionado.nome : "Médico");
  const esp = formatarEspecialidadeNome(agendamento.medico_especialidade || especialidadeSelecionada);

  confirmacaoAgendamentoEl.innerHTML = `
    <div class="comprovante-box">
      <span class="icone-sucesso" aria-hidden="true">✓</span>
      <h2>Consulta agendada com sucesso!</h2>
      <p>Guarde as informações do seu atendimento:</p>
      <ul>
        <li><strong>Paciente:</strong> ${agendamento.paciente_nome || "Paciente"} (#${agendamento.paciente_id})</li>
        <li><strong>Data:</strong> ${dataFormatada}</li>
        <li><strong>Profissional:</strong> Dr(a). ${nomeMedico}</li>
        <li><strong>Especialidade:</strong> ${esp}</li>
        <li><strong>Prioridade calculada:</strong> ${typeof agendamento.prioridade === "number" ? agendamento.prioridade.toFixed(1) : agendamento.prioridade} pontos</li>
        <li><strong>Status:</strong> ${agendamento.status}</li>
      </ul>
      <p class="hint">Você pode acompanhar suas consultas na lista de Consultas Agendadas logo abaixo.</p>
    </div>
  `;

  confirmacaoAgendamentoEl.hidden = false;
  confirmacaoAgendamentoEl.scrollIntoView({ behavior: "smooth" });
  Feedback.sucesso("Consulta agendada com sucesso!");
}

// ── 6. Renderizar Fila de Consultas Agendadas (Separada da Urgência) ────────
async function carregarFilaAgendamentos() {
  if (!listaFilaAgendadaEl) return;

  listaFilaAgendadaEl.replaceChildren();
  try {
    const agendamentos = await api("/agendamentos");
    listaFilaAgendadaEl.replaceChildren();

    if (!Array.isArray(agendamentos) || agendamentos.length === 0) {
      if (filaAgendadaVaziaEl) filaAgendadaVaziaEl.hidden = false;
      return;
    }

    if (filaAgendadaVaziaEl) filaAgendadaVaziaEl.hidden = true;

    agendamentos.forEach((item, index) => {
      const card = document.createElement("li");
      card.className = "queue-card agendamento-card";
      card.setAttribute(
        "aria-label",
        `Posição ${index + 1} da fila agendada: ${item.paciente_nome || "Paciente"} para ${formatarDataBR(item.data_agendamento)}`
      );

      const topo = document.createElement("div");
      topo.className = "queue-card-top";

      const posEl = document.createElement("span");
      posEl.className = "fila-posicao agendamento-posicao";
      posEl.textContent = String(index + 1);

      const nomeEl = document.createElement("h3");
      nomeEl.textContent = item.paciente_nome || `Paciente #${item.paciente_id}`;

      const badgesEl = document.createElement("div");
      badgesEl.className = "queue-card-badges";

      const badgeData = document.createElement("span");
      badgeData.className = "badge azul";
      badgeData.textContent = `📅 ${formatarDataBR(item.data_agendamento)}`;
      badgesEl.appendChild(badgeData);

      const scoreEl = document.createElement("span");
      scoreEl.className = "queue-score";
      scoreEl.textContent = `Prioridade: ${typeof item.prioridade === "number" ? item.prioridade.toFixed(1) : item.prioridade}`;
      badgesEl.appendChild(scoreEl);

      topo.append(posEl, nomeEl, badgesEl);

      const infoEl = document.createElement("div");
      infoEl.className = "queue-card-info";

      function infoRow(rotulo, valor) {
        const row = document.createElement("p");
        row.className = "queue-info-row";
        const strong = document.createElement("strong");
        strong.textContent = rotulo;
        const span = document.createElement("span");
        span.textContent = valor;
        row.append(strong, span);
        return row;
      }

      infoEl.appendChild(infoRow("Médico:", `Dr(a). ${item.medico_nome || "Médico"} (${formatarEspecialidadeNome(item.medico_especialidade)})`));
      infoEl.appendChild(infoRow("Motivo:", item.motivo || "Consulta de rotina"));
      infoEl.appendChild(infoRow("Status:", item.status || "agendado"));

      card.append(topo, infoEl);
      listaFilaAgendadaEl.appendChild(card);
    });
  } catch (err) {
    mostrarFeedback(`Erro ao listar agendamentos: ${err.message}`, "error");
  }
}

// ── 7. Inicialização ────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  inicializarParametrosURL();

  selectEspecialidade?.addEventListener("change", (e) => {
    especialidadeSelecionada = e.target.value;
    carregarMedicosDaEspecialidade(especialidadeSelecionada);
  });

  if (especialidadeSelecionada && selectEspecialidade) {
    selectEspecialidade.value = especialidadeSelecionada;
    carregarMedicosDaEspecialidade(especialidadeSelecionada);
  }

  formAgendamento?.addEventListener("submit", submeterAgendamento);
  btnAtualizarFilaAgendada?.addEventListener("click", carregarFilaAgendamentos);

  carregarFilaAgendamentos();
});
