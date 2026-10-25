// Componentes de feedback visual (issue #20).
//   Feedback.carregando("Carregando seus dados…")  -> abre o modal; devolve função que o fecha
//   Feedback.sucesso("Registro salvo com sucesso") -> banner que some sozinho
//   Feedback.erro("Não foi possível salvar.")      -> banner que fica até o usuário fechar
//   Feedback.info("…")                             -> banner informativo
//   Feedback.comCarregamento(texto, promessa)      -> mostra o modal enquanto a promessa não termina
const Feedback = (() => {
  const ICONES = { sucesso: "✓", erro: "!", info: "i" };
  const TEMPO_MS = { sucesso: 5000, info: 5000, erro: 0 }; // 0 = não fecha sozinho
  let area = null, fundo = null, textoModal = null, abertos = 0, ultimoFoco = null;

  function el(tag, classe, texto) {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto; // textContent evita injeção de HTML
    return e;
  }

  function garantirArea() {
    if (area) return;
    area = el("div", "sv-banners");
    document.body.append(area);

    fundo = el("div", "sv-modal-fundo");
    fundo.hidden = true;
    const modal = el("div", "sv-modal");
    modal.setAttribute("role", "alertdialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-live", "assertive");
    modal.setAttribute("aria-busy", "true");
    modal.tabIndex = -1;
    textoModal = el("p");
    textoModal.style.margin = "0";
    modal.append(el("div", "sv-giro"), textoModal);
    modal.setAttribute("aria-labelledby", (textoModal.id = "sv-modal-texto"));
    fundo.append(modal);
    document.body.append(fundo);
  }

  function banner(tipo, texto) {
    garantirArea();
    const b = el("div", "sv-banner " + tipo);
    // erro avisa na hora (alert); os demais esperam o leitor de tela terminar (status).
    b.setAttribute("role", tipo === "erro" ? "alert" : "status");
    b.append(el("span", "sv-icone", ICONES[tipo]), el("span", "sv-texto", texto));
    const fechar = el("button", "", "Fechar");
    fechar.type = "button";
    fechar.addEventListener("click", () => b.remove());
    b.append(fechar);
    area.append(b);
    if (TEMPO_MS[tipo]) setTimeout(() => b.remove(), TEMPO_MS[tipo]);
    return () => b.remove();
  }

  // Aceita chamadas aninhadas: o modal só fecha quando todas terminarem.
  function carregando(texto = "Carregando seus dados…") {
    garantirArea();
    if (!abertos) {
      ultimoFoco = document.activeElement;
      fundo.hidden = false;
      fundo.firstChild.focus();
    }
    abertos++;
    textoModal.textContent = texto;
    let fechado = false;
    return () => {
      if (fechado) return;
      fechado = true;
      if (--abertos === 0) {
        fundo.hidden = true;
        if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
      }
    };
  }

  async function comCarregamento(texto, promessa) {
    const fechar = carregando(texto);
    try { return await promessa; } finally { fechar(); }
  }

  return {
    carregando, comCarregamento,
    sucesso: (t) => banner("sucesso", t),
    erro: (t) => banner("erro", t),
    info: (t) => banner("info", t),
  };
})();
