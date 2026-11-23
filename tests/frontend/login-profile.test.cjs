const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

test('perfil ajusta identificacao e cadastro sem apagar o identificador digitado',()=>{
  const nodes=new Map(['identificador','identificador-label','login-ajuda','login-submit','login-cadastro'].map(id=>[id,{}]));
  let mudar;
  const form={elements:{perfil:{value:'paciente'}},addEventListener(event,fn){mudar=fn;}};
  nodes.set('login-form',form);nodes.get('identificador').value='123';
  vm.runInNewContext(fs.readFileSync('frontend/assets/js/login-profile.js','utf8'),{
    document:{readyState:'complete',getElementById:id=>nodes.get(id)||null},
  });
  assert.equal(nodes.get('login-cadastro').hidden,false);
  assert.equal(nodes.get('identificador').inputMode,'text');
  assert.match(nodes.get('login-ajuda').textContent,/e-mail/);
  form.elements.perfil.value='medico';mudar({target:{name:'perfil'}});
  assert.equal(nodes.get('login-cadastro').hidden,true);
  assert.equal(nodes.get('identificador').inputMode,'numeric');
  assert.equal(nodes.get('login-submit').textContent,'Entrar no painel médico →');
  assert.equal(nodes.get('identificador').value,'123');
  form.elements.perfil.value='paciente';mudar({target:{name:'perfil'}});
  assert.equal(nodes.get('login-cadastro').hidden,false);
  assert.equal(nodes.get('identificador-label').textContent,'Número do cadastro ou e-mail *');
});
