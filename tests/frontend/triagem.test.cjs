const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

test('resultado da triagem oferece apenas acoes de paciente',async()=>{
  function element(tag='div'){
    return {tag,children:[],events:{},hidden:false,value:'',
      classList:{toggle(){}},setAttribute(){},removeAttribute(){},focus(){},
      append(...children){this.children.push(...children);},
      replaceChildren(...children){this.children=children;},
      querySelector(){return null;},addEventListener(name,fn){this.events[name]=fn;}};
  }
  const nodes=new Map(['triagem-form','resultado','paciente-id','relato'].map(id=>[id,element()]));
  nodes.get('relato').value='Dor de cabeça desde ontem';
  const pedidos=[];const erros=[];
  const Auth={current:()=>({perfil:'paciente',id:2,nome:'Paciente'}),patientId:()=> '2',adaptResponse:(_,body)=>body};
  vm.runInNewContext(fs.readFileSync('frontend/assets/js/app.js','utf8'),{
    document:{getElementById:id=>nodes.get(id)||null,createElement:element,
      documentElement:{style:{setProperty(){}}},body:{dataset:{page:'triagem'},classList:{toggle(){}}},
      querySelector:()=>null,querySelectorAll:()=>[]},
    window:{Auth},Auth,location:{search:''},URLSearchParams,AbortController,setTimeout,clearTimeout,
    localStorage:{getItem:()=>null},sessionStorage:{setItem(){}},
    Feedback:{carregando:()=>()=>{},sucesso(){},erro:message=>erros.push(message)},
    fetch:async(path)=>{
      pedidos.push(path);
      return {ok:true,status:200,json:async()=>path==='/fila'
        ? {medico_alocado:'Helena',score:5}
        : {id:7,urgencia:'baixa',especialidade:'clinica_geral',justificativa:'Avaliação inicial',
          prioridade:1,criado_em:'2026-11-22T12:00:00Z'}};
    },
  });
  const form=nodes.get('triagem-form');form.events.submit({preventDefault(){},currentTarget:form});
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(erros,[]);
  assert.deepEqual(pedidos,['/pacientes/2/triagens','/fila']);
  const resultado=nodes.get('resultado');assert.equal(resultado.hidden,false);
  const acoes=resultado.children.find(node=>node.className==='patient-actions');
  assert.ok(acoes);
  const links=acoes.children.filter(node=>node.tag==='a');
  assert.ok(links.some(node=>node.href.startsWith('/pages/historico.html')));
  assert.ok(links.some(node=>node.href.startsWith('/pages/agendamento.html')));
  assert.ok(!links.some(node=>node.href.includes('/pages/medico.html')));
  assert.equal(links.length,2);
});
