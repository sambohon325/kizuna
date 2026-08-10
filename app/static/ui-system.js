/* Small structural enhancements shared by every craft workspace. */
(function setupKizunaUiSystem(){
  const topbar=document.querySelector('.topbar'),account=document.querySelector('#account-nav'),signOut=document.querySelector('#sign-out'),newProject=document.querySelector('#new-project');
  if(topbar&&account&&signOut&&!topbar.querySelector('.account-actions')){
    const actions=document.createElement('div');actions.className='account-actions';topbar.insertBefore(actions,newProject);actions.append(account,signOut);
  }
  document.querySelectorAll('.rail button').forEach(button=>{
    const label=button.querySelector('span')?.textContent?.trim()||button.getAttribute('aria-label')||button.id.replace('-nav','').replaceAll('-',' ');
    button.title=label;if(!button.getAttribute('aria-label'))button.setAttribute('aria-label',label);
  });
  document.querySelectorAll('.workspace-view button, dialog button').forEach(button=>{
    const text=button.textContent.trim().toLowerCase();
    if(/delete|remove|revoke|reject/.test(text))button.dataset.intent='danger';
  });
  document.querySelectorAll('.empty').forEach(empty=>{empty.setAttribute('role','status');});
})();
