// true = usa os dados de exemplo abaixo; false = busca GET /pacientes/{id}/historico (issue #18).
const USAR_DADOS_EXEMPLO = true;
const API = window.location.origin;
const ID_PACIENTE = new URLSearchParams(location.search).get("paciente") || "1";

// Formato do HistoricoUnificadoResposta (app/schemas.py).
const DADOS_EXEMPLO = {
  nome: "Raimundo Nonato", email: "raimundo@exemplo.com", idade: 65,
  condicao_cronica: "cardiopatia", criado_em: "2026-10-01T10:00:00",
  eventos_historico: [
    { id: 3, paciente_id: 1, tipo_evento: "triagem", descricao: "Dor no peito e falta de ar",
      urgencia: "emergencia", especialidade: "cardiologia",
      justificativa: "Classificado como emergencia por mencionar: dor no peito e falta de ar",
      criado_em: "2026-10-14T21:30:00" },
    { id: 2, paciente_id: 1, tipo_evento: "atendimento", descricao: "Consulta de rotina",
      urgencia: "baixa", especialidade: "clinica_geral", justificativa: null,
      criado_em: "2026-10-05T09:00:00" },
    { id: 1, paciente_id: 1, tipo_evento: "triagem", descricao: "Febre há dois dias",
      urgencia: "alta", especialidade: "clinica_geral", justificativa: "",
      criado_em: "2026-10-02T15:10:00" }
  ]
};

const $ = (id) => document.getElementById(id);
const ROTULO_URGENCIA = { emergencia: "Emergência", alta: "Urgência alta", media: "Urgência média", baixa: "Urgência baixa" };

function semUnderscore(t) { return String(t || "").replace(/_/g, " "); }

function formatarData(iso) {
  // criado_em vem em UTC sem "Z" (datetime.now(timezone.utc) no SQLite); trata como UTC.
  const d = new Date(/(Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : iso + "Z");
  if (isNaN(d)) return "Data não informada";
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function aviso(texto, erro) {
  const a = $("aviso");
  a.textContent = texto; a.hidden = !texto; a.className = erro ? "erro" : "";
}

function criar(tag, classe, texto) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texto !== undefined) e.textContent = texto; // textContent evita injeção de HTML
  return e;
}

function renderizar(eventos) {
  const ol = $("linha"); ol.replaceChildren();
  const ordenados = [...eventos].sort((a, b) => new Date(b.criado_em) - new Date(a.criado_em));
  for (const ev of ordenados) {
    const li = criar("li");
    li.append(criar("p", "data", formatarData(ev.criado_em)));
    li.append(criar("p", "tipo", semUnderscore(ev.tipo_evento)));
    li.append(criar("p", "desc", ev.descricao));
    const p = criar("p");
    p.append(criar("span", "selo " + ev.urgencia, ROTULO_URGENCIA[ev.urgencia] || semUnderscore(ev.urgencia)));
    p.append(document.createTextNode("Especialidade: " + semUnderscore(ev.especialidade)));
    li.append(p);
    if (ev.justificativa && ev.justificativa.trim()) li.append(criar("p", "just", ev.justificativa));
    ol.append(li);
  }
}

async function carregar() {
  $("linha").replaceChildren();
  aviso("Carregando seu histórico…", false);
  try {
    let dados;
    if (USAR_DADOS_EXEMPLO) dados = DADOS_EXEMPLO;
    else {
      const r = await fetch(API + "/pacientes/" + encodeURIComponent(ID_PACIENTE) + "/historico");
      if (!r.ok) throw new Error("status " + r.status);
      dados = await r.json();
    }
    const eventos = Array.isArray(dados.eventos_historico) ? dados.eventos_historico : [];
    if (dados.nome) $("paciente").textContent = dados.nome + " — da mais recente para a mais antiga.";
    if (!eventos.length) { aviso("Você ainda não tem registros no histórico.", false); return; }
    aviso("", false);
    renderizar(eventos);
  } catch (e) {
    aviso("Não foi possível carregar seu histórico. Tente novamente em instantes.", true);
  }
}

$("recarregar").addEventListener("click", carregar);
carregar();