const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

function element(tag='div') {
  return {tag,children:[],dataset:{},hidden:false,value:'',open:false,events:{},
    classList:{toggle(){}},setAttribute(key,value){this[key]=value;},focus(){},
    append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},
    addEventListener(event,callback){this.events[event]=callback;},
    reset(){},querySelector(){return this.button ||= element('button');},
    querySelectorAll(){return this.children.filter(c=>c.tag==='details'&&c.open);}};
}
function browser() {
  const nodes=new Map();const get=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);};
  get('admin-area').hidden=true;get('admin-tipo').value='urgencia';get('admin-etapa').value='todos';
  get('admin-filtro-tipo').value='todos';
  const selectEtapa=fs.readFileSync('frontend/pages/admin.html','utf8').match(/<select id="admin-etapa">([\s\S]*?)<\/select>/)[1];
  get('admin-etapa').options=Array.from(selectEtapa.matchAll(/<option value="([^"]+)"/g),m=>({value:m[1],disabled:false}));
  get('admin-filtros').reset=()=>{
    get('admin-etapa').value='todos';get('admin-filtro-tipo').value='todos';get('admin-busca').value='';
  };
  const docEvents={};const timers=new Map();let nextTimer=0;let authenticated=false;
  const document={hidden:false,getElementById:get,createElement:element,
    addEventListener(event,cb){docEvents[event]=cb;}};
  const calls=[];
  let response=async()=>[{id:1,nome:'Paciente exemplo',atendimentos:[]}];
  const AdminAPI={login:async()=>{authenticated=true;return [];},logout(){authenticated=false;},
    isAuthenticated:()=>authenticated,request(path){calls.push(path);return response(path);}};
  vm.runInNewContext(fs.readFileSync('frontend/assets/js/admin.js','utf8'),{
    document,AdminAPI,URLSearchParams,Date,
    setTimeout(cb,delay){timers.set(++nextTimer,{cb,delay});return nextTimer;},
    clearTimeout(id){timers.delete(id);},
  });
  const settle=()=>new Promise(resolve=>setImmediate(resolve));
  async function event(id,name='click'){const target=get(id);target.events[name]({preventDefault(){},currentTarget:target});await settle();}
  return {get,calls,timers,document,settle,setResponse(fn){response=fn;},event,
    async enter(){await event('admin-login','submit');await event('aba-pacientes');},
    async tick(){const timer=timers.values().next().value;assert.ok(timer,'Atualização automática deve ser agendada');
      timers.clear();timer.cb();await settle();},
    async visibility(hidden){document.hidden=hidden;docEvents.visibilitychange?.();await settle();}};
}
function paciente(etapa){return [{id:1,nome:'Paciente exemplo',atendimentos:[
  {id:1,tipo:'urgencia',etapa,medico_nome:'Helena',data:'2026-11-22T12:00:00Z'},
]}];}
const texto=node=>[node.textContent||'',...node.children.map(texto)].join(' ');

test('cada tipo mostra somente as etapas compativeis',async()=>{
  const b=browser();await b.enter();
  const permitidas={
    urgencia:['todos','aguardando','atendido','cancelado'],
    agendamento:['todos','agendado','atendido','cancelado'],
    consulta:['todos','atendido'],triagem:['todos','triagem'],
  };
  for(const [tipo,etapas] of Object.entries(permitidas)){
    b.get('admin-filtro-tipo').value=tipo;await b.event('admin-filtro-tipo','change');
    assert.deepEqual(b.get('admin-etapa').options.filter(o=>!o.hidden).map(o=>o.value),etapas);
  }
  b.get('admin-filtro-tipo').value='todos';await b.event('admin-filtro-tipo','change');
  assert.ok(b.get('admin-etapa').options.every(o=>!o.disabled));
  assert.ok(b.get('admin-etapa').options.every(o=>!o.hidden));
});

test('etapa incompativel volta para todos antes da busca e permanece no timer',async()=>{
  const b=browser();await b.enter();
  b.get('admin-etapa').value='agendado';
  b.get('admin-filtro-tipo').value='urgencia';await b.event('admin-filtro-tipo','change');
  assert.equal(b.get('admin-etapa').value,'todos');
  assert.equal(new URLSearchParams(b.calls.at(-1).split('?')[1]).get('etapa'),'todos');
  await b.tick();
  assert.equal(new URLSearchParams(b.calls.at(-1).split('?')[1]).get('etapa'),'todos');
});

test('sair restaura todas as opcoes de etapa para o proximo acesso',async()=>{
  const b=browser();await b.enter();
  b.get('admin-filtro-tipo').value='consulta';await b.event('admin-filtro-tipo','change');
  await b.event('admin-sair');await b.enter();
  assert.equal(b.get('admin-filtro-tipo').value,'todos');
  assert.ok(b.get('admin-etapa').options.every(o=>!o.disabled));
  assert.ok(b.get('admin-etapa').options.every(o=>!o.hidden));
});

test('tipo combina com etapa e nome e persiste no ciclo automatico',async()=>{
  const b=browser();await b.enter();
  b.get('admin-busca').value='Paciente';b.get('admin-etapa').value='aguardando';
  b.get('admin-filtro-tipo').value='urgencia';await b.event('admin-filtro-tipo','change');
  let parametros=new URLSearchParams(b.calls.at(-1).split('?')[1]);
  assert.equal(parametros.get('tipo'),'urgencia');
  assert.equal(parametros.get('etapa'),'aguardando');
  assert.equal(parametros.get('nome'),'Paciente');
  await b.tick();assert.equal(new URLSearchParams(b.calls.at(-1).split('?')[1]).get('tipo'),'urgencia');
  b.get('admin-filtro-tipo').value='todos';await b.event('admin-filtro-tipo','change');
  assert.equal(new URLSearchParams(b.calls.at(-1).split('?')[1]).get('tipo'),'todos');
});

test('registro mostra especialidade do medico e suporta atendimento sem medico',async()=>{
  const b=browser();
  const dados=paciente('aguardando');
  dados[0].atendimentos[0].medico_especialidade='clinica_geral';
  b.setResponse(async()=>dados);await b.enter();
  assert.match(texto(b.get('admin-pacientes-lista')),/Helena · clinica geral ·/);
  dados[0].atendimentos[0].medico_nome=null;
  dados[0].atendimentos[0].medico_especialidade=null;
  await b.tick();
  const exibido=texto(b.get('admin-pacientes-lista'));
  assert.match(exibido,/Sem médico vinculado/);
  assert.doesNotMatch(exibido,/null|undefined|clinica geral/);
});

test('trocar etapa aplica filtro imediatamente e o mantem na atualizacao automatica',async()=>{
  const b=browser();await b.enter();
  b.get('admin-etapa').value='agendado';
  await b.event('admin-etapa','change');
  assert.match(b.calls.at(-1),/etapa=agendado/);
  await b.tick();
  assert.match(b.calls.at(-1),/etapa=agendado/);
  b.get('admin-etapa').value='todos';await b.event('admin-etapa','change');
  assert.match(b.calls.at(-1),/etapa=todos/);
});

test('atendimento muda automaticamente e preserva cartao aberto e filtros',async()=>{
  const b=browser();b.get('admin-busca').value='Paciente';b.get('admin-etapa').value='aguardando';
  b.setResponse(async()=>paciente('aguardando'));await b.enter();
  assert.equal(b.timers.values().next().value.delay,10000);
  b.get('admin-pacientes-lista').children[0].open=true;
  b.setResponse(async()=>paciente('atendido'));await b.tick();
  assert.match(texto(b.get('admin-pacientes-lista')),/Atendido/);
  assert.equal(b.get('admin-pacientes-lista').children[0].open,true);
  assert.equal(b.calls.length,2);
  assert.match(b.calls[1],/nome=Paciente&etapa=aguardando/);
  assert.equal(b.get('admin-busca').value,'Paciente');
});
test('pausa em outra aba e ao sair da administracao',async()=>{
  const b=browser();await b.enter();assert.equal(b.timers.size,1);
  await b.event('aba-medicos');assert.equal(b.timers.size,0);
  await b.event('aba-pacientes');assert.equal(b.timers.size,1);
  await b.event('admin-sair');assert.equal(b.timers.size,0);
});
test('pausa quando a pagina fica oculta e atualiza ao voltar',async()=>{
  const b=browser();await b.enter();
  await b.visibility(true);assert.equal(b.timers.size,0);
  b.setResponse(async()=>paciente('atendido'));await b.visibility(false);
  assert.match(texto(b.get('admin-pacientes-lista')),/Atendido/);
  assert.equal(b.timers.size,1);
});
test('nao sobrepoe requisicoes e descarta resultado de filtro antigo',async()=>{
  const b=browser();let resolver;
  b.setResponse(()=>new Promise(resolve=>{resolver=resolve;}));await b.enter();
  b.get('admin-busca').value='Novo filtro';
  await b.event('admin-filtros','submit');assert.equal(b.calls.length,1);
  b.setResponse(async()=>[]);resolver(paciente('aguardando'));await b.settle();await b.settle();
  assert.equal(b.calls.length,2);
  assert.match(b.calls[1],/nome=Novo\+filtro/);
  assert.doesNotMatch(texto(b.get('admin-pacientes-lista')),/Paciente exemplo/);
});
test('resposta pendente nao volta ao painel depois de sair',async()=>{
  const b=browser();let resolver;
  b.setResponse(()=>new Promise(resolve=>{resolver=resolve;}));await b.enter();
  await b.event('admin-sair');resolver(paciente('atendido'));await b.settle();
  assert.equal(b.get('admin-pacientes-lista').children.length,0);
  assert.equal(b.timers.size,0);
});
test('falha automatica conserva dados e permite proxima tentativa',async()=>{
  const b=browser();b.setResponse(async()=>paciente('aguardando'));await b.enter();
  b.setResponse(async()=>{throw new Error('Falha temporária');});await b.tick();
  assert.match(texto(b.get('admin-pacientes-lista')),/Aguardando/);
  b.setResponse(async()=>paciente('atendido'));await b.tick();
  assert.match(texto(b.get('admin-pacientes-lista')),/Atendido/);
});
test('dados inalterados nao reconstroem os cartoes e preservam filtro em edicao',async()=>{
  const b=browser();b.setResponse(async()=>paciente('aguardando'));await b.enter();
  const card=b.get('admin-pacientes-lista').children[0];
  b.get('admin-busca').value='Texto ainda não aplicado';await b.tick();
  assert.equal(b.get('admin-pacientes-lista').children[0],card);
  assert.match(b.calls[1],/nome=&etapa=todos/);
  assert.equal(b.get('admin-busca').value,'Texto ainda não aplicado');
});
test('erro da busca enfileirada durante atualizacao automatica e tratado',async()=>{
  const b=browser();await b.enter();let resolver;
  b.setResponse(()=>new Promise(resolve=>{resolver=resolve;}));await b.tick();
  b.get('admin-busca').value='Novo filtro';await b.event('admin-filtros','submit');
  b.setResponse(async()=>{throw new Error('Falha da busca');});
  resolver([]);await b.settle();await b.settle();
  assert.match(b.get('admin-feedback').textContent,/Falha da busca/);
  assert.equal(b.timers.size,1);
});
