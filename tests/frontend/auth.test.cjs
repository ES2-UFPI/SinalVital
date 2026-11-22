const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('frontend/assets/js/auth.js', 'utf8');

function browser(profile, page = 'historico') {
  const data = new Map(profile ? [['sv-profile', JSON.stringify(profile)], ['sv-patient', '99']] : []);
  const nodes = new Map();
  const links = ['inicio','cadastro','triagem','agendamento','historico','fila','medico'].map(nav => ({dataset:{nav}, hidden:false}));
  let init;
  const location = {assign(url) { this.target=url; }, replace(url) { this.target=url; }};
  const document = {
    readyState:'loading', body:{dataset:{page}},
    addEventListener(event, callback) { init=callback; },
    getElementById(id) { return nodes.get(id) || null; },
    querySelector() { return null; },
    querySelectorAll() { return links; },
  };
  const context = {window:{}, document, location, sessionStorage:{
    getItem:key=>data.get(key) || null, setItem:(key,value)=>data.set(key,value), removeItem:key=>data.delete(key),
  }, console, URL, setTimeout, clearTimeout};
  vm.runInNewContext(source, context);
  return {auth:context.window.Auth, nodes, links, data, location, init:()=>init()};
}
const paciente = {perfil:'paciente', id:2, nome:'Raimundo'};
const medico = {perfil:'medico', id:7, nome:'Helena'};

test('sessao malformada e ignorada e sair limpa identificadores antigos', () => {
  const b=browser(paciente);
  b.data.set('sv-profile','invalido');
  assert.equal(b.auth.current(),null);
  b.auth.logout();
  assert.equal(b.data.size,0);
  assert.equal(b.location.target,'/pages/login.html');
});
test('perfil paciente sempre prevalece sobre ID fornecido por URL', () => {
  assert.equal(browser(paciente).auth.patientId('99'),'2');
});
test('paciente ve apenas seus itens e mantem posicao global da fila', () => {
  const b=browser(paciente);
  const rows=[{paciente_id:1,status:'aguardando'}, {paciente_id:2,status:'aguardando'}, {paciente_id:3,status:'aguardando'}];
  const result=b.auth.adaptResponse('/fila', rows);
  assert.equal(result.length,1);
  assert.equal(result[0].paciente_id,2);
  assert.equal(result[0].posicao_global,2);
  assert.equal(rows[1].posicao_global,undefined);
});
test('paciente ve somente seus agendamentos, inclusive com query string', () => {
  const result=browser(paciente).auth.adaptResponse('/agendamentos?status=agendado',[{paciente_id:1},{paciente_id:2}]);
  assert.equal(result.length,1);
  assert.equal(result[0].paciente_id,2);
});
test('medico ve apenas seus pacientes e seu cadastro no painel', () => {
  const b=browser(medico,'medico');
  assert.equal(b.auth.adaptResponse('/fila?status=aguardando',[{medico_id:7},{medico_id:8}]).length,1);
  assert.equal(b.auth.adaptResponse('/medicos',[{id:8},{id:7}])[0].id,7);
});
test('paciente tem menu proprio e identificador preenchido e bloqueado', () => {
  const b=browser(paciente);
  const input={value:'99', readOnly:false}; b.nodes.set('paciente-id', input);
  b.init();
  assert.equal(input.value,'2'); assert.equal(input.readOnly,true);
  assert.equal(b.links.find(l=>l.dataset.nav==='medico').hidden,true);
  assert.equal(b.links.find(l=>l.dataset.nav==='historico').hidden,false);
});
test('acesso direto ao painel medico com perfil paciente redireciona', () => {
  const b=browser(paciente,'medico'); b.init(); assert.equal(b.location.target,'/');
});
test('acesso a tela de paciente com perfil medico redireciona', () => {
  const b=browser(medico,'triagem'); b.init(); assert.equal(b.location.target,'/pages/medico.html');
});
test('visitante e direcionado ao login em telas de atendimento', () => {
  const b=browser(null); b.init(); assert.equal(b.location.target,'/pages/login.html');
});
test('novo cadastro permanece acessivel sem perfil', () => {
  const b=browser(null,'cadastro'); b.init(); assert.equal(b.location.target,undefined);
});
