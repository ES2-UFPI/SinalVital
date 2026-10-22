

    (function () {
      // tamanhos de letra possiveis, do normal ate o bem grande
      var ESCALAS = [1, 1.125, 1.25, 1.5, 1.75];

      // pegamos os elementos uma vez so aqui no comeco pra nao ficar procurando toda hora
      var raiz = document.documentElement;
      var btnMais = document.getElementById('btn-aumentar');
      var btnMenos = document.getElementById('btn-diminuir');
      var btnContraste = document.getElementById('btn-contraste');
      var texto = document.getElementById('texto-relato');
      var avisos = document.getElementById('avisos');
      var chips = document.querySelectorAll('.chip');

      // le uma preferencia guardada no navegador. se nao tiver nada (ou o navegador
      // bloquear, como no modo privado), devolve o valor padrao e a vida segue
      function ler(chave, padrao) {
        try { var v = localStorage.getItem(chave); return v === null ? padrao : v; }
        catch (e) { return padrao; }
      }

      // guarda uma preferencia pra lembrar na proxima visita. se der erro, ignora
      // em silencio porque nao vale travar a pagina por causa disso
      function gravar(chave, valor) {
        try { localStorage.setItem(chave, valor); } catch (e) { /* sem problema */ }
      }

      // recupera o nivel de fonte salvo e confere se ele ainda faz sentido
      var indice = parseInt(ler('sv_fonte', '0'), 10);
      if (isNaN(indice) || indice < 0 || indice >= ESCALAS.length) indice = 0;

      // aplica o tamanho de letra escolhido: muda a escala da pagina, desliga o botao
      // que ja chegou no limite (diminuir no menor tamanho, aumentar no maior) e salva a escolha
      function aplicarFonte() {
        raiz.style.setProperty('--escala', ESCALAS[indice]);
        btnMenos.disabled = indice === 0;
        btnMais.disabled = indice === ESCALAS.length - 1;
        gravar('sv_fonte', String(indice));
      }

      // cada clique sobe ou desce um nivel, sem passar do limite
      btnMais.addEventListener('click', function () {
        if (indice < ESCALAS.length - 1) { indice++; aplicarFonte(); }
      });
      btnMenos.addEventListener('click', function () {
        if (indice > 0) { indice--; aplicarFonte(); }
      });
      aplicarFonte();

      // liga ou desliga o alto contraste. o css reage sozinho ao atributo no html,
      // e o aria pressed avisa o leitor de tela se o botao esta ativo
      function aplicarContraste(alto) {
        raiz.setAttribute('data-contraste', alto ? 'alto' : 'normal');
        btnContraste.setAttribute('aria-pressed', alto ? 'true' : 'false');
        gravar('sv_contraste', alto ? 'alto' : 'normal');
      }
      aplicarContraste(ler('sv_contraste', 'normal') === 'alto');
      btnContraste.addEventListener('click', function () {
        aplicarContraste(raiz.getAttribute('data-contraste') !== 'alto');
      });

      // quebra o texto do relato em uma lista de sintomas separados por virgula,
      // tirando espacos e pedacos vazios
      function sintomasAtuais() {
        return texto.value.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
      }

      // deixa os chips em sincronia com o que esta escrito no relato: se o sintoma
      // aparece no texto, o chip fica marcado, senao fica desmarcado. roda tanto
      // quando clicam num chip quanto quando a pessoa digita
      function sincronizarChips() {
        var lista = sintomasAtuais().map(function (s) { return s.toLowerCase(); });
        chips.forEach(function (chip) {
          var ativo = lista.indexOf(chip.dataset.sintoma.toLowerCase()) !== -1;
          chip.setAttribute('aria-pressed', ativo ? 'true' : 'false');
        });
      }

      // clicar num chip adiciona o sintoma no relato, e clicar de novo tira.
      // assim nao ha risco de repetir o mesmo sintoma duas vezes
      chips.forEach(function (chip) {
        chip.setAttribute('aria-pressed', 'false');
        chip.addEventListener('click', function () {
          var alvo = chip.dataset.sintoma;
          var lista = sintomasAtuais();
          var pos = lista.map(function (s) { return s.toLowerCase(); }).indexOf(alvo.toLowerCase());
          if (pos === -1) lista.push(alvo); else lista.splice(pos, 1);
          texto.value = lista.join(', ');
          sincronizarChips();
        });
      });
      texto.addEventListener('input', sincronizarChips);

      // botao limpar: apaga o relato e qualquer aviso na tela, desmarca os chips
      // e devolve o cursor pro campo de texto
      document.getElementById('btn-limpar').addEventListener('click', function () {
        texto.value = '';
        avisos.textContent = '';
        avisos.classList.remove('erro');
        sincronizarChips();
        texto.focus();
      });

      // o botao grande "relatar sintomas" rola suavemente ate o formulario e ja
      // coloca o cursor no campo de texto, pra pessoa poder comecar a escrever
      document.getElementById('ir-relato').addEventListener('click', function (ev) {
        ev.preventDefault();
        document.getElementById('relato').scrollIntoView({ behavior: 'smooth', block: 'start' });
        texto.focus();
      });

      // envio do relato. primeiro confere se tem alguma coisa escrita e, se nao tiver,
      // mostra um aviso em vermelho. se estiver ok, dispara o evento sinalvital:relato
      // com o texto e o id do paciente. quem for ligar isso na api (issue 12) so precisa
      // escutar esse evento e chamar o post de triagens
      document.getElementById('relato').addEventListener('submit', function (ev) {
        ev.preventDefault();
        var relato = texto.value.trim();
        if (!relato) {
          avisos.classList.add('erro');
          avisos.textContent = 'Escreva ou toque em pelo menos um sintoma antes de enviar.';
          texto.focus();
          return;
        }
        avisos.classList.remove('erro');
        avisos.textContent = 'Relato pronto para envio.';
        document.dispatchEvent(new CustomEvent('sinalvital:relato', { detail: { relato: relato, pacienteId: pacienteId } }));
      });

      // descobre qual paciente estamos mostrando pelo endereco (?paciente=2, por
      // exemplo) e usa o 1 se nao vier nada. o mesmo id vai no link do historico
      var params = new URLSearchParams(window.location.search);
      var pacienteId = parseInt(params.get('paciente') || '1', 10) || 1;
      document.getElementById('ir-historico').setAttribute('href', 'historico.html?paciente=' + pacienteId);

      // busca o nome do paciente na api pra trocar o "olá!" por "olá, nome!". se a
      // api nao responder (ou a pagina foi aberta direto do arquivo), fica o "olá!"
      fetch('/pacientes/' + pacienteId + '/historico')
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (dados) {
          if (dados && dados.nome) {
            document.getElementById('saudacao').textContent = 'Olá, ' + dados.nome.split(' ')[0] + '!';
          }
        })
        .catch(function () { /* sem api, mantem a saudacao simples */ });
    })();