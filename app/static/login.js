const form=document.querySelector('#auth-form'),error=document.querySelector('#auth-error'),button=form.querySelector('button');
const title=document.querySelector('#auth-title'),intro=document.querySelector('#auth-intro'),eyebrow=document.querySelector('#auth-eyebrow'),authSwitch=document.querySelector('#auth-switch');
let mode='login',invitationToken='',betaInvitationToken='',flowToken='';
const field=name=>form.elements[name].closest('label');
const hideForm=message=>{form.hidden=true;intro.textContent=message;authSwitch.hidden=false;authSwitch.innerHTML='<a href="/login">Return to sign in</a>';};
async function jsonRequest(url,options={}){const response=await fetch(url,options);let payload={};try{payload=await response.json();}catch{}if(!response.ok)throw new Error(typeof payload.detail==='string'?payload.detail:'Unable to continue');return payload;}
async function initialize(){
  const status=await jsonRequest('/api/auth/status');
  if(status.marketing_url)document.querySelector('#marketing-link').href=status.marketing_url;
  const parts=location.pathname.split('/').filter(Boolean);flowToken=parts.length>1?decodeURIComponent(parts.at(-1)):'';
  if(location.pathname.startsWith('/verify-email/')){
    mode='verify';form.hidden=true;authSwitch.hidden=true;eyebrow.textContent='ACCOUNT SECURITY';title.textContent='Verifying your email';intro.textContent='Checking your single-use verification link…';
    const result=await jsonRequest(`/api/auth/verify/${encodeURIComponent(flowToken)}`,{method:'POST'});title.textContent='Email verified';hideForm(result.message);return;
  }
  if(location.pathname.startsWith('/reset-password/')){
    mode='reset';await jsonRequest(`/api/auth/password/reset/${encodeURIComponent(flowToken)}`);eyebrow.textContent='ACCOUNT RECOVERY';title.textContent='Choose a new password';intro.textContent='Use at least 12 characters. Completing this reset signs out every existing session.';
    field('email').hidden=true;form.elements.email.required=false;field('confirm_password').hidden=false;form.elements.confirm_password.required=true;form.elements.password.autocomplete='new-password';button.textContent='Update password';authSwitch.hidden=true;return;
  }
  if(location.pathname==='/forgot-password'){
    mode='forgot';eyebrow.textContent='ACCOUNT RECOVERY';title.textContent='Reset your password';intro.textContent='Enter your account email. For privacy, Kizuna always returns the same response.';field('password').hidden=true;form.elements.password.required=false;button.textContent='Send reset link';authSwitch.innerHTML='<a href="/login">Return to sign in</a>';return;
  }
  betaInvitationToken=location.pathname.startsWith('/beta-invite/')?decodeURIComponent(parts.at(-1)):'';
  if(betaInvitationToken){
    mode='beta-invite';const invitation=await jsonRequest(`/api/auth/beta-invitations/${encodeURIComponent(betaInvitationToken)}`);eyebrow.textContent='PRIVATE BETA INVITATION';title.textContent='Build your first original story';intro.textContent=`${invitation.email} was invited to the ${invitation.cohort} cohort. Beta access is currently scheduled through ${new Date(invitation.access_ends_at).toLocaleDateString()}.`;
    field('display_name').hidden=false;form.elements.display_name.required=true;form.elements.display_name.value=invitation.display_name||'';field('email').hidden=true;form.elements.email.required=false;form.elements.password.autocomplete='new-password';button.textContent='Create beta account';authSwitch.hidden=true;return;
  }
  invitationToken=location.pathname.startsWith('/invite/')?decodeURIComponent(parts.at(-1)):'';
  if(invitationToken){
    mode='invite';const invitation=await jsonRequest(`/api/auth/invitations/${encodeURIComponent(invitationToken)}`);eyebrow.textContent='STUDIO INVITATION';title.textContent='Join the production';intro.textContent=`${invitation.email} was invited to ${invitation.project_access.map(item=>item.project_title).join(', ')}.`;
    field('display_name').hidden=false;form.elements.display_name.required=true;form.elements.display_name.value=invitation.display_name||'';field('email').hidden=true;form.elements.email.required=false;form.elements.password.autocomplete='new-password';authSwitch.hidden=true;return;
  }
  if(!status.auth_required){location.href='/';return;}
  if(location.pathname==='/signup'){
    mode='signup';if(!status.trial_signup_available)throw new Error('Trial signup will open as soon as Kizuna finishes studio setup.');eyebrow.textContent=`${status.trial_days}-DAY STUDIO TRIAL`;title.textContent='Create your first production';intro.textContent=`Explore the full workflow for ${status.trial_days} days. Trial video exports are limited to ${status.trial_export_seconds} seconds and include a Kizuna watermark.`;
    field('display_name').hidden=false;form.elements.display_name.required=true;form.elements.password.autocomplete='new-password';button.textContent='Start free trial';authSwitch.innerHTML='<a href="/login">Already have an account? Sign in</a>';const challenge=document.querySelector('#challenge-field');challenge.hidden=false;challenge.innerHTML=`<div class="cf-turnstile" data-sitekey="${status.turnstile_site_key}" data-theme="dark" data-size="flexible"></div>`;const script=document.createElement('script');script.src='https://challenges.cloudflare.com/turnstile/v0/api.js';script.async=true;script.defer=true;document.head.appendChild(script);return;
  }
  if(status.setup_required){
    mode='setup';eyebrow.textContent='FIRST-RUN SECURITY';title.textContent='Create the studio administrator';intro.textContent='This account will own existing productions and control studio-wide settings.';field('display_name').hidden=false;form.elements.display_name.required=true;field('bootstrap_key').hidden=false;form.elements.password.autocomplete='new-password';authSwitch.hidden=true;return;
  }
  if(location.pathname==='/setup'){location.href='/login';}
}
form.addEventListener('submit',async event=>{
  event.preventDefault();error.textContent='';button.disabled=true;const original=button.textContent;button.textContent='Working…';
  try{
    if(mode==='forgot'){const result=await jsonRequest('/api/auth/password/forgot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:form.elements.email.value})});title.textContent='Check your email';hideForm(result.message);return;}
    if(mode==='reset'){const result=await jsonRequest(`/api/auth/password/reset/${encodeURIComponent(flowToken)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:form.elements.password.value,confirm_password:form.elements.confirm_password.value})});title.textContent='Password updated';hideForm(result.message);return;}
    const body=['invite','beta-invite'].includes(mode)?{display_name:form.elements.display_name.value,password:form.elements.password.value}:{email:form.elements.email.value,password:form.elements.password.value};
    if(mode==='signup'){body.display_name=form.elements.display_name.value;body.challenge_token=form.querySelector('[name="cf-turnstile-response"]')?.value||'';}if(mode==='setup'){body.display_name=form.elements.display_name.value;body.bootstrap_key=form.elements.bootstrap_key.value;}
    const endpoint=mode==='beta-invite'?`/api/auth/beta-invitations/${encodeURIComponent(betaInvitationToken)}`:mode==='invite'?`/api/auth/invitations/${encodeURIComponent(invitationToken)}`:mode==='setup'?'/api/auth/setup':mode==='signup'?'/api/auth/trial':'/api/auth/login';const result=await jsonRequest(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(result.verification_required){title.textContent='Check your email';hideForm('We sent a single-use verification link. Verify your email before signing in.');return;}location.href='/';
  }catch(reason){error.textContent=reason.message;button.disabled=false;button.textContent=original;}
});
initialize().catch(reason=>{error.textContent=reason.message||'Kizuna could not check the studio security status.';});
