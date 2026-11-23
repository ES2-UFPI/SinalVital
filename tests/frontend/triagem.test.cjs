const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

// Issue #70 ([005-08]): a triagem não coloca mais o paciente na fila sozinha. O resultado mostra
// a sugestão da IA e dois botões, e o POST /fila só acontece quando o paciente clica.

const TEXTO_FILA='Entrar na Fila de Atendimento de Urgência';
const TEXTO_AGENDAMENTO='Ir para Agendamento de Consulta';

function element(tag='div'){
  return {tag,children:[],events:{},hidden:false,value:'',disabled:false,
    classList:{toggle(){}},setAttribute(){},removeAttribute(){},focus(){},
    append(...children){this.children.push(...children);},
    replaceChildren(...children){this.children=children;},
    querySelector(){return null;},addEventListener(name,fn){this.events[name]=fn;}};
}
function todos(node){return [node,...(node.children||[]).flatMap(todos)];}
// app.js testa `instanceof HTMLElement`; no Node os elementos falsos precisam ser reconhecidos como tal.
class HTMLElement{static [Symbol.hasInstance](valor){return Boolean(valor)&&typeof valor==='object'&&Array.isArray(valor.children);}}

const TRIAGENS={
  emergencia:{id:7,urgencia:'emergencia',classificacao:'vermelho',especialidade:'cardiologia',
    justificativa:'Dor no peito exige atendimento imediato.',prioridade:1,sugestao_fluxo:'urgencia',
    recomendacao:'Procure atendimento de urgência imediatamente ou ligue para o SAMU (192).',criado_em:'2026-11-22T12:00:00Z'},
  alta:{id:8,urgencia:'alta',classificacao:'laranja',especialidade:'clinica_geral',
    justificativa:'Febre alta com vômitos.',prioridade:2,sugestao_fluxo:'urgencia',
    recomendacao:'Procure atendimento de urgência o quanto antes.',criado_em:'2026-11-22T12:00:00Z'},
  media:{id:9,urgencia:'media',classificacao:'amarelo',especialidade:'clinica_geral',
    justificativa:'Sintomas respiratórios leves.',prioridade:3,sugestao_fluxo:'agendamento',
    recomendacao:'Agende uma consulta o mais breve possível.',criado_em:'2026-11-22T12:00:00Z'},
  baixa:{id:10,urgencia:'baixa',classificacao:'verde',especialidade:'dermatologia',
    justificativa:'Alteração de pele estável.',prioridade:4,sugestao_fluxo:'agendamento',
    recomendacao:'Agende uma consulta de rotina.',criado_em:'2026-11-22T12:00:00Z'},
};

// Monta app.js com um DOM falso e envia o formulário de triagem.
async function enviarTriagem(nivel,{fila}={}){
  const nodes=new Map(['triagem-form','resultado','paciente-id','relato'].map(id=>[id,element()]));
  nodes.get('relato').value='Relato de teste para a triagem';
  const pedidos=[];const erros=[];const sucessos=[];
  const Auth={current:()=>({perfil:'paciente',id:2,nome:'Paciente'}),patientId:()=> '2',adaptResponse:(_,body)=>body};
  vm.runInNewContext(fs.readFileSync('frontend/assets/js/app.js','utf8'),{
    document:{getElementById:id=>nodes.get(id)||null,createElement:element,
      documentElement:{style:{setProperty(){}}},body:{dataset:{page:'triagem'},classList:{toggle(){}}},
      querySelector:()=>null,querySelectorAll:()=>[]},
    window:{Auth},Auth,HTMLElement,location:{search:''},URLSearchParams,AbortController,setTimeout,clearTimeout,
    localStorage:{getItem:()=>null},sessionStorage:{setItem(){}},
    Feedback:{carregando:()=>()=>{},sucesso:m=>sucessos.push(m),erro:m=>erros.push(m)},
    fetch:async(path,options={})=>{
      pedidos.push({path,method:options.method||'GET',body:options.body?JSON.parse(options.body):undefined});
      if(path==='/fila'){
        if(fila==='falha')return {ok:false,status:400,json:async()=>({detail:'Fila indisponível.'})};
        return {ok:true,status:200,json:async()=>({medico_alocado:'Helena',score:105.5})};
      }
      return {ok:true,status:200,json:async()=>TRIAGENS[nivel]};
    },
  });
  const form=nodes.get('triagem-form');form.events.submit({preventDefault(){},currentTarget:form});
  await new Promise(resolve=>setImmediate(resolve));
  const resultado=nodes.get('resultado');
  const nos=todos(resultado);
  return {pedidos,erros,sucessos,resultado,nos,
    botaoFila:nos.find(n=>n.tag==='button'&&n.textContent===TEXTO_FILA),
    linkAgendamento:nos.find(n=>n.tag==='a'&&n.textContent===TEXTO_AGENDAMENTO)};
}

const esperar=()=>new Promise(resolve=>setImmediate(resolve));

test('enviar a triagem nao chama POST /fila',async()=>{
  const {pedidos,erros}=await enviarTriagem('emergencia');
  assert.deepEqual(erros,[]);
  assert.deepEqual(pedidos.map(p=>[p.method,p.path]),[['POST','/pacientes/2/triagens']]);
});

for(const nivel of Object.keys(TRIAGENS)){
  test(`resultado (${nivel}) mostra a sugestao da IA e os dois botoes de escolha`,async()=>{
    const {resultado,nos,botaoFila,linkAgendamento}=await enviarTriagem(nivel);
    const triagem=TRIAGENS[nivel];
    assert.equal(resultado.hidden,false);
    assert.ok(nos.some(n=>n.textContent===triagem.recomendacao),'mostra a recomendação textual da IA');
    const rotulo=triagem.sugestao_fluxo==='urgencia'?'Atendimento de urgência':'Agendamento de consulta';
    assert.ok(nos.some(n=>typeof n.textContent==='string'&&n.textContent.includes('Sugestão da IA')&&n.textContent.includes(rotulo)));
    assert.ok(botaoFila,'botão da fila sempre visível');
    assert.ok(linkAgendamento,'botão de agendamento sempre visível');
  });

  test(`botao de agendamento (${nivel}) leva especialidade, triagem_id e relato do paciente`,async()=>{
    const {linkAgendamento}=await enviarTriagem(nivel);
    const triagem=TRIAGENS[nivel];
    assert.ok(linkAgendamento.href.startsWith('/pages/agendamento.html?'));
    const params=new URLSearchParams(linkAgendamento.href.split('?')[1]);
    assert.equal(params.get('paciente'),'2');
    assert.equal(params.get('triagem_id'),String(triagem.id));
    assert.equal(params.get('especialidade'),triagem.especialidade);
    assert.equal(params.get('motivo'),'Relato de teste para a triagem');
  });

  test(`botao sugerido pela IA (${nivel}) recebe o destaque`,async()=>{
    const {botaoFila,linkAgendamento}=await enviarTriagem(nivel);
    const sugeridoFila=TRIAGENS[nivel].sugestao_fluxo==='urgencia';
    assert.ok(botaoFila.className.includes(sugeridoFila?'primary':'secondary'));
    assert.ok(linkAgendamento.className.includes(sugeridoFila?'secondary':'primary'));
  });
}

test('alerta do SAMU 192 aparece na emergencia e nao na triagem de baixa urgencia',async()=>{
  const emergencia=await enviarTriagem('emergencia');
  assert.ok(emergencia.nos.some(n=>typeof n.textContent==='string'&&n.textContent.includes('SAMU 192')));
  assert.ok(emergencia.nos.some(n=>n.tag==='a'&&n.href==='tel:192'));
  const baixa=await enviarTriagem('baixa');
  assert.ok(!baixa.nos.some(n=>typeof n.textContent==='string'&&n.textContent.includes('SAMU 192')));
});

test('clicar em entrar na fila faz POST /fila com a triagem e o paciente',async()=>{
  const {pedidos,botaoFila,sucessos}=await enviarTriagem('emergencia');
  assert.equal(pedidos.length,1);
  botaoFila.events.click({preventDefault(){}});
  await esperar();
  assert.equal(pedidos.length,2);
  assert.deepEqual(pedidos[1],{path:'/fila',method:'POST',body:{triagem_id:7,paciente_id:2}});
  assert.equal(botaoFila.disabled,true,'bloqueia novo clique depois de entrar na fila');
  assert.ok(sucessos.length>=1);
});

test('mostra o medico alocado e o score depois de entrar na fila',async()=>{
  const {resultado,botaoFila}=await enviarTriagem('alta');
  botaoFila.events.click({preventDefault(){}});
  await esperar();
  const textos=todos(resultado).map(n=>n.textContent).filter(t=>typeof t==='string');
  assert.ok(textos.some(t=>t.includes('Helena')&&t.includes('105.5')));
});

test('clique duplo em entrar na fila envia apenas um POST /fila',async()=>{
  const {pedidos,botaoFila}=await enviarTriagem('emergencia');
  botaoFila.events.click({preventDefault(){}});
  botaoFila.events.click({preventDefault(){}});
  await esperar();
  assert.equal(pedidos.filter(p=>p.path==='/fila').length,1);
});

test('falha ao entrar na fila mostra o erro e libera o botao para tentar de novo',async()=>{
  const {pedidos,resultado,botaoFila,erros}=await enviarTriagem('emergencia',{fila:'falha'});
  botaoFila.events.click({preventDefault(){}});
  await esperar();
  assert.equal(pedidos.filter(p=>p.path==='/fila').length,1);
  assert.equal(botaoFila.disabled,false);
  const textos=todos(resultado).map(n=>n.textContent).filter(t=>typeof t==='string');
  assert.ok(textos.some(t=>t.includes('Fila indisponível.')));
  assert.ok(erros.length>=1);
});

test('resultado da triagem oferece apenas acoes de paciente',async()=>{
  const {nos}=await enviarTriagem('baixa');
  const links=nos.filter(n=>n.tag==='a');
  assert.ok(links.some(n=>n.href.startsWith('/pages/historico.html')));
  assert.ok(links.some(n=>n.href.startsWith('/pages/agendamento.html')));
  assert.ok(!links.some(n=>n.href.includes('/pages/medico.html')));
});
