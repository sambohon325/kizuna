(function setupProcessNavigation(){
  const navigation=document.querySelector('.process-nav');
  if(!navigation)return;
  const phaseButtons=[...navigation.querySelectorAll('[data-phase-target]')];
  const closeMenu=()=>{
    navigation.dataset.menuOpen='false';
    phaseButtons.forEach(button=>button.setAttribute('aria-expanded','false'));
  };
  const openPhase=phase=>{
    const same=navigation.dataset.openPhase===phase;
    const opening=!same||navigation.dataset.menuOpen!=='true';
    navigation.dataset.openPhase=phase;
    navigation.dataset.menuOpen=String(opening);
    phaseButtons.forEach(button=>{
      const selected=button.dataset.phaseTarget===phase;
      button.setAttribute('aria-expanded',String(selected&&opening));
    });
  };
  phaseButtons.forEach(button=>button.addEventListener('click',event=>{
    event.stopPropagation();
    openPhase(button.dataset.phaseTarget);
  }));
  navigation.querySelectorAll('.process-submenu button').forEach(button=>button.addEventListener('click',closeMenu));
  navigation.querySelector('#productions-nav')?.addEventListener('click',closeMenu);
  document.addEventListener('click',event=>{if(!navigation.contains(event.target))closeMenu();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu();});
  closeMenu();
  window.closeProcessNavigationMenu=closeMenu;
})();
