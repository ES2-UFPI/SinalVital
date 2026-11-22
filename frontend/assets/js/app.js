"use strict";
const $ = (id) => document.getElementById(id);
const store = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* Reading controls still work without storage. */
    }
  },
};

let fontSize = Math.max(18, Math.min(24, Number(store.get("sv-font")) || 18));
function applyFont() {
  document.documentElement.style.setProperty("--font-size", `${fontSize}px`);
  if ($("font-down")) $("font-down").disabled = fontSize <= 18;
  if ($("font-up")) $("font-up").disabled = fontSize >= 24;
}
applyFont();

$("font-up")?.addEventListener("click", () => {
  fontSize = Math.min(24, fontSize + 2);
  applyFont();
  store.set("sv-font", fontSize);
});
$("font-down")?.addEventListener("click", () => {
  fontSize = Math.max(18, fontSize - 2);
  applyFont();
  store.set("sv-font", fontSize);
});

function contrast(active) {
  document.body.classList.toggle("high-contrast", active);
  $("contrast")?.setAttribute("aria-pressed", String(active));
}
contrast(store.get("sv-contrast") === "true");
$("contrast")?.addEventListener("click", () => {
  const active = !document.body.classList.contains("high-contrast");
  contrast(active);
  store.set("sv-contrast", active);
});

document
  .querySelector(`[data-nav="${document.body.dataset.page}"]`)
  ?.setAttribute("aria-current", "page");

// Patient identifier is kept only in this tab; clinical details are not stored in the browser.
const patientSession = {
  get() {
    try {
      return sessionStorage.getItem("sv-patient");
    } catch {
      return null;
    }
  },
  set(id) {
    try {
      sessionStorage.setItem("sv-patient", id);
    } catch {}
  },
};

const queryPatient = new URLSearchParams(location.search).get("paciente");
if ($("paciente-id")) {
  const isPainelMedico = document.body.dataset.page === "medico";
  $("paciente-id").value = /^[1-9]\d*$/.test(queryPatient || "")
    ? queryPatient
    : isPainelMedico
      ? ""
      : patientSession.get() || "";
}

function setFeedback(nodeOrMessage, message = "", type = "info") {
  let node = $("consulta-feedback") || $("feedback");
  let msg = message;
  let resolvedType = type;

  if (
    typeof nodeOrMessage === "string" ||
    nodeOrMessage === null ||
    nodeOrMessage === undefined
  ) {
    node = $("feedback") || $("consulta-feedback");
    msg = nodeOrMessage || "";
    resolvedType = message ? "error" : "info";
  } else if (typeof nodeOrMessage === "function") {
    node = $("consulta-feedback") || $("feedback");
  } else if (nodeOrMessage instanceof HTMLElement) {
    node = nodeOrMessage;
  }

  if (!node) return;
  const isError = resolvedType === "error" || resolvedType === true;
  const isSuccess = resolvedType === "success";
  node.hidden = !msg;
  node.textContent = msg;
  node.classList.toggle("error", isError);
  node.classList.toggle("success", isSuccess);
  node.setAttribute("role", isError ? "alert" : "status");
}

function feedback(message, error = false) {
  setFeedback($("feedback") || $("consulta-feedback"), message, error ? "error" : "info");
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
    if (response.status >= 500)
      throw new Error(
        "O servidor não conseguiu concluir a operação. Seus dados podem não ter sido salvos. Tente novamente após o suporte verificar o serviço.",
      );
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error(
        "O servidor retornou um formato inesperado. Atualize a página e tente novamente.",
      );
    }
    if (!response.ok) {
      if (response.status === 404) {
        if (typeof body?.detail === "string" && /m[eé]dico/i.test(body.detail)) {
          throw new Error(
            "Médico não encontrado. Selecione um profissional válido para registrar a consulta.",
          );
        }
        if (typeof body?.detail === "string" && /triagem/i.test(body.detail)) {
          throw new Error(body.detail);
        }
        throw new Error(
          "Paciente não encontrado. Confira o número ou faça seu cadastro.",
        );
      }
      if (response.status === 400 && typeof body?.detail === "string") {
        throw new Error(body.detail);
      }
      if (response.status === 409)
        throw new Error(
          "Este e-mail já está cadastrado. Use o número de paciente recebido anteriormente.",
        );
      if (response.status === 422)
        throw new Error("Confira os campos preenchidos e tente novamente.");
      throw new Error(
        "Não foi possível concluir agora. Tente novamente em instantes.",
      );
    }
    return body;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "A resposta demorou mais que o esperado. Confira o histórico antes de repetir um envio.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.",
      );
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function submit(form, message, task) {
  const button = form.querySelector('[type="submit"]');
  if (button && button.disabled) return;
  if (button) button.disabled = true;
  form.setAttribute("aria-busy", "true");
  feedback("");
  const fechar = Feedback.carregando(message);
  try {
    await task();
  } catch (error) {
    setFeedback(
      form.querySelector(".feedback") || $("consulta-feedback") || $("feedback"),
      error.message,
      "error",
    );
    Feedback.erro(error.message);
  } finally {
    fechar();
    if (button) button.disabled = false;
    form.removeAttribute("aria-busy");
  }
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

const labels = {
  vermelho: "Emergência",
  laranja: "Urgência alta",
  amarelo: "Urgência média",
  verde: "Urgência baixa",
  azul: "Urgência baixa",
  emergencia: "Emergência",
  alta: "Urgência alta",
  media: "Urgência média",
  baixa: "Urgência baixa",
};

const ESPECIALIDADES_LABELS = {
  cardiologia: "Cardiologia",
  clinica_geral: "Clínica Geral",
  oftalmologia: "Oftalmologia",
  pediatria: "Pediatria",
  neurologia: "Neurologia",
  ortopedia: "Ortopedia",
};

function formatarEspecialidade(valor) {
  if (!valor) return "Clínica Geral";
  const chave = String(valor).toLowerCase().trim();
  if (ESPECIALIDADES_LABELS[chave]) return ESPECIALIDADES_LABELS[chave];
  const texto = chave.replaceAll("_", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function badge(value) {
  const key = String(value || "").toLowerCase().trim();
  return element(
    "span",
    labels[key] || "Classificação não informada",
    `badge ${Object.hasOwn(labels, key) ? key : ""}`.trim(),
  );
}

function urgenciaBadge(value) {
  return badge(value);
}

function date(value) {
  if (!value) return "Data não informada";
  const normalized = /(Z|[+-]\d\d:?\d\d)$/.test(value) ? value : value + "Z";
  const d = new Date(normalized);
  return Number.isNaN(d.getTime())
    ? "Data não informada"
    : d.toLocaleString("pt-BR", { dateStyle: "medium", timeStyle: "short" });
}

// ---------------------------------------------------------------------------
// 01 · Cadastro de Pacientes
// ---------------------------------------------------------------------------
$("cadastro-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submit(form, "Salvando seu cadastro…", async () => {
    const nome = $("nome").value.trim();
    if (!nome) throw new Error("Preencha seu nome antes de continuar.");
    const body = {
      nome,
      email: $("email").value.trim(),
      idade: $("idade").value === "" ? null : Number($("idade").value),
      condicao_cronica: $("condicao").value.trim() || null,
    };
    const patient = await api("/pacientes", {
      method: "POST",
      body: JSON.stringify(body),
    });
    patientSession.set(patient.id);
    feedback(
      `Cadastro salvo com sucesso! Seu número de paciente é ${patient.id}. Guarde esse número.`,
    );
    $("continuar").href = `/pages/triagem.html?paciente=${patient.id}`;
    $("continuar").hidden = false;
  });
});

// ---------------------------------------------------------------------------
// 02 · Triagem + Encaminhamento Automático para a Fila (POST /fila)
// ---------------------------------------------------------------------------
document.querySelectorAll("[data-sintoma]").forEach((button) =>
  button.addEventListener("click", () => {
    const input = $("relato");
    if (!input) return;
    const text = input.value.trim();
    const symptom = button.dataset.sintoma;
    if (!text.toLowerCase().includes(symptom.toLowerCase())) {
      const next = text ? `${text}; ${symptom}` : symptom;
      if (!input.maxLength || input.maxLength < 0 || next.length <= input.maxLength) {
        input.value = next;
      }
    }
    input.focus();
  }),
);

const triagemForm = $("triagem-form");
triagemForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const result = $("triagem-resultado") || $("resultado");
  if (result) result.hidden = true;

  submit(form, "Analisando seu relato…", async () => {
    const pacienteId = $("paciente-id").value.trim();
    const relato = $("relato").value.trim();
    if (relato.length < 5)
      throw new Error("Descreva seus sintomas com pelo menos 5 caracteres.");

    const data = await api(`/pacientes/${pacienteId}/triagens`, {
      method: "POST",
      body: JSON.stringify({ relato, estrategia: "palavras_chave" }),
    });
    patientSession.set(pacienteId);

    // Integração automática da triagem com a fila priorizada (segura via try/catch)
    let filaItem = null;
    try {
      filaItem = await api("/fila", {
        method: "POST",
        body: JSON.stringify({
          triagem_id: data.id,
          paciente_id: Number(pacienteId),
        }),
      });
    } catch {
      /* Não interrompe o fluxo de triagem caso a fila não esteja disponível no momento */
    }

    if (result) {
      const titulo = element("h2", "Classificação inicial", "");
      titulo.id = "resultado-title";

      result.replaceChildren(
        badge(data.urgencia || data.classificacao),
        titulo,
        element("p", data.justificativa),
        element(
          "p",
          `Especialidade recomendada: ${formatarEspecialidade(data.especialidade || "clinica_geral")}`,
        ),
        element(
          "p",
          `Prioridade informada: ${data.prioridade}. Registro nº ${data.id} · ${date(data.criado_em)}`,
        ),
      );

      if (filaItem) {
        const medicoAlocado =
          filaItem.medico_alocado || "Aguardando vaga na especialidade";
        const scoreTexto =
          typeof filaItem.score === "number"
            ? ` · Score de prioridade: ${filaItem.score.toFixed(1)}`
            : "";
        result.append(
          element(
            "p",
            `Médico alocado na fila: ${medicoAlocado}${scoreTexto}`,
          ),
        );
      }

      result.append(
        element(
          "p",
          "Esta triagem é uma simulação por palavras-chave e não substitui avaliação médica.",
          "notice",
        ),
      );

      if (["vermelho", "laranja"].includes(data.classificacao)) {
        result.append(
          element(
            "p",
            "Procure atendimento imediato. Em caso de emergência, ligue para o SAMU 192.",
            "notice",
          ),
        );
        const call = element("a", "Ligar para o SAMU 192", "button primary");
        call.href = "tel:192";
        result.append(call);
      }

      const again = element("a", "Consultar meu histórico →", "button secondary");
      again.href = `/pages/historico.html?paciente=${encodeURIComponent(pacienteId)}`;
      result.append(again);

      const linkAgendamento = element(
        "a",
        "Ir para Agendamento →",
        "button secondary btn",
      );
      linkAgendamento.id = "btn-ir-agendamento";
      const paramsAgendamento = new URLSearchParams({
        paciente: pacienteId,
        triagem_id: String(data.id),
        especialidade: data.especialidade || "clinica_geral",
        motivo: data.justificativa || data.texto_sintomas || "",
      });
      linkAgendamento.href = `/pages/agendamento.html?${paramsAgendamento.toString()}`;
      result.append(linkAgendamento);

      const linkMedico = element(
        "a",
        "Abrir painel médico →",
        "button secondary btn",
      );
      linkMedico.href = `/pages/medico.html?paciente=${encodeURIComponent(pacienteId)}`;
      result.append(linkMedico);

      result.hidden = false;
    }

    Feedback.sucesso(
      "Triagem salva com sucesso. Confira a classificação abaixo.",
    );
  }).then(() => {
    const result = $("triagem-resultado") || $("resultado");
    if (result && !result.hidden) result.focus();
  });
});

// ---------------------------------------------------------------------------
// 03 · Histórico Clínico do Paciente
// ---------------------------------------------------------------------------
let events = [];
function renderHistory() {
  if (!$("timeline")) return;
  const filtered = events
    .filter((item) => !$("tipo")?.value || item.tipo_evento === $("tipo").value)
    .sort((a, b) => new Date(b.criado_em) - new Date(a.criado_em));
  $("timeline").replaceChildren();
  if ($("history-empty")) $("history-empty").hidden = filtered.length > 0;
  if (!filtered.length && $("history-empty")) {
    $("history-empty").replaceChildren(
      element(
        "h2",
        events.length
          ? "Nenhum registro com este filtro"
          : "Ainda não há eventos no histórico",
      ),
      element(
        "p",
        "Quando houver eventos disponíveis na API de histórico, eles aparecerão aqui.",
      ),
    );
  }
  for (const item of filtered) {
    const row = element("li");
    const time = element("time", date(item.criado_em));
    time.dateTime = item.criado_em;
    const selo =
      item.tipo_evento === "consulta" && !item.urgencia
        ? element("span", "Consulta médica", "badge azul")
        : badge(item.urgencia);
    row.append(
      time,
      element("h3", String(item.tipo_evento).replaceAll("_", " ")),
      selo,
      element("p", item.descricao),
      element(
        "p",
        `Especialidade: ${formatarEspecialidade(item.especialidade || "Não informada")}`,
      ),
    );
    if (item.justificativa)
      row.append(element("p", item.justificativa, "hint"));
    $("timeline").append(row);
  }
}

$("historico-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  events = [];
  $("timeline")?.replaceChildren();
  if ($("patient-summary")) $("patient-summary").hidden = true;
  if ($("history-empty")) $("history-empty").hidden = true;
  submit(form, "Carregando seu histórico…", async () => {
    const id = $("paciente-id").value.trim();
    const data = await api(`/pacientes/${id}/historico`);
    patientSession.set(id);
    const summary = $("patient-summary");
    if (summary) {
      summary.className = "patient-summary";
      summary.replaceChildren(
        element("h2", data.nome),
        element(
          "p",
          `Paciente nº ${data.id}${data.idade != null ? ` · ${data.idade} anos` : ""}`,
        ),
      );
      summary.hidden = false;
    }
    events = data.eventos_historico || [];
    renderHistory();
    Feedback.sucesso(
      `Histórico carregado. ${events.length} registro(s) disponível(is).`,
    );
  });
});

$("tipo")?.addEventListener("change", renderHistory);
// Load the selected patient's history immediately when arriving from triage or consultation.
if ($("historico-form") && /^[1-9]\d*$/.test($("paciente-id")?.value || "")) {
  $("historico-form").requestSubmit();
}

// ---------------------------------------------------------------------------
// 04 · Painel Médico da Dra. Helena (Fila Priorizada + Registro de Consulta)
// ---------------------------------------------------------------------------
const consultaForm = $("consulta-form");
let medicosCache = [];
let filaCache = [];
let agendamentosMedicosCache = [];
const medicosAgendamentoIds = new Set();
const pacientesAtendidosNaSessao = new Set();
const nomesPacientesCache = new Map();
let ultimoMotivoFilaPreenchido = "";
let timerBuscaPacienteId = null;
let prontuarioMedicoEventosCache = [];
let prontuarioMedicoPacienteIdAtual = null;

function normalizarItemAgendamentoParaFilaMedica(ag) {
  return {
    id: ag.id,
    agendamento_id: ag.id,
    modalidade: "agendamento",
    paciente_id: ag.paciente_id,
    paciente_nome: ag.paciente_nome,
    paciente_idade: ag.paciente_idade ?? null,
    paciente_condicao_cronica: ag.paciente_condicao_cronica || null,
    paciente_gestante: ag.paciente_gestante ?? null,
    triagem_id: ag.triagem_id || null,
    urgencia: ag.urgencia || (ag.recomenda_urgencia ? "alta" : "baixa"),
    especialidade: ag.medico_especialidade || "clinica_geral",
    motivo: ag.motivo,
    relato_paciente: ag.motivo,
    justificativa_ia:
      ag.justificativa_ia ||
      ag.justificativa_urgencia ||
      "Consulta agendada com prioridade fixa por condições do paciente.",
    status: ag.status || "agendado",
    score: typeof ag.prioridade === "number" ? ag.prioridade : Number(ag.prioridade || 0),
    data_agendamento: ag.data_agendamento || null,
    medico_id: ag.medico_id,
    medico_alocado: ag.medico_nome || `Médico #${ag.medico_id}`,
    criado_em: ag.criado_em,
  };
}

function criarItemMetadadoProntuario(rotulo, valor) {
  const box = element("div", undefined, "prontuario-meta-item");
  box.append(
    element("span", rotulo),
    element("strong", valor || "Não informado"),
  );
  return box;
}

function ocultarProntuarioEvolutivoMedico() {
  const secao = $("prontuario-evolutivo");
  if (!secao) return;
  secao.hidden = true;
  prontuarioMedicoEventosCache = [];
  prontuarioMedicoPacienteIdAtual = null;
  $("prontuario-dados-cadastrais")?.replaceChildren();
  $("prontuario-motivo-atual")?.replaceChildren();
  $("prontuario-historico-lista")?.replaceChildren();
}

function renderizarHistoricoProntuarioMedico() {
  const lista = $("prontuario-historico-lista");
  const contador = $("prontuario-historico-contador");
  if (!lista) return;

  const filtroTipo = $("prontuario-filtro-tipo")?.value || "";
  const eventosOrdenados = [...prontuarioMedicoEventosCache]
    .filter((ev) => !filtroTipo || ev.tipo_evento === filtroTipo)
    .sort((a, b) => new Date(b.criado_em || 0) - new Date(a.criado_em || 0));

  lista.replaceChildren();

  if (contador) {
    contador.textContent = `${eventosOrdenados.length} registro(s) no histórico clínico (triagens e consultas, inclusive com outros médicos).`;
  }

  if (!eventosOrdenados.length) {
    const itemVazio = element("li");
    itemVazio.append(
      element("strong", "Nenhum registro encontrado para este filtro"),
      element(
        "p",
        "As triagens e consultas anteriores do paciente aparecerão nesta linha do tempo.",
      ),
    );
    lista.append(itemVazio);
    return;
  }

  for (const item of eventosOrdenados) {
    const li = element("li");
    const isTriagem = item.tipo_evento === "triagem";
    const rotuloTipo = isTriagem
      ? "Triagem de sintomas"
      : "Consulta médica / atendimento";

    const cabecalhoItem = element("div", undefined, "prontuario-motivo-badges");
    cabecalhoItem.append(
      urgenciaBadge(item.urgencia || "baixa"),
      element("span", formatarEspecialidade(item.especialidade), "badge azul"),
      element("time", ` · ${date(item.criado_em)}`),
    );

    const tituloEvento = element(
      "h4",
      `${rotuloTipo} · ${formatarEspecialidade(item.especialidade)}`,
    );
    const descricaoEvento = element(
      "p",
      isTriagem
        ? `Relato do paciente: ${item.descricao || "Não informado"}`
        : item.descricao || "Registro clínico de consulta.",
    );

    li.append(cabecalhoItem, tituloEvento, descricaoEvento);

    if (item.justificativa) {
      li.append(
        element("p", `Justificativa da IA: ${item.justificativa}`, "hint"),
      );
    }

    lista.append(li);
  }
}

async function carregarProntuarioEvolutivoMedico(pacienteId, itemDaFila = null) {
  const secao = $("prontuario-evolutivo");
  const boxCadastrais = $("prontuario-dados-cadastrais");
  const boxMotivo = $("prontuario-motivo-atual");
  const linkHistorico = $("prontuario-link-historico");

  if (!secao || !boxCadastrais || !boxMotivo) return;

  const idLimpo = String(pacienteId || "").trim();
  if (!/^[1-9]\d*$/.test(idLimpo)) {
    ocultarProntuarioEvolutivoMedico();
    return;
  }

  prontuarioMedicoPacienteIdAtual = idLimpo;
  if (linkHistorico) {
    linkHistorico.href = `/pages/historico.html?paciente=${encodeURIComponent(idLimpo)}`;
  }

  let dadosHistorico = null;
  try {
    dadosHistorico = await api(`/pacientes/${encodeURIComponent(idLimpo)}/historico`);
  } catch {
    dadosHistorico = null;
  }

  // Evita condição de corrida caso o médico tenha trocado de paciente enquanto a requisição carregava
  if (prontuarioMedicoPacienteIdAtual !== idLimpo) return;

  if (!dadosHistorico && !itemDaFila) {
    ocultarProntuarioEvolutivoMedico();
    return;
  }

  const nomePaciente =
    dadosHistorico?.nome ||
    itemDaFila?.paciente_nome ||
    nomesPacientesCache.get(Number(idLimpo)) ||
    `Paciente #${idLimpo}`;
  if (dadosHistorico?.nome) {
    nomesPacientesCache.set(Number(idLimpo), dadosHistorico.nome);
  }

  const idadeVal =
    dadosHistorico?.idade ?? itemDaFila?.paciente_idade ?? null;
  const textoIdade =
    idadeVal != null && idadeVal !== "" ? `${idadeVal} anos` : "Não informada";

  const condicaoCronicaVal =
    dadosHistorico?.condicao_cronica ||
    itemDaFila?.paciente_condicao_cronica ||
    null;
  const textoCondicoes = condicaoCronicaVal
    ? String(condicaoCronicaVal)
    : "Nenhuma condição crônica informada";

  const eventos = Array.isArray(dadosHistorico?.eventos_historico)
    ? dadosHistorico.eventos_historico
    : [];
  prontuarioMedicoEventosCache = eventos;

  // Identifica a triagem correspondente ao item da fila (ou a mais recente do histórico)
  const triagensHistorico = eventos
    .filter((e) => e.tipo_evento === "triagem")
    .sort((a, b) => new Date(b.criado_em || 0) - new Date(a.criado_em || 0));

  const triagemVinculada =
    (itemDaFila?.triagem_id &&
      triagensHistorico.find(
        (t) => Number(t.id) === Number(itemDaFila.triagem_id),
      )) ||
    triagensHistorico[0] ||
    null;

  const relatoOriginalPaciente =
    itemDaFila?.relato_paciente ||
    triagemVinculada?.descricao ||
    itemDaFila?.motivo ||
    "Relato clínico registrado no encaminhamento.";

  const justificativaIa =
    itemDaFila?.justificativa_ia ||
    triagemVinculada?.justificativa ||
    itemDaFila?.motivo ||
    "Classificação realizada pelo motor de triagem.";

  const urgenciaAtual =
    itemDaFila?.urgencia || triagemVinculada?.urgencia || "baixa";
  const especialidadeAtual =
    itemDaFila?.especialidade ||
    triagemVinculada?.especialidade ||
    "clinica_geral";
  const scoreAtual =
    typeof itemDaFila?.score === "number"
      ? itemDaFila.score.toFixed(1)
      : itemDaFila?.score != null
        ? String(itemDaFila.score)
        : null;
  const medicoAlocado =
    itemDaFila?.medico_alocado || "Alocado para atendimento clínico";

  // 1. Preenche dados cadastrais do paciente (Nome, Idade, Condições Crônicas, Especialidade)
  boxCadastrais.replaceChildren(
    criarItemMetadadoProntuario("Paciente", `${nomePaciente} (#${idLimpo})`),
    criarItemMetadadoProntuario("Idade", textoIdade),
    criarItemMetadadoProntuario("Condições crônicas", textoCondicoes),
    criarItemMetadadoProntuario(
      "Especialidade / Alocação",
      `${formatarEspecialidade(especialidadeAtual)} · ${medicoAlocado}`,
    ),
  );

  // 2. Preenche o motivo da consulta ou consulta de urgência + justificativa da IA + score
  const badgesLinha = element("div", undefined, "prontuario-motivo-badges");
  badgesLinha.append(urgenciaBadge(urgenciaAtual));
  if (scoreAtual !== null) {
    badgesLinha.append(
      element("span", `Score ${scoreAtual}`, "queue-score"),
    );
  }
  if (itemDaFila?.status) {
    badgesLinha.append(
      element("span", `Status: ${itemDaFila.status}`, "badge azul"),
    );
  }

  const pRelato = element("p");
  pRelato.append(
    element("strong", "Motivo da consulta / relato do paciente: "),
    document.createTextNode(relatoOriginalPaciente),
  );

  const pJustificativa = element("p");
  pJustificativa.append(
    element("strong", "Justificativa da IA: "),
    document.createTextNode(justificativaIa),
  );

  boxMotivo.replaceChildren(badgesLinha, pRelato, pJustificativa);

  // 3. Renderiza a linha do tempo do histórico completo do paciente (inclusive com outros médicos)
  renderizarHistoricoProntuarioMedico();
  secao.hidden = false;
}

function formatarNomeMedico(medico) {
  if (!medico || !medico.nome) return "Médico não identificado";
  const nome = String(medico.nome).trim();
  const prefixado =
    /helena|ana|mariana|camila|z[eé]lia/i.test(nome) && !/^dra?\./i.test(nome)
      ? `Dra. ${nome}`
      : !/^dra?\./i.test(nome)
        ? `Dr(a). ${nome}`
        : nome;
  const esp = medico.especialidade
    ? ` — ${formatarEspecialidade(medico.especialidade)}`
    : "";
  const sufixoModalidade =
    medico.id && medicosAgendamentoIds.size > 0
      ? medicosAgendamentoIds.has(Number(medico.id))
        ? " (Consulta Agendada)"
        : " (Urgência)"
      : "";
  return `${prefixado}${esp}${sufixoModalidade}`;
}

function atualizarResumoPacienteSelecionado({ id, nome, motivo, bloqueado = false }) {
  const resumo = $("paciente-selecionado-resumo");
  if (!resumo) return;
  if (!id) {
    resumo.hidden = true;
    resumo.replaceChildren();
    return;
  }
  const nomeExibicao = nome ? `${nome} (#${id})` : `Paciente #${id}`;
  const prefixo = bloqueado ? "Atendimento bloqueado" : "Em atendimento";
  const titulo = element("strong", `${prefixo}: ${nomeExibicao}`);
  const detalheMotivo = element(
    "p",
    motivo
      ? motivo
      : "Paciente alocado na fila para atendimento clínico.",
  );
  resumo.replaceChildren(titulo, detalheMotivo);
  resumo.hidden = false;
}

function destacarCardDaFilaPorPaciente(pacienteId) {
  document.querySelectorAll("#fila-medica .queue-card").forEach((card) => {
    const btn = card.querySelector(".btn-atender");
    card.classList.toggle(
      "is-selected",
      Boolean(
        pacienteId &&
          btn &&
          String(btn.dataset.pacienteId) === String(pacienteId),
      ),
    );
  });
}

function validarAlocacaoPacienteParaMedico(pacienteId, medicoId) {
  const itensUrgencia = filaCache.filter(
    (i) => String(i.paciente_id) === String(pacienteId),
  );
  const itensAgendados = agendamentosMedicosCache
    .filter((a) => String(a.paciente_id) === String(pacienteId))
    .map(normalizarItemAgendamentoParaFilaMedica);

  const todosItensDoPaciente = [...itensUrgencia, ...itensAgendados];
  const medicoObj = medicosCache.find(
    (m) => String(m.id) === String(medicoId),
  );
  const nomeMedico = medicoObj
    ? formatarNomeMedico(medicoObj)
    : `Médico #${medicoId}`;

  if (!todosItensDoPaciente.length) {
    return {
      permitido: false,
      item: null,
      mensagem: `Não é permitido registrar consulta: o paciente #${pacienteId} ainda não realizou triagem e não está na fila de atendimento.`,
    };
  }

  if (medicoId) {
    const itemAlocado = todosItensDoPaciente.find(
      (i) =>
        String(i.medico_id) === String(medicoId) &&
        (!medicoObj?.especialidade ||
          !i.especialidade ||
          String(i.especialidade).toLowerCase() ===
            String(medicoObj.especialidade).toLowerCase()),
    );
    if (!itemAlocado) {
      const itemRef = todosItensDoPaciente[0];
      const espDirecionada = formatarEspecialidade(itemRef.especialidade);
      const medAlocado =
        itemRef.medico_alocado || "outro profissional da especialidade";
      return {
        permitido: false,
        item: itemRef,
        mensagem: `Não é permitido registrar consulta: o paciente #${pacienteId} (${itemRef.paciente_nome || "triado"}) foi direcionado para ${espDirecionada} (${medAlocado}) e não está alocado para ${nomeMedico}.`,
      };
    }
    return { permitido: true, item: itemAlocado, mensagem: "" };
  }

  return { permitido: true, item: todosItensDoPaciente[0], mensagem: "" };
}

function limparAnamneseAutomatica(inputAnamnese) {
  if (
    inputAnamnese &&
    ultimoMotivoFilaPreenchido &&
    inputAnamnese.value === ultimoMotivoFilaPreenchido
  ) {
    inputAnamnese.value = "";
    ultimoMotivoFilaPreenchido = "";
  }
}

function resetarFormularioClinicoConsulta({ limparPacienteId = false } = {}) {
  if (limparPacienteId && $("paciente-id")) {
    $("paciente-id").value = "";
  }
  if ($("anamnese")) $("anamnese").value = "";
  if ($("diagnostico")) {
    $("diagnostico").value = "";
    $("diagnostico").removeAttribute("aria-invalid");
  }
  if ($("conduta")) {
    $("conduta").value = "";
    $("conduta").removeAttribute("aria-invalid");
  }
  ultimoMotivoFilaPreenchido = "";
  atualizarResumoPacienteSelecionado({ id: null });
  ocultarProntuarioEvolutivoMedico();
}

async function sincronizarPacientePorId(
  rawId,
  { veioDaFila = false, nomeFila = null, motivoFila = null } = {},
) {
  const idLimpo = String(rawId || "").trim();
  const inputAnamnese = $("anamnese");
  const medicoAtualId = $("medico-id")?.value?.trim() || "";

  destacarCardDaFilaPorPaciente(idLimpo);

  if (!/^[1-9]\d*$/.test(idLimpo)) {
    atualizarResumoPacienteSelecionado({ id: null });
    ocultarProntuarioEvolutivoMedico();
    limparAnamneseAutomatica(inputAnamnese);
    return;
  }

  const validacao = validarAlocacaoPacienteParaMedico(idLimpo, medicoAtualId);
  const itemDaFila = validacao.item;
  const nomeConhecido =
    (veioDaFila && nomeFila) ||
    itemDaFila?.paciente_nome ||
    nomesPacientesCache.get(Number(idLimpo)) ||
    null;

  if (nomeConhecido) {
    nomesPacientesCache.set(Number(idLimpo), nomeConhecido);
  }

  if (!validacao.permitido) {
    limparAnamneseAutomatica(inputAnamnese);
    ocultarProntuarioEvolutivoMedico();
    atualizarResumoPacienteSelecionado({
      id: idLimpo,
      nome: nomeConhecido,
      motivo: validacao.mensagem,
      bloqueado: true,
    });
    return;
  }

  patientSession.set(idLimpo);
  const motivoConhecido = veioDaFila
    ? motivoFila
    : itemDaFila?.motivo || null;

  // Se a anamnese tinha sido preenchida automaticamente por outro paciente da fila,
  // atualiza ou limpa para nunca misturar dados de pacientes diferentes.
  if (inputAnamnese) {
    const valorAtualAnamnese = inputAnamnese.value.trim();
    if (
      !valorAtualAnamnese ||
      inputAnamnese.value === ultimoMotivoFilaPreenchido
    ) {
      inputAnamnese.value = motivoConhecido || "";
      ultimoMotivoFilaPreenchido = motivoConhecido || "";
    }
  }

  atualizarResumoPacienteSelecionado({
    id: idLimpo,
    nome: nomeConhecido,
    motivo: motivoConhecido
      ? `Motivo / observação da triagem: ${motivoConhecido}`
      : "Paciente alocado para este médico na fila priorizada.",
    bloqueado: false,
  });

  await carregarProntuarioEvolutivoMedico(idLimpo, itemDaFila);
}

function selecionarPacienteDaFila({ pacienteId, medicoId, pacienteNome, motivo }) {
  const inputPaciente = $("paciente-id");
  const selectMedico = $("medico-id");
  const inputDiagnostico = $("diagnostico");
  const feedbackNode = $("consulta-feedback") || $("feedback");

  if (inputPaciente && pacienteId) {
    inputPaciente.value = String(pacienteId);
    inputPaciente.removeAttribute("aria-invalid");
  }

  if (selectMedico && medicoId) {
    const optionExists = Array.from(selectMedico.options).some(
      (opt) => opt.value === String(medicoId),
    );
    if (optionExists) {
      selectMedico.value = String(medicoId);
      selectMedico.removeAttribute("aria-invalid");
    }
    sincronizarModalidadeComMedicoSelecionado(medicoId);
  }

  sincronizarPacientePorId(pacienteId, {
    veioDaFila: true,
    nomeFila: pacienteNome,
    motivoFila: motivo,
  });

  const labelPaciente = pacienteNome
    ? `${pacienteNome} (#${pacienteId})`
    : `#${pacienteId}`;
  const msg = `Paciente ${labelPaciente} selecionado para atendimento. Preencha o diagnóstico e a conduta.`;
  setFeedback(feedbackNode, msg, "info");
  Feedback.info(msg);

  if (inputDiagnostico) {
    inputDiagnostico.focus();
  }
}

async function carregarMedicos() {
  const selectMedico = $("medico-id");
  const filtroFila = $("filtro-medico-fila");
  if (!selectMedico && !filtroFila) return [];

  try {
    const [medicos, medicosAgendamento] = await Promise.all([
      api("/medicos"),
      api("/agendamentos/medicos").catch(() => []),
    ]);
    medicosCache = Array.isArray(medicos) ? medicos : [];
    medicosAgendamentoIds.clear();
    if (Array.isArray(medicosAgendamento)) {
      for (const mAg of medicosAgendamento) {
        if (mAg && mAg.id != null) {
          medicosAgendamentoIds.add(Number(mAg.id));
        }
      }
    }

    const ativos = medicosCache.filter((m) => m.ativo !== false);
    const listaParaSelect = ativos.length > 0 ? ativos : medicosCache;

    // Popula o select #medico-id do formulário de consulta
    if (selectMedico) {
      const valorAtual = selectMedico.value;
      selectMedico.replaceChildren();

      if (!listaParaSelect.length) {
        const optVazio = element(
          "option",
          "Nenhum médico cadastrado — execute o seed",
        );
        optVazio.value = "";
        selectMedico.append(optVazio);
      } else {
        for (const medico of listaParaSelect) {
          const opt = element("option", formatarNomeMedico(medico));
          opt.value = String(medico.id);
          selectMedico.append(opt);
        }

        // Pré-seleciona Dra. Helena se existir, ou o primeiro médico ativo
        const draHelena =
          listaParaSelect.find((m) => /helena/i.test(m.nome)) ||
          listaParaSelect[0];
        if (
          valorAtual &&
          listaParaSelect.some((m) => String(m.id) === valorAtual)
        ) {
          selectMedico.value = valorAtual;
        } else if (draHelena) {
          selectMedico.value = String(draHelena.id);
        }
      }
    }

    // Popula o select de filtro da fila (#filtro-medico-fila)
    if (filtroFila) {
      const filtroAtual = filtroFila.value;
      filtroFila.replaceChildren();
      const optTodos = element("option", "Todos os pacientes aguardando na fila");
      optTodos.value = "";
      filtroFila.append(optTodos);

      for (const medico of listaParaSelect) {
        const opt = element("option", formatarNomeMedico(medico));
        opt.value = String(medico.id);
        filtroFila.append(opt);
      }

      const optSemVaga = element("option", "Aguardando vaga na especialidade");
      optSemVaga.value = "sem_medico";
      filtroFila.append(optSemVaga);

      if (filtroAtual) {
        filtroFila.value = filtroAtual;
      }
    }

    return medicosCache;
  } catch (error) {
    setFeedback(
      $("consulta-feedback") || $("feedback"),
      error.message,
      "error",
    );
    return [];
  }
}

function obterItensAtivosDaModalidadeAtual() {
  const modalidade = $("filtro-modalidade-fila")?.value || "urgencia";
  if (modalidade === "agendamento") {
    return agendamentosMedicosCache.map(normalizarItemAgendamentoParaFilaMedica);
  }
  return filaCache;
}

function renderizarFilaMedica(itens = null) {
  const container = $("fila-medica");
  if (!container) return;

  const modalidade = $("filtro-modalidade-fila")?.value || "urgencia";
  const listaBase = Array.isArray(itens)
    ? itens
    : obterItensAtivosDaModalidadeAtual();

  const filtroMedicoVal = $("filtro-medico-fila")?.value || "";
  const itensFiltrados = listaBase.filter((item) => {
    if (!filtroMedicoVal) return true;
    if (filtroMedicoVal === "sem_medico") return item.medico_id == null;
    return String(item.medico_id) === String(filtroMedicoVal);
  });

  container.replaceChildren();
  const filaVaziaEl = $("fila-vazia");
  if (filaVaziaEl) {
    filaVaziaEl.hidden = itensFiltrados.length > 0;
  }

  if ($("fila-contador")) {
    $("fila-contador").textContent = `${itensFiltrados.length} paciente(s) na fila`;
  }

  if (!itensFiltrados.length) {
    const emptyBox = element("div", undefined, "empty queue-empty");
    emptyBox.append(
      element("h3", "Nenhum paciente aguardando neste filtro"),
      element(
        "p",
        listaBase.length
          ? "Altere o filtro de médico ou a modalidade para visualizar outros pacientes."
          : modalidade === "agendamento"
            ? "As consultas agendadas aparecerão aqui ordenadas pela prioridade fixa do paciente."
            : "Assim que novas triagens forem concluídas, os pacientes aparecerão aqui por ordem de prioridade.",
      ),
    );
    container.append(emptyBox);
    return;
  }

  itensFiltrados.forEach((item, index) => {
    const posicao = `${index + 1}º`;
    const nomePaciente =
      item.paciente_nome || `Paciente #${item.paciente_id}`;
    const scoreFormatado =
      typeof item.score === "number" ? item.score.toFixed(1) : String(item.score ?? 0);
    const motivoTexto =
      item.motivo || "Relato clínico registrado na triagem.";
    const medicoAlocado =
      item.medico_alocado || "Aguardando vaga na especialidade";
    const urgKey = String(item.urgencia || "baixa").toLowerCase().trim();
    const jaAtendido = pacientesAtendidosNaSessao.has(Number(item.paciente_id));

    const tagCard = container.tagName === "OL" || container.tagName === "UL" ? "li" : "article";
    const card = element(tagCard, undefined, `queue-card ${urgKey}`.trim());
    card.setAttribute(
      "aria-label",
      `${posicao} da fila: ${nomePaciente}, ID ${item.paciente_id}`,
    );

    const header = element("div", undefined, "queue-card-header");
    const posBadge = element("span", `${posicao} · Score ${scoreFormatado}`, "queue-score");
    const seloUrgencia = urgenciaBadge(item.urgencia || "baixa");
    header.append(posBadge, seloUrgencia);
    if (item.modalidade === "agendamento" && item.data_agendamento) {
      header.append(
        element("span", `Agendado: ${item.data_agendamento}`, "badge azul"),
      );
    }
    if (jaAtendido) {
      header.append(element("span", "Atendido nesta sessão ✓", "badge verde"));
    }

    const titulo = element(
      "h3",
      `${posicao} · ${nomePaciente} (#${item.paciente_id})`,
    );

    const partesPerfil = [];
    if (item.paciente_idade != null) {
      partesPerfil.push(`Idade: ${item.paciente_idade} anos`);
    }
    if (item.paciente_condicao_cronica) {
      partesPerfil.push(`Condições crônicas: ${item.paciente_condicao_cronica}`);
    }

    const meta = element(
      "p",
      `Especialidade: ${formatarEspecialidade(item.especialidade)} · Médico alocado: ${medicoAlocado}${partesPerfil.length ? ` · ${partesPerfil.join(" · ")}` : ""}`,
      "queue-meta",
    );

    const relatoCardTexto = item.relato_paciente || motivoTexto;
    const motivoEl = element(
      "p",
      `Motivo / relato do paciente: ${relatoCardTexto}`,
      "queue-motivo",
    );

    const elementosCard = [header, titulo, meta, motivoEl];
    if (item.justificativa_ia && item.justificativa_ia !== relatoCardTexto) {
      elementosCard.push(
        element(
          "p",
          `Justificativa da IA: ${item.justificativa_ia}`,
          "queue-meta",
        ),
      );
    }

    const btnAtender = element(
      "button",
      "Selecionar paciente",
      "btn btn-primary btn-atender",
    );
    btnAtender.type = "button";
    btnAtender.dataset.pacienteId = String(item.paciente_id);
    btnAtender.dataset.medicoId = item.medico_id != null ? String(item.medico_id) : "";
    btnAtender.dataset.pacienteNome = nomePaciente;
    btnAtender.dataset.motivo = relatoCardTexto;
    btnAtender.addEventListener("click", () => {
      selecionarPacienteDaFila({
        pacienteId: item.paciente_id,
        medicoId: item.medico_id,
        pacienteNome: nomePaciente,
        motivo: relatoCardTexto,
      });
    });

    elementosCard.push(btnAtender);
    card.append(...elementosCard);
    container.append(card);
  });

  destacarCardDaFilaPorPaciente($("paciente-id")?.value?.trim());
}

async function carregarAgendamentosMedicos() {
  try {
    const agendamentos = await api("/agendamentos?status=agendado");
    agendamentosMedicosCache = Array.isArray(agendamentos) ? agendamentos : [];
    for (const ag of agendamentosMedicosCache) {
      if (ag.paciente_id && ag.paciente_nome) {
        nomesPacientesCache.set(Number(ag.paciente_id), ag.paciente_nome);
      }
    }
    return agendamentosMedicosCache;
  } catch {
    agendamentosMedicosCache = [];
    return [];
  }
}

async function carregarFilaMedica() {
  const container = $("fila-medica");
  if (!container) return [];

  container.setAttribute("aria-busy", "true");
  try {
    const [itens] = await Promise.all([
      api("/fila?status=aguardando"),
      carregarAgendamentosMedicos(),
    ]);
    filaCache = Array.isArray(itens) ? itens : [];
    for (const item of filaCache) {
      if (item.paciente_id && item.paciente_nome) {
        nomesPacientesCache.set(Number(item.paciente_id), item.paciente_nome);
      }
    }
    renderizarFilaMedica();

    // Sincroniza sempre o resumo com o ID atualmente preenchido no input #paciente-id
    const idAtual = $("paciente-id")?.value?.trim();
    if (idAtual) {
      await sincronizarPacientePorId(idAtual);
    } else {
      atualizarResumoPacienteSelecionado({ id: null });
    }

    return filaCache;
  } catch (error) {
    setFeedback(
      $("consulta-feedback") || $("feedback"),
      error.message,
      "error",
    );
    return [];
  } finally {
    container.removeAttribute("aria-busy");
  }
}

function sincronizarModalidadeComMedicoSelecionado(medicoId) {
  const selectModalidade = $("filtro-modalidade-fila");
  if (!selectModalidade || !medicoId || medicoId === "sem_medico") return;
  if (medicosAgendamentoIds.size === 0) return;

  const isMedicoAgendamento = medicosAgendamentoIds.has(Number(medicoId));
  selectModalidade.value = isMedicoAgendamento ? "agendamento" : "urgencia";
}

$("atualizar-fila")?.addEventListener("click", () => {
  carregarFilaMedica();
});

$("filtro-modalidade-fila")?.addEventListener("change", (e) => {
  const novaModalidade = e.currentTarget.value;
  const filtroMedico = $("filtro-medico-fila");
  if (
    filtroMedico &&
    filtroMedico.value &&
    filtroMedico.value !== "sem_medico" &&
    medicosAgendamentoIds.size > 0
  ) {
    const isMedicoAg = medicosAgendamentoIds.has(Number(filtroMedico.value));
    const modalidadeMedicoFiltro = isMedicoAg ? "agendamento" : "urgencia";
    if (modalidadeMedicoFiltro !== novaModalidade) {
      filtroMedico.value = "";
    }
  }
  renderizarFilaMedica();
});

$("filtro-medico-fila")?.addEventListener("change", (e) => {
  sincronizarModalidadeComMedicoSelecionado(e.currentTarget.value);
  renderizarFilaMedica();
});

$("medico-id")?.addEventListener("change", (e) => {
  $("medico-id").removeAttribute("aria-invalid");
  const medicoIdVal = e.currentTarget.value;
  sincronizarModalidadeComMedicoSelecionado(medicoIdVal);
  if ($("filtro-medico-fila") && $("filtro-medico-fila").value) {
    $("filtro-medico-fila").value = medicoIdVal;
  }
  renderizarFilaMedica();
  const idAtual = $("paciente-id")?.value?.trim();
  if (idAtual) {
    sincronizarPacientePorId(idAtual);
  }
});

$("prontuario-filtro-tipo")?.addEventListener("change", () => {
  renderizarHistoricoProntuarioMedico();
});

$("limpar-consulta")?.addEventListener("click", () => {
  resetarFormularioClinicoConsulta({ limparPacienteId: false });
  destacarCardDaFilaPorPaciente("");
  setFeedback($("consulta-feedback") || $("feedback"), "", "info");
});

// Limpa o estado aria-invalid assim que o médico edita um campo obrigatório
["paciente-id", "medico-id", "diagnostico", "conduta"].forEach((fieldId) => {
  $(fieldId)?.addEventListener("input", (e) => {
    e.currentTarget.removeAttribute("aria-invalid");
  });
});

if (consultaForm) {
  const inputPacientePainel = $("paciente-id");
  inputPacientePainel?.addEventListener("input", (e) => {
    const novoValor = e.currentTarget.value.trim();
    clearTimeout(timerBuscaPacienteId);
    timerBuscaPacienteId = setTimeout(() => {
      sincronizarPacientePorId(novoValor);
    }, 200);
  });
  inputPacientePainel?.addEventListener("change", (e) => {
    clearTimeout(timerBuscaPacienteId);
    sincronizarPacientePorId(e.currentTarget.value.trim());
  });

  // Inicializa médicos e fila priorizada ao abrir medico.html
  Promise.all([carregarMedicos(), carregarFilaMedica()]);

  consultaForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const feedbackNode = $("consulta-feedback") || $("feedback");
    const resultadoBox = $("consulta-resultado");
    const inputPaciente = form.elements.paciente_id || $("paciente-id");
    const selectMedico = form.elements.medico_id || $("medico-id");
    const inputAnamnese = form.elements.anamnese || $("anamnese");
    const inputDiagnostico = form.elements.diagnostico || $("diagnostico");
    const inputConduta = form.elements.conduta || $("conduta");

    const pacienteVal = inputPaciente ? String(inputPaciente.value).trim() : "";
    const medicoVal = selectMedico ? String(selectMedico.value).trim() : "";
    const anamneseVal = inputAnamnese ? String(inputAnamnese.value).trim() : "";
    const diagnosticoVal = inputDiagnostico ? String(inputDiagnostico.value).trim() : "";
    const condutaVal = inputConduta ? String(inputConduta.value).trim() : "";

    // Validação acessível de campos obrigatórios antes do envio
    const validacoes = [
      {
        valido: /^[1-9]\d*$/.test(pacienteVal) && Number(pacienteVal) >= 1,
        campo: inputPaciente,
        mensagem: "Informe o número válido do paciente para registrar a consulta.",
      },
      {
        valido: /^[1-9]\d*$/.test(medicoVal) && Number(medicoVal) >= 1,
        campo: selectMedico,
        mensagem: "Selecione o médico responsável pelo atendimento.",
      },
      {
        valido: diagnosticoVal.length > 0,
        campo: inputDiagnostico,
        mensagem: "Preencha o diagnóstico clínico antes de salvar a consulta.",
      },
      {
        valido: condutaVal.length > 0,
        campo: inputConduta,
        mensagem: "Preencha a conduta terapêutica antes de salvar a consulta.",
      },
    ];

    const erroValidacao = validacoes.find((item) => !item.valido);
    if (erroValidacao) {
      if (erroValidacao.campo) {
        erroValidacao.campo.setAttribute("aria-invalid", "true");
        erroValidacao.campo.focus();
      }
      setFeedback(feedbackNode, erroValidacao.mensagem, "error");
      Feedback.erro(erroValidacao.mensagem);
      return;
    }

    // Garante que a fila está atualizada e valida se o paciente realizou triagem
    // e foi direcionado/alocado para o médico e especialidade selecionados.
    await carregarFilaMedica();
    const validacaoAlocacao = validarAlocacaoPacienteParaMedico(
      pacienteVal,
      medicoVal,
    );
    if (!validacaoAlocacao.permitido) {
      if (inputPaciente) {
        inputPaciente.setAttribute("aria-invalid", "true");
        inputPaciente.focus();
      }
      setFeedback(feedbackNode, validacaoAlocacao.mensagem, "error");
      Feedback.erro(validacaoAlocacao.mensagem);
      return;
    }

    const submitButton = form.querySelector('[type="submit"]');
    if (submitButton && submitButton.disabled) return;
    if (submitButton) submitButton.disabled = true;
    form.setAttribute("aria-busy", "true");
    setFeedback(feedbackNode, "", "info");
    if (resultadoBox) resultadoBox.hidden = true;

    const fecharLoading = Feedback.carregando(
      "Registrando consulta médica no prontuário...",
    );

    try {
      const payload = {
        paciente_id: Number(pacienteVal),
        medico_id: Number(medicoVal),
        anamnese: anamneseVal || null,
        diagnostico: diagnosticoVal,
        conduta: condutaVal,
      };

      const data = await api("/consultas", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      patientSession.set(String(data.paciente_id));
      pacientesAtendidosNaSessao.add(Number(data.paciente_id));
      ultimoMotivoFilaPreenchido = "";

      let nomeRealPaciente =
        nomesPacientesCache.get(Number(data.paciente_id)) ||
        filaCache.find((i) => Number(i.paciente_id) === Number(data.paciente_id))
          ?.paciente_nome ||
        null;

      if (!nomeRealPaciente) {
        try {
          const histPac = await api(`/pacientes/${data.paciente_id}/historico`);
          if (histPac?.nome) {
            nomeRealPaciente = histPac.nome;
            nomesPacientesCache.set(Number(data.paciente_id), histPac.nome);
          }
        } catch {
          /* Fallback para Paciente #ID */
        }
      }

      const msgSucesso =
        "Consulta registrada com sucesso! O atendimento já consta no histórico do paciente.";
      setFeedback(feedbackNode, msgSucesso, "success");
      Feedback.sucesso(msgSucesso);

      if (resultadoBox) {
        const medicoObj = medicosCache.find(
          (m) => Number(m.id) === Number(data.medico_id),
        );
        const nomePaciente = nomeRealPaciente
          ? `${nomeRealPaciente} (#${data.paciente_id})`
          : `Paciente #${data.paciente_id}`;
        const nomeMedico = medicoObj
          ? `${formatarNomeMedico(medicoObj)} (#${data.medico_id})`
          : `Médico #${data.medico_id}`;

        const titulo = element(
          "h2",
          `Consulta #${data.id} registrada no prontuário`,
        );
        const pPaciente = element("p", `Paciente: ${nomePaciente}`);
        const pMedico = element("p", `Médico: ${nomeMedico}`);
        const pDiagnostico = element("p", `Diagnóstico: ${data.diagnostico}`);
        const pConduta = element("p", `Conduta: ${data.conduta}`);
        const pData = element(
          "p",
          `Data/Hora: ${date(data.criado_em)}`,
          "hint",
        );

        const linkHistorico = element(
          "a",
          "Ver imediatamente no histórico do paciente",
          "btn button secondary",
        );
        linkHistorico.href = `/pages/historico.html?paciente=${encodeURIComponent(data.paciente_id)}`;

        resultadoBox.replaceChildren(
          element("span", "Atendimento concluído", "badge verde"),
          titulo,
          pPaciente,
          pMedico,
          ...(data.anamnese
            ? [element("p", `Anamnese: ${data.anamnese}`)]
            : []),
          pDiagnostico,
          pConduta,
          pData,
          linkHistorico,
        );
        resultadoBox.hidden = false;
        if (resultadoBox.tabIndex < 0) resultadoBox.tabIndex = -1;
        resultadoBox.focus();
      }

      // Limpa os campos clínicos e o ID do paciente atendido (que saiu da fila)
      resetarFormularioClinicoConsulta({ limparPacienteId: true });

      await carregarFilaMedica();
    } catch (error) {
      setFeedback(feedbackNode, error.message, "error");
      Feedback.erro(error.message);
    } finally {
      fecharLoading();
      if (submitButton) submitButton.disabled = false;
      form.removeAttribute("aria-busy");
    }
  });
}
