const form=document.querySelector('#auth-form'),error=document.querySelector('#auth-error');
let setup=false;
async function initialize(){
  const status=await fetch('/api/auth/status').then(response=>response.json());
  if(!status.auth_required){location.href='/';return;}
  setup=status.setup_required;
  if(location.pathname==='/setup'&&!setup){location.href='/login';return;}
  if(setup){
    document.querySelector('#auth-eyebrow').textContent='FIRST-RUN SECURITY';
    document.querySelector('#auth-title').textContent='Create the studio administrator';
    document.querySelector('#auth-intro').textContent='This account will own existing productions and control studio-wide settings.';
    document.querySelector('#name-field').hidden=false;document.querySelector('#name-field input').required=true;
    document.querySelector('#key-field').hidden=false;
    form.elements.password.autocomplete='new-password';
  }
}
form.addEventListener('submit',async event=>{
  event.preventDefault();error.textContent='';const button=form.querySelector('button');button.disabled=true;button.textContent=setup?'Securing studio…':'Signing in…';
  const body={email:form.elements.email.value,password:form.elements.password.value};
  if(setup){body.display_name=form.elements.display_name.value;body.bootstrap_key=form.elements.bootstrap_key.value;}
  try{const response=await fetch(setup?'/api/auth/setup':'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok){const payload=await response.json();throw new Error(typeof payload.detail==='string'?payload.detail:'Unable to continue');}location.href='/';}
  catch(reason){error.textContent=reason.message;button.disabled=false;button.textContent='Continue';}
});
initialize().catch(()=>{error.textContent='Kizuna could not check the studio security status.';});
