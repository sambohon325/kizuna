(() => {
  const config = window.KIZUNA_MARKETING || {};
  const appUrl = String(config.appUrl || "https://app.kizuna.com").replace(/\/$/, "");
  document.querySelectorAll('[data-app-link="signup"]').forEach(link => link.href = `${appUrl}/signup`);
  document.querySelectorAll('[data-app-link="login"]').forEach(link => link.href = `${appUrl}/login`);
  document.querySelectorAll('[data-year]').forEach(node => node.textContent = new Date().getFullYear());

  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#site-nav');
  menu?.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') === 'true';
    menu.setAttribute('aria-expanded', String(!open));
    nav?.classList.toggle('open', !open);
  });
  nav?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    menu?.setAttribute('aria-expanded', 'false');
    nav.classList.remove('open');
  }));

  const header = document.querySelector('[data-header]');
  const updateHeader = () => header?.classList.toggle('scrolled', window.scrollY > 24);
  updateHeader();
  window.addEventListener('scroll', updateHeader, {passive: true});

  const details = [
    {label:'IMAGINE', title:'Find the heart of the story.', body:'Develop the premise, release plan, narrative structure, creative direction, characters, and world. Ask for guidance or open the full craft controls.', note:'Story intent remains connected to every downstream decision.'},
    {label:'DIRECT', title:'Turn intention into time and motion.', body:'Build scenes and coverage, assemble the picture, shape performance, and create dialogue, music, ambience, and effects on connected timelines.', note:'Continuity and production context travel with every shot.'},
    {label:'FINISH', title:'Bring every layer into the final frame.', body:'Composite approved assets, preview motion, coordinate local or cloud rendering, run compliance checks, and prepare delivery masters.', note:'Approvals, rights, versions, and audit history remain visible.'},
    {label:'GROW', title:'Let one world support many stories.', body:'Adapt format, runtime, screen shape, and release plan while preserving the production’s cast, lore, assets, creative history, and decisions.', note:'The roadmap carries the same story foundation into future Kizuna suites.'}
  ];
  const workflowButtons = [...document.querySelectorAll('[data-workflow-step]')];
  const workflowDetail = document.querySelector('[data-workflow-detail]');
  workflowButtons.forEach(button => button.addEventListener('click', () => {
    const index = Number(button.dataset.workflowStep);
    const item = details[index];
    workflowButtons.forEach(node => node.classList.toggle('active', node === button));
    if (workflowDetail && item) {
      workflowDetail.classList.remove('swap');
      void workflowDetail.offsetWidth;
      workflowDetail.innerHTML = `<span>${item.label}</span><h3>${item.title}</h3><p>${item.body}</p><em>${item.note}</em>`;
      workflowDetail.classList.add('swap');
    }
  }));

  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
  const articleBody = value => String(value || '').split(/\n{2,}/).map(block => {
    const text = block.trim();
    if (text.startsWith('## ')) return `<h3>${escapeHTML(text.slice(3))}</h3>`;
    if (text.startsWith('> ')) return `<blockquote>${escapeHTML(text.slice(2))}</blockquote>`;
    return `<p>${escapeHTML(text)}</p>`;
  }).join('');
  const articleDialog = document.querySelector('#article-dialog');
  document.querySelector('[data-close-article]')?.addEventListener('click', () => articleDialog.close());
  articleDialog?.addEventListener('click', event => { if (event.target === articleDialog) articleDialog.close(); });

  async function openArticle(slug) {
    const host = document.querySelector('[data-article-content]');
    host.innerHTML = '<p>Loading studio note…</p>';
    articleDialog.showModal();
    try {
      const response = await fetch(`/api/blog/${encodeURIComponent(slug)}`);
      if (!response.ok) throw new Error('This studio note is not available.');
      const post = await response.json();
      host.innerHTML = `<small>${escapeHTML(post.category)}</small><h2>${escapeHTML(post.title)}</h2><div class="article-meta">${escapeHTML(post.author)} · ${new Date(post.published_at).toLocaleDateString()}</div><div class="article-body">${articleBody(post.body)}</div>`;
      history.replaceState(null, '', `/blog/${encodeURIComponent(post.slug)}`);
    } catch (error) { host.innerHTML = `<p>${escapeHTML(error.message)}</p>`; }
  }
  articleDialog?.addEventListener('close', () => { if (location.pathname.startsWith('/blog/')) history.replaceState(null, '', '/#journal'); });

  async function loadBlog() {
    const host = document.querySelector('[data-blog-list]');
    try {
      const response = await fetch('/api/blog');
      if (!response.ok) throw new Error();
      const posts = await response.json();
      if (!posts.length) return;
      host.innerHTML = posts.map(post => `<article class="journal-card ${post.featured?'featured':''}" tabindex="0" role="link" data-blog-slug="${escapeHTML(post.slug)}"><small>${escapeHTML(post.category)}</small><h3>${escapeHTML(post.title)}</h3><p>${escapeHTML(post.excerpt)}</p><footer><span>${escapeHTML(post.author)}</span><span>${new Date(post.published_at).toLocaleDateString()}</span></footer></article>`).join('');
      host.querySelectorAll('[data-blog-slug]').forEach(card => {
        card.addEventListener('click', () => openArticle(card.dataset.blogSlug));
        card.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openArticle(card.dataset.blogSlug); } });
      });
      const route = location.pathname.match(/^\/blog\/([^/]+)$/);
      if (route) openArticle(decodeURIComponent(route[1]));
    } catch { host.innerHTML = '<div class="journal-empty">Studio notes are temporarily unavailable.</div>'; }
  }

  async function submitPublicForm(form, endpoint, successMessage) {
    const result = form.querySelector('.form-result');
    const button = form.querySelector('button[type="submit"]');
    result.classList.remove('error'); button.disabled = true; button.textContent = 'Sending…';
    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'We could not send this yet. Please try again.');
      result.textContent = endpoint === '/api/tickets' ? `${successMessage} Reference: ${data.reference}.` : successMessage;
      form.reset();
    } catch (error) { result.textContent = error.message; result.classList.add('error'); }
    finally { button.disabled = false; button.innerHTML = endpoint === '/api/tickets' ? 'Submit ticket <span>↗</span>' : 'Apply for beta <span>↗</span>'; }
  }
  document.querySelector('#beta-form')?.addEventListener('submit', event => { event.preventDefault(); submitPublicForm(event.currentTarget, '/api/beta', 'Thank you. Your beta application has been received.'); });
  document.querySelector('#ticket-form')?.addEventListener('submit', event => { event.preventDefault(); submitPublicForm(event.currentTarget, '/api/tickets', 'Your ticket has been received.'); });
  document.querySelector('#public-help-form')?.addEventListener('submit', async event => {
    event.preventDefault();const form=event.currentTarget,host=form.querySelector('[data-public-help-answer]'),button=form.querySelector('button');host.hidden=false;host.innerHTML='<p>Reading the Kizuna manuals…</p>';button.disabled=true;
    try{const response=await fetch('/api/help/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:form.elements.question.value.trim()})}),result=await response.json();if(!response.ok)throw new Error(result.detail||'Help is temporarily unavailable.');host.innerHTML=`<b>${result.grounded?'Answer from Kizuna Help':'No published answer found'}</b><p>${escapeHTML(result.answer)}</p>${result.sources.length?`<div>${result.sources.map(source=>`<a href="${escapeHTML(source.source_path)}" target="_blank" rel="noopener"><span>${escapeHTML(source.title)}</span><small>${escapeHTML(source.section)} ↗</small></a>`).join('')}</div>`:''}`;}catch(error){host.innerHTML=`<b>Help is temporarily unavailable</b><p>${escapeHTML(error.message)}</p>`;}finally{button.disabled=false;}
  });

  const socialLabels = {instagram:'Instagram',youtube:'YouTube',tiktok:'TikTok',x:'X',linkedin:'LinkedIn',discord:'Discord'};
  const socialHost = document.querySelector('[data-social-links]');
  const socialEntries = Object.entries(config.socials || {}).filter(([,url]) => url);
  if (socialHost) socialHost.innerHTML = socialEntries.map(([key,url]) => `<a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(socialLabels[key] || key)} ↗</a>`).join('');
  loadBlog();

  const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add('visible'); reveal.unobserve(entry.target); }
  }), {threshold: .12, rootMargin: '0px 0px -40px'});
  document.querySelectorAll('.reveal').forEach(node => reveal.observe(node));
})();
