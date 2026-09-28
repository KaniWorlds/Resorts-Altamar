const $ = selector => document.querySelector(selector);
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateText = value => new Date(value+'T12:00:00').toLocaleDateString('es-CL');
function localDate(offset=0){const d=new Date();d.setDate(d.getDate()+offset);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function message(text,error=false){$('#message').textContent=text;$('#message').className=error?'error':'';}
async function api(path,data){
  const response=await fetch('/api/'+path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||'No se pudo completar la operación.');
  return result;
}
async function refresh(){
  const rows=await api('reservations');
  $('#count').textContent=rows.filter(r=>r.status==='Confirmada').length;
  $('#reservations').innerHTML=rows.length?rows.map(r=>`<article class="reservation"><div class="reservation-top"><div><h3>${escapeHTML(r.guest)}</h3><span class="code">ALT-${String(r.id).padStart(4,'0')}</span></div><span class="badge ${r.status==='Cancelada'?'cancelled':''}">${escapeHTML(r.status)}</span></div><p>${escapeHTML(r.hotel)} · Habitación ${r.room}</p><div class="reservation-bottom"><span>${dateText(r.arrival)} → ${dateText(r.departure)}</span>${r.status==='Confirmada'?`<button class="cancel" data-id="${r.id}">Cancelar reserva</button>`:''}</div></article>`).join(''):'<p class="empty">Aún no hay reservas.<br>Crea la primera con el formulario.</p>';
}
$('#reservation-form').addEventListener('submit',async event=>{
  event.preventDefault();$('#save').disabled=true;message('');
  try{
    const result=await api('reservations',Object.fromEntries(new FormData(event.target)));
    message(result.message);event.target.elements.guest.value='';await refresh();
  }catch(error){message(error.message,true);}finally{$('#save').disabled=false;}
});
$('#reservations').addEventListener('click',async event=>{
  const button=event.target.closest('[data-id]');
  if(!button||!confirm('¿Cancelar esta reserva y liberar la habitación?'))return;
  button.disabled=true;
  try{const result=await api('cancel',{id:Number(button.dataset.id)});message(result.message);await refresh();}
  catch(error){message(error.message,true);button.disabled=false;}
});
$('#refresh').addEventListener('click',()=>refresh().catch(error=>message(error.message,true)));
$('#arrival').addEventListener('change',()=>{
  const d=new Date($('#arrival').value+'T12:00:00');d.setDate(d.getDate()+1);
  const next=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  $('#departure').min=next;if($('#departure').value<next)$('#departure').value=next;
});
(async()=>{
  $('#arrival').min=localDate();$('#arrival').value=localDate();$('#departure').min=localDate(1);$('#departure').value=localDate(1);
  try{
    const hotels=await api('hotels');
    $('#hotels').innerHTML=hotels.map(h=>`<option value="${h.id}">${escapeHTML(h.name)} · ${escapeHTML(h.region)}</option>`).join('');
    await refresh();
  }catch(error){message(error.message,true);}
})();
