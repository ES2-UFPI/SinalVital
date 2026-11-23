const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function painel(){
  const nodes=new Map();
  function element(){return {children:[],hidden:false,disabled:false,textContent:'',
    append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;}};}
  for(const id of ['paciente-selecionado-resumo','atendimento-vazio','registro-clinico','atendimento-titulo','historico-detalhes'])nodes.set(id,element());
  const context={document:{getElementById:id=>nodes.get(id)||null,createElement:element,
    documentElement:{style:{setProperty(){}}},body:{dataset:{page:'medico'},classList:{toggle(){}}},
    querySelector:()=>null,querySelectorAll:()=>[]},localStorage:{getItem:()=>null},
    location:{search:''},URLSearchParams,window:{},setTimeout,clearTimeout};
  vm.createContext(context);vm.runInContext(fs.readFileSync('frontend/assets/js/app.js','utf8'),context);
  return {nodes,selecionar:dados=>context.atualizarResumoPacienteSelecionado(dados)};
}

test('registro aparece para paciente valido e fecha ao limpar ou bloquear atendimento',()=>{
  const p=painel();p.selecionar({id:null});
  assert.equal(p.nodes.get('registro-clinico').hidden,true);
  assert.equal(p.nodes.get('registro-clinico').disabled,true);
  assert.equal(p.nodes.get('atendimento-vazio').hidden,false);
  p.selecionar({id:2,nome:'Raimundo',motivo:'Dor de cabeça'});
  assert.equal(p.nodes.get('registro-clinico').hidden,false);
  assert.equal(p.nodes.get('registro-clinico').disabled,false);
  assert.equal(p.nodes.get('atendimento-vazio').hidden,true);
  assert.equal(p.nodes.get('atendimento-titulo').textContent,'Atendimento de Raimundo');
  p.selecionar({id:3,nome:'Outro paciente',bloqueado:true});
  assert.equal(p.nodes.get('registro-clinico').disabled,true);
  p.selecionar({id:null});
  assert.equal(p.nodes.get('atendimento-titulo').textContent,'Seu atendimento');
});
