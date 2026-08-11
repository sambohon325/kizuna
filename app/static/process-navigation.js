(function setupProcessNavigation(){
  const navigation=document.querySelector('.process-nav');
  if(!navigation)return;
  const openPhase=phase=>{
    navigation.dataset.openPhase=phase;
    navigation.querySelectorAll('[data-phase-target]').forEach(button=>{
      const selected=button.dataset.phaseTarget===phase;
      button.classList.toggle('active',selected);
      button.setAttribute('aria-selected',String(selected));
    });
  };
  navigation.querySelectorAll('[data-phase-target]').forEach(button=>button.addEventListener('click',()=>openPhase(button.dataset.phaseTarget)));
  openPhase(navigation.dataset.activePhase||'home');
})();
