const assetCategoryLabels={all:'All assets',character:'Characters',wardrobe:'Wardrobe',prop:'Props',environment:'Worlds & environments',building:'Buildings',furniture:'Furniture',vehicle:'Vehicles',effect:'Effects',audio:'Audio',reference:'Storyboards & references',other:'Other'};
const assetLibraryDialog=document.querySelector('#asset-dialog');
let activeAssetLibrary=null,activeAssetCategory='all',activeAssetKey='',activeAssetVersionId=0;

function normalizedAssetCategory(asset){return asset.kind==='background'?'environment':asset.kind==='reference'?'reference':asset.kind||'other';}
function assetGroupKey(asset){return `${asset.asset_type}:${asset.group_id}`;}
function assetPreview(asset,large=false){
  if((asset.mime_type||'').startsWith('image/'))return `<img src="${safe(asset.uri)}" alt="${safe(asset.name)}" loading="lazy">`;
  const icons={audio:'♫',effect:'✦',reference:'▤',prop:'◆',wardrobe:'♙',building:'▧',furniture:'▰',vehicle:'▷',character:'♟',environment:'▨'};
  return `<div class="asset-file-icon ${large?'large':''}"><i>${icons[normalizedAssetCategory(asset)]||'◇'}</i><span>${safe((asset.mime_type||'asset').split('/').pop())}</span></div>`;
}

function groupedAssets(){
  const groups=new Map();
  for(const asset of activeAssetLibrary?.assets||[]){const key=assetGroupKey(asset);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(asset);}
  return [...groups.entries()].map(([key,versions])=>{versions.sort((a,b)=>b.version-a.version||b.id-a.id);return{key,versions,asset:versions.find(item=>item.id===activeAssetVersionId)||versions.find(item=>item.active)||versions[0]};});
}

function renderAssetLibrary(){
  if(!activeAssetLibrary)return;
  const query=document.querySelector('#asset-search').value.trim().toLowerCase(),review=document.querySelector('#asset-review-filter').value,groups=groupedAssets();
  const counts={all:groups.length};for(const group of groups){const category=normalizedAssetCategory(group.asset);counts[category]=(counts[category]||0)+1;}
  document.querySelector('#asset-categories').innerHTML=Object.entries(assetCategoryLabels).map(([key,label])=>`<button type="button" class="${key===activeAssetCategory?'active':''}" data-asset-category="${key}"><span>${safe(label)}</span><b>${counts[key]||0}</b></button>`).join('');
  const filtered=groups.filter(group=>{const asset=group.asset,haystack=`${asset.name} ${asset.description||''} ${(asset.tags||[]).join(' ')} ${asset.source_tool||''}`.toLowerCase();return(activeAssetCategory==='all'||normalizedAssetCategory(asset)===activeAssetCategory)&&(review==='all'||asset.review_status===review)&&(!query||haystack.includes(query));});
  const pending=groups.filter(group=>group.asset.review_status==='pending').length;
  document.querySelector('#asset-summary').textContent=`${filtered.length} asset${filtered.length===1?'':'s'}${pending?` · ${pending} need review`:''}`;
  document.querySelector('#asset-grid').innerHTML=filtered.length?filtered.map(group=>{const asset=group.asset;return `<button type="button" class="asset-card ${group.key===activeAssetKey?'active':''}" data-asset-key="${safe(group.key)}"><span class="asset-card-preview">${assetPreview(asset)}</span><span class="asset-card-copy"><small>${safe(assetCategoryLabels[normalizedAssetCategory(asset)]||normalizedAssetCategory(asset))}</small><b>${safe(asset.name)}</b><span>${safe((asset.tags||[]).slice(0,3).join(' · ')||asset.source_tool||'Production asset')}</span></span><span class="asset-card-meta"><i class="review-${safe(asset.review_status)}">${safe(asset.review_status)}</i><em>v${asset.version}${group.versions.length>1?` · ${group.versions.length} versions`:''}</em></span></button>`;}).join(''):'<div class="asset-empty"><b>No assets match this view.</b><span>Try another category or add a file you are authorized to use.</span></div>';
  document.querySelectorAll('[data-asset-category]').forEach(button=>button.onclick=()=>{activeAssetCategory=button.dataset.assetCategory;renderAssetLibrary();});
  document.querySelectorAll('[data-asset-key]').forEach(button=>button.onclick=()=>{activeAssetKey=button.dataset.assetKey;activeAssetVersionId=groupedAssets().find(item=>item.key===activeAssetKey)?.asset.id||0;renderAssetLibrary();renderAssetInspector();});
  if(activeAssetKey&&!groups.some(group=>group.key===activeAssetKey)){activeAssetKey='';renderAssetInspector();}
}

function renderAssetInspector(){
  const group=groupedAssets().find(item=>item.key===activeAssetKey),host=document.querySelector('#asset-inspector');
  if(!group){host.innerHTML='<div class="asset-inspector-empty">Choose an asset to review it or use it in this production.</div>';return;}
  const asset=group.asset,isLibrary=asset.asset_type==='library';
  host.innerHTML=`<div class="asset-inspector-preview">${assetPreview(asset,true)}</div><div class="asset-inspector-heading"><span>${safe(assetCategoryLabels[normalizedAssetCategory(asset)]||asset.kind)}</span><h3>${safe(asset.name)}</h3><p>${safe(asset.description||'No description yet.')}</p></div><div class="asset-state-row"><span class="review-${safe(asset.review_status)}">${safe(asset.review_status)}</span><span class="rights-${safe(asset.rights_status||'pending')}">${safe((asset.rights_status||'pending').replace('_',' '))}</span></div>${isLibrary?`<form id="asset-metadata-form"><label>Name<input name="name" value="${safe(asset.name)}" maxlength="160"></label><label>Category<select name="category">${assetCategoryOptions(normalizedAssetCategory(asset))}</select></label><label>Description<textarea name="description" rows="3">${safe(asset.description||'')}</textarea></label><label>Tags<input name="tags" value="${safe((asset.tags||[]).join(', '))}"></label><label>Rights<select name="rights_status"><option value="owned">Owned</option><option value="licensed">Licensed</option><option value="public_domain">Public domain</option><option value="generated">Generated</option><option value="pending">Needs review</option></select></label><label>Rights notes<textarea name="rights_notes" rows="2">${safe(asset.rights_notes||'')}</textarea></label><label>Source tool<input name="source_tool" value="${safe(asset.source_tool||'creator upload')}"></label><button class="primary" type="submit">Save details</button></form>`:`<div class="asset-managed-note">This asset is managed in ${asset.asset_type==='character'?'Character Studio':asset.asset_type==='background'?'Worlds':'Storyboard & Shot Planner'}. Approval and version selection are available here.</div>`}<section class="asset-approval"><h4>Production approval</h4><textarea id="asset-review-notes" rows="2" placeholder="Review notes">${safe(asset.review_notes||'')}</textarea><div><button type="button" data-asset-review="rejected">Reject</button><button type="button" data-asset-review="approved">Approve</button><button class="primary" type="button" data-asset-review="selected">Use in production</button></div></section><section class="asset-versions"><div><h4>Versions</h4>${isLibrary?'<label class="new-version">Add version<input id="asset-version-file" type="file"></label>':''}</div>${group.versions.map(item=>`<button type="button" data-asset-version="${item.id}" class="${item.id===asset.id?'active':''}"><span>v${item.version}</span><b>${safe(item.name)}</b><small>${safe(item.review_status)}${item.active?' · active':''}</small></button>`).join('')}</section>`;
  if(isLibrary){const rights=host.querySelector('[name="rights_status"]');rights.value=asset.rights_status||'pending';host.querySelector('#asset-metadata-form').onsubmit=saveAssetMetadata;const file=host.querySelector('#asset-version-file');file.onchange=uploadAssetVersion;}
  host.querySelectorAll('[data-asset-review]').forEach(button=>button.onclick=()=>reviewAsset(button.dataset.assetReview));
  host.querySelectorAll('[data-asset-version]').forEach(button=>button.onclick=()=>{activeAssetVersionId=Number(button.dataset.assetVersion);renderAssetInspector();});
}

function assetCategoryOptions(selected='reference'){return Object.entries(assetCategoryLabels).filter(([key])=>key!=='all').map(([key,label])=>`<option value="${key}" ${key===selected?'selected':''}>${label}</option>`).join('');}

async function loadAssetLibrary(projectId){activeAssetLibrary=await api(`/api/projects/${projectId}/asset-library`);if(activeAssetKey&&!groupedAssets().some(group=>group.key===activeAssetKey))activeAssetKey='';renderAssetLibrary();renderAssetInspector();}
async function openAssetLibrary(projectId){
  openWorkspace(assetLibraryDialog);const select=document.querySelector('#asset-project'),chosen=projectId||currentFlowProject()?.id||projects[0]?.id;select.innerHTML=projects.map(project=>`<option value="${project.id}">${safe(project.title)}</option>`).join('');if(chosen)select.value=chosen;activeAssetKey='';activeAssetVersionId=0;if(chosen)await loadAssetLibrary(Number(chosen));else document.querySelector('#asset-grid').innerHTML='<div class="asset-empty">Create a production before adding assets.</div>';
}

function csrfHeaders(file){const token=(document.cookie.match(/(?:^|; )kizuna_csrf=([^;]+)/)||[])[1]||'';return{'Content-Type':file.type||'application/octet-stream',...(token?{'X-Kizuna-CSRF':decodeURIComponent(token)}:{})};}
async function uploadAssetRequest(url,file){const response=await fetch(url,{method:'POST',headers:csrfHeaders(file),body:file});if(!response.ok){let message;try{message=(await response.json()).detail;}catch{message=await response.text();}throw new Error(message||'Upload failed');}return response.json();}

async function importAsset(event){
  event.preventDefault();const file=document.querySelector('#asset-file').files[0],projectId=Number(document.querySelector('#asset-project').value),status=document.querySelector('#asset-upload-status');if(!file||!projectId)return;const params=new URLSearchParams({filename:file.name,name:document.querySelector('#asset-name').value||file.name.replace(/\.[^.]+$/,''),category:document.querySelector('#asset-category').value,rights_status:document.querySelector('#asset-rights').value,rights_notes:document.querySelector('#asset-rights-notes').value,source_tool:document.querySelector('#asset-source').value,tags:document.querySelector('#asset-tags').value});status.textContent='Importing and indexing asset…';try{const asset=await uploadAssetRequest(`/api/projects/${projectId}/library-assets/upload?${params}`,file);activeAssetKey=assetGroupKey({...asset,asset_type:'library',group_id:asset.group_key});event.target.reset();document.querySelector('#asset-source').value='creator upload';document.querySelector('#asset-upload-panel').hidden=true;await loadAssetLibrary(projectId);}catch(error){status.textContent=error.message;}
}

async function saveAssetMetadata(event){event.preventDefault();const group=groupedAssets().find(item=>item.key===activeAssetKey),asset=group?.asset;if(!asset)return;const form=event.target,payload={name:form.elements.name.value,category:form.elements.category.value,description:form.elements.description.value,tags:form.elements.tags.value.split(',').map(item=>item.trim()).filter(Boolean),rights_status:form.elements.rights_status.value,rights_notes:form.elements.rights_notes.value,source_tool:form.elements.source_tool.value};await api(`/api/library-assets/${asset.id}`,{method:'PUT',body:JSON.stringify(payload)});await loadAssetLibrary(activeAssetLibrary.project_id);}
async function reviewAsset(action){const group=groupedAssets().find(item=>item.key===activeAssetKey),asset=group?.asset;if(!asset)return;await api(`/api/assets/${asset.asset_type}/${asset.id}/review`,{method:'PUT',body:JSON.stringify({status:action==='selected'?'approved':action,selected:action==='selected',notes:document.querySelector('#asset-review-notes').value})});await loadAssetLibrary(activeAssetLibrary.project_id);}
async function uploadAssetVersion(event){const file=event.target.files[0],group=groupedAssets().find(item=>item.key===activeAssetKey),asset=group?.asset;if(!file||!asset)return;await uploadAssetRequest(`/api/library-assets/${asset.id}/versions/upload?filename=${encodeURIComponent(file.name)}`,file);await loadAssetLibrary(activeAssetLibrary.project_id);}

document.querySelector('#assets-nav').onclick=()=>openAssetLibrary();
document.querySelector('#asset-close').onclick=()=>closeWorkspace();
document.querySelector('#asset-project').onchange=event=>{activeAssetKey='';loadAssetLibrary(Number(event.target.value));};
document.querySelector('#asset-search').oninput=renderAssetLibrary;
document.querySelector('#asset-review-filter').onchange=renderAssetLibrary;
document.querySelector('#asset-category').innerHTML=assetCategoryOptions('reference');
document.querySelector('#asset-upload-toggle').onclick=()=>document.querySelector('#asset-upload-panel').hidden=false;
document.querySelector('#asset-upload-cancel').onclick=()=>document.querySelector('#asset-upload-panel').hidden=true;
document.querySelector('#asset-upload-form').onsubmit=importAsset;
window.openAssetLibraryReady=openAssetLibrary;
