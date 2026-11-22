const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function api(fetch) {
  const context={window:{},fetch,AbortController,setTimeout,clearTimeout};
  vm.runInNewContext(fs.readFileSync('frontend/assets/js/admin-api.js','utf8'),context);
  return context.window.AdminAPI;
}
test('senha segue apenas no header e logout impede novas chamadas',async()=>{
  const chamadas=[];
  const admin=api(async(path,options)=>{
    chamadas.push({path,options}); return {ok:true,status:200,json:async()=>[]};
  });
  await assert.rejects(admin.request('/admin/pacientes'));
  await admin.login('senha-ficticia');
  await admin.request('/admin/pacientes');
  assert.equal(chamadas.length,2);
  assert.equal(chamadas[0].options.headers['X-Admin-Password'],'senha-ficticia');
  assert.equal(chamadas[0].path.includes('senha-ficticia'),false);
  assert.equal(chamadas[0].options.cache,'no-store');
  admin.logout();
  await assert.rejects(admin.request('/admin/medicos'));
  assert.equal(chamadas.length,2);
});
test('senha incorreta nao permanece na memoria da API',async()=>{
  const admin=api(async()=>({ok:false,status:401,json:async()=>({detail:'Senha inválida.'})}));
  await assert.rejects(admin.login('errada'),/Senha inválida/);
  await assert.rejects(admin.request('/admin/pacientes'),/Entre com/);
});
test('servidor sem senha configurada apresenta erro e bloqueia acesso',async()=>{
  const admin=api(async()=>({ok:false,status:503,json:async()=>({detail:'Acesso não configurado.'})}));
  await assert.rejects(admin.login('qualquer'),/não configurado/);
  await assert.rejects(admin.request('/admin/pacientes'),/Entre com/);
});
test('resposta atrasada nao restaura dados depois de sair',async()=>{
  let resolver;
  const admin=api(()=>new Promise(resolve=>{resolver=resolve;}));
  const login=admin.login('senha-ficticia');
  admin.logout();
  resolver({ok:true,status:200,json:async()=>[{nome:'Dado antigo'}]});
  await assert.rejects(login,/Sessão encerrada/);
});
