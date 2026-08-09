const form=document.querySelector('#auth-form'),error=document.querySelector('#auth-error');
let setup=false,signup=false,invitationToken='';
async function initialize(){
  const status=await fetch('/api/auth/status').then(response=>response.json());
  if(status.marketing_url)document.querySelector('#marketing-link').href=status.marketing_url;
  invitationToken=location.pathname.startsWith('/invite/')?decodeURIComponent(location.pathname.split('/').pop()):'';
  if(invitationToken){
    const response=await fetch(`/api/auth/invitations/${encodeURIComponent(invitationToken)}`);if(!response.ok)throw new Error('This invitation is invalid or expired.');const invitation=await response.json();
    document.querySelector('#auth-eyebrow').textContent='STUDIO INVITATION';document.querySelector('#auth-title').textContent='Join the production';document.querySelector('#auth-intro').textContent=`${invitation.email} was invited to ${invitation.project_access.map(item=>item.project_title).join(', ')}.`;
    document.querySelector('#name-field').hidden=false;document.querySelector('#name-field input').required=true;document.querySelector('#name-field input').value=invitation.display_name||'';
    form.elements.email.closest('label').hidden=true;form.elements.email.required=false;form.elements.password.autocomplete='new-password';document.querySelector('#auth-switch').hidden=true;return;
  }
  if(!status.auth_required){location.href='/';return;}
  signup=location.pathname==='/signup';
  if(signup){
    if(!status.trial_signup_available)throw new Error('Trial signup will open as soon as Kizuna finishes studio setup.');
    document.querySelector('#auth-eyebrow').textContent=`${status.trial_days}-DAY STUDIO TRIAL`;document.querySelector('#auth-title').textContent='Create your first production';document.querySelector('#auth-intro').textContent=`Explore the full workflow for ${status.trial_days} days. Trial video exports are limited to ${status.trial_export_seconds} seconds and include a Kizuna watermark.`;
    document.querySelector('#name-field').hidden=false;document.querySelector('#name-field input').required=true;form.elements.password.autocomplete='new-password';form.querySelector('button').textContent='Start free trial';document.querySelector('#auth-switch').innerHTML='<a href="/login">Already have an account? Sign in</a>';return;
  }
  setup=status.setup_required;
  if(location.pathname==='/setup'&&!setup){location.href='/login';return;}
  if(setup){
    document.querySelector('#auth-eyebrow').textContent='FIRST-RUN SECURITY';document.querySelector('#auth-title').textContent='Create the studio administrator';document.querySelector('#auth-intro').textContent='This account will own existing productions and control studio-wide settings.';
    document.querySelector('#name-field').hidden=false;document.querySelector('#name-field input').required=true;document.querySelector('#key-field').hidden=false;form.elements.password.autocomplete='new-password';document.querySelector('#auth-switch').hidden=true;
  }
}
form.addEventListener('submit',async event=>{
  event.preventDefault();error.textContent='';const button=form.querySelector('button');button.disabled=true;button.textContent=setup?'Securing studio...':signup?'Creating your studio...':'Signing in...';
  const body=invitationToken?{display_name:form.elements.display_name.value,password:form.elements.password.value}:{email:form.elements.email.value,password:form.elements.password.value};
  if(signup)body.display_name=form.elements.display_name.value;
  if(setup){body.display_name=form.elements.display_name.value;body.bootstrap_key=form.elements.bootstrap_key.value;}
  try{const endpoint=invitationToken?`/api/auth/invitations/${encodeURIComponent(invitationToken)}`:setup?'/api/auth/setup':signup?'/api/auth/trial':'/api/auth/login';const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok){const payload=await response.json();throw new Error(typeof payload.detail==='string'?payload.detail:'Unable to continue');}location.href='/';}
  catch(reason){error.textContent=reason.message;button.disabled=false;button.textContent=signup?'Start free trial':'Continue';}
});
initialize().catch(reason=>{error.textContent=reason.message||'Kizuna could not check the studio security status.';});
