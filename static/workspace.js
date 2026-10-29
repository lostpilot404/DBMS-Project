/* Personal role workspace. Persisted API data only; backend policy is authoritative. */
'use strict';
window.HMS_ROLE_BOOT = async function (legacy) {
  const main=document.getElementById('mainContent'),nav=document.getElementById('primaryNav'),modal=document.getElementById('modalRoot');
  let workspace=null, identity=null, currentForm='',page=1,search='',epoch=0;
  window.hmsAdminMode=false;
  const esc=(s)=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels={manager:'Manager',doctor:'Doctor',patient:'Patient',receptionist:'Reception',nurse:'Ward nursing',pharmacist:'Pharmacy',cashier:'Billing & cashier',lab:'Laboratory',maintenance:'Maintenance'};
  function expired(){epoch++;window.hmsAdminMode=false;identity=null;window.hmsUser=null;window.hmsCsrf='';workspace=null;modal.innerHTML='';nav.innerHTML='';legacy.clear();loginScreen();}
  window.hmsExpired=expired;
  async function call(url,options={}) {
    const marker=window.hmsCsrf;
    const r=await fetch(url,{...options,headers:{'Content-Type':'application/json','X-CSRF-Token':window.hmsCsrf||'',...(options.headers||{})}});
    const body=await r.json();if(marker&&marker!==window.hmsCsrf)throw new Error('Session changed; stale response ignored.');if(!r.ok){if(r.status===401&&url!='/api/auth/login')expired();const error=new Error(body.error?.message||'Request failed');error.code=body.error?.code;error.status=r.status;throw error;}return body.data;
  }
  function loginScreen(message=''){
    document.getElementById('pageTitle').textContent='Personal sign in';document.title='Sign in · CarePoint';
    main.innerHTML=`<section class="identity-card"><span class="eyebrow">CarePoint · Hospital workspace</span><h2>Welcome back</h2><p>Use your personal account. Access is limited to your assigned role and patients.</p><form id="identityLogin"><label>Username<input class="form-control" name="username" autocomplete="username" required maxlength="100"></label><label>Password<input class="form-control" name="password" type="password" autocomplete="current-password" required maxlength="128"></label><p class="form-error" id="identityError" role="alert">${esc(message)}</p><button class="button button-primary" type="submit">Sign in</button></form><p class="field-hint">No default credentials. Ask a manager for an activated account. Synthetic academic demo; not a production clinical service.</p></section>`;
  }
  const f=(key,label,type='text',source=null,optional=false)=>({key,label,type,source,optional});
  const patient=f('patient_id','Patient','select','patients'),doctor=f('doctor_id','Doctor','select','doctors'),enc=f('encounter_id','Consultation','select','consultations'),admission=f('admission_id','Admission','select','admissions');
  const forms={
    register:{label:'Register patient',roles:['manager','receptionist'],url:'/api/patients',fields:[f('patient_name','Full name'),f('date_of_birth','Date of birth','date'),f('gender','Gender','select',['M','F','O']),f('phone','Phone','tel',null,true),f('address','Address','text',null,true)]},
    book:{label:'Book appointment',roles:['manager','receptionist'],url:'/api/appointments',fields:[patient,doctor,f('appointment_date','Hospital date','date'),f('appointment_time','Time','time'),f('duration_minutes','Minutes','number')]},
    admission:{label:'Admit patient',roles:['manager','receptionist'],url:'/api/admissions',fields:[patient,f('room_id','Available room','select','rooms'),f('admission_date','Hospital admission date','date')]},
    reschedule:{label:'Reschedule scheduled appointment',roles:['manager','receptionist'],url:p=>`/api/appointments/${p.appointment_id}`,method:'PUT',fields:[f('appointment_id','Scheduled appointment','select','appointments'),doctor,f('appointment_date','New hospital date','date'),f('appointment_time','New time','time'),f('duration_minutes','Minutes','number')]},
    request_appointment:{label:'Request appointment / follow-up',roles:['patient','doctor','manager'],fields:[patient,doctor,f('encounter_id','Related consultation (follow-up)','select','consultations',true),f('requested_date','Requested hospital date','date'),f('requested_time','Requested time','time'),f('reason','Reason','text',null,true)]},
    review_request:{label:'Accept or reject request',roles:['receptionist','manager'],fields:[f('request_id','Request','select','requests'),f('decision','Decision','select',['Accepted','Rejected']),f('duration_minutes','Minutes','number')]},
    consultation:{label:'Begin consultation',roles:['doctor','manager'],fields:[patient,doctor,f('appointment_id','Waiting appointment','select','appointments',true),f('admission_id','OR active inpatient admission','select','admissions',true),f('diagnosis','Working diagnosis','textarea',null,true),f('clinical_notes','Clinical notes','textarea',null,true)]},
    complete_consultation:{label:'Complete consultation / release notes',roles:['doctor','manager'],fields:[enc,f('diagnosis','Final diagnosis','textarea'),f('clinical_notes','Final notes (visible to patient on completion)','textarea')]},
    prescribe:{label:'Prescribe medicine',roles:['doctor','manager'],fields:[enc,f('medicine_id','Medicine','select','medicines'),f('ordered_quantity','Ordered units','number'),f('dosage','Dosage instructions'),f('duration','Duration')]},
    order_test:{label:'Order laboratory test',roles:['doctor','manager'],fields:[enc,f('test_id','Test','select','test_catalog')]},
    result:{label:'Record test result',roles:['lab','manager'],fields:[f('order_id','Test order','select','tests'),f('result_text','Result (retained, cannot overwrite)','textarea')]},
    observation:{label:'Record ward observation',roles:['nurse','manager'],fields:[admission,f('observation','Observation','textarea')]},
    transfer:{label:'Transfer active admission',roles:['nurse','manager'],url:p=>`/api/admissions/${p.admission_id}`,method:'PUT',fields:[admission,f('room_id','Available destination room','select','rooms')]},
    discharge:{label:'Discharge admission',roles:['nurse','manager'],url:p=>`/api/admissions/${p.admission_id}/discharge`,fields:[admission,f('discharge_date','Discharge hospital date','date')]},
    medicine:{label:'Create medicine catalogue entry',roles:['pharmacist','manager'],url:'/api/medicines',fields:[f('medicine_name','Medicine'),f('manufacturer','Manufacturer','text',null,true),f('price','Unit billing price (INR)','number')]},
    receive_batch:{label:'Receive new medicine batch',roles:['pharmacist','manager'],fields:[f('medicine_id','Medicine','select','medicines'),f('batch_number','Batch number'),f('expires_on','Expiry hospital date','date'),f('quantity','Received units','number')]},
    dispense:{label:'Dispense prescription',roles:['pharmacist','manager'],fields:[f('prescription_id','Prescription','select','prescriptions'),f('batch_id','Matching in-date batch','select','batches'),f('quantity','Units','number')]},
    prepare_bill:{label:'Prepare itemized care invoice',roles:['cashier','manager'],fields:[f('encounter_id','Consultation OR leave blank for admission','select','billing_encounters',true),f('admission_id','Discharged admission','select','billing_admissions',true),f('room_charge','Agreed room charge (INR)','number',null,true),f('notes','Administrative notes','text',null,true)]},
    staff:{label:'Create staff record',roles:['manager'],fields:[f('full_name','Full name'),f('staff_kind','Staff role','select',['manager','receptionist','nurse','pharmacist','cashier','lab','maintenance']),f('phone','Phone','tel',null,true)]},
    update_staff:{label:'Edit / activate staff',roles:['manager'],fields:[f('staff_id','Staff','select','staff'),f('full_name','Updated name','text',null,true),f('phone','Phone','tel',null,true),f('is_active','Active','select',['Y','N'])]},
    user:{label:'Create personal account',roles:['manager'],url:'/api/admin/users',fields:[f('username','Username'),f('password','Initial password (12–128 characters)','password'),f('role','Role','select',Object.keys(labels)),f('patient_id','Patient link (patients only)','select','patients',true),f('doctor_id','Doctor link (doctors only)','select','doctors',true),f('staff_id','Staff link (all staff roles)','select','staff',true)]},
    account:{label:'Activate / deactivate account',roles:['manager'],url:p=>`/api/admin/users/${p.user_id}`,method:'PUT',fields:[f('user_id','Account','select','users'),f('is_active','Active','select',['Y','N'])]},
    role:{label:'Change role / reset password',roles:['manager'],url:p=>`/api/admin/users/${p.user_id}`,method:'PUT',fields:[f('user_id','Account','select','users'),f('role','Role','select',Object.keys(labels)),f('password','New password (optional)','password',null,true),f('patient_id','Patient link','select','patients',true),f('doctor_id','Doctor link','select','doctors',true),f('staff_id','Staff link','select','staff',true)]},
    assign_doctor:{label:'Assign inpatient / ongoing doctor',roles:['manager'],fields:[patient,doctor,f('is_active','Active','select',['Y','N'])]},
    assign_ward:{label:'Assign ward nurse',roles:['manager'],fields:[admission,f('user_id','Nurse account','select','users'),f('is_active','Active','select',['Y','N'])]},
    settings:{label:'Configure consultation fee',roles:['manager'],fields:[f('consultation_fee','Consultation fee (INR)','number')]},
    update_test_catalog:{label:'Edit / deactivate lab catalogue',roles:['manager'],fields:[f('test_id','Existing test','select','test_catalog'),f('test_name','Updated test name','text',null,true),f('fee','New fee','number',null,true),f('is_active','Active','select',['Y','N'])]},
    test_catalog:{label:'Create lab test',roles:['manager'],fields:[f('test_name','Test name'),f('fee','Test fee (INR)','number')]},
    maintenance_request:{label:'Request room maintenance',roles:['manager','nurse','receptionist'],fields:[f('room_id','Room','select','rooms'),f('description','Repair request')]},
    maintenance_start:{label:'Start room maintenance',roles:['maintenance','manager'],fields:[f('task_id','Open task','select','maintenance')]},
    maintenance_complete:{label:'Complete room maintenance',roles:['maintenance','manager'],fields:[f('task_id','Open task','select','maintenance')]},
    password:{label:'Change my password',roles:Object.keys(labels),url:'/api/auth/password',fields:[f('current_password','Current password','password'),f('new_password','New password (12–128 characters)','password')]}
  };
  const reason=f('reason','Reason / authorizing evidence (retained)','textarea');
  const corrections={
    amend_consultation:{label:'Append completed consultation amendment',roles:['doctor','manager'],fields:[enc,f('content','Amendment; original remains unchanged','textarea'),reason]},
    amend_result:{label:'Append laboratory result amendment',roles:['lab','manager'],fields:[f('result_id','Original result ID','select','tests'),f('content','Corrected result / explanation','textarea'),reason]},
    cancel_rx:{label:'Cancel remaining prescription',roles:['doctor','manager'],fields:[f('prescription_id','Unfulfilled / partially filled prescription','select','prescriptions'),reason]},
    cancel_test:{label:'Cancel unperformed test order',roles:['doctor','manager'],fields:[f('order_id','Unperformed test','select','tests'),reason]},
    return_stock:{label:'Record medicine return (financial review separate)',roles:['pharmacist','manager'],fields:[f('dispense_id','Original dispense','select','dispensing'),f('quantity','Returned units','number'),f('disposition','Verified disposition','select',['Restock','Quarantine']),reason]},
    write_off:{label:'Write off damaged / expired batch stock',roles:['pharmacist','manager'],fields:[f('batch_id','Batch','select','batches'),f('quantity','Unavailable units','number'),reason]},
    adjust_add:{label:'Authorized positive batch count correction',roles:['manager'],fields:[f('batch_id','Verified batch','select','batches'),f('quantity','Additional counted units','number'),reason]},
    adjust_remove:{label:'Authorized negative batch count correction',roles:['manager'],fields:[f('batch_id','Batch','select','batches'),f('quantity','Missing units','number'),reason]},
    profile:{label:'Update my contact profile',roles:['patient'],fields:[f('phone','My phone (blank clears)','tel',null,true),f('address','My address (blank clears)','text',null,true)]},
    cancel_appointment:{label:'Cancel my future scheduled appointment',roles:['patient'],fields:[f('appointment_id','My scheduled appointment','select','appointments'),reason]},
    reschedule_appointment:{label:'Reschedule my future appointment (same doctor)',roles:['patient'],fields:[f('appointment_id','My scheduled appointment','select','appointments'),f('appointment_date','New hospital date','date'),f('appointment_time','New time','time'),reason]},
    refund:{label:'Authorize linked receipt refund + price credit',roles:['manager'],fields:[f('bill_id','Invoice','select','bills'),f('payment_id','Original receipt','select','payments'),f('amount','Refund INR','number'),reason]},
    void_invoice:{label:'Void unpaid administrative invoice (retain history)',roles:['manager'],fields:[f('bill_id','Unpaid administrative invoice','select','bills'),reason]}
  };
  for(const [key,label]of Object.entries({credit:'Credit unpaid charges',debit:'Add reasoned financial debit',writeoff:'Write off unpaid financial debt'}))corrections[key]={label,roles:['manager'],fields:[f('bill_id','Invoice','select','bills'),f('amount','Correction INR','number'),reason]};
  for(const [key,spec]of Object.entries(corrections))forms[key]={...spec,journaled:true,url:`/api/corrections/${key}`};
  for(const key of ['credit','writeoff','refund'])forms[key].fields.splice(-1,0,f('stock_event_id','Optional billed medicine-return event ID','select','return_review',true));
  forms.refund.roles=['manager','cashier'];
  forms.receive_batch.journaled=true;
  function options(field){
    if(Array.isArray(field.source))return field.source.map(v=>[v,v]);
    const rows=workspace.queues[field.source]||[];
    const choiceKey=field.key==='result_id'?'result_id':null;
    const keys={rooms:'room_id',patients:'patient_id',doctors:'doctor_id',consultations:'encounter_id',admissions:'admission_id',appointments:'appointment_id',requests:'request_id',medicines:'medicine_id',test_catalog:'test_id',tests:'order_id',batches:'batch_id',prescriptions:'prescription_id',staff:'staff_id',users:'user_id',maintenance:'task_id',billing_admissions:'admission_id',billing_encounters:'encounter_id',dispensing:'dispense_id',bills:'bill_id',payments:'payment_id',return_review:'event_id'};
    return rows.filter(r=>!(field.source==='rooms'&&['transfer','admission'].includes(currentForm)&&r.availability_status!=='Available')&&!(field.source==='admissions'&&r.discharge_date)&&!(field.source==='maintenance'&&r.status!==(currentForm==='maintenance_complete'?'InProgress':'Open'))&&!(field.source==='tests'&&currentForm==='result'&&r.status!=='Ordered')&&!(field.source==='requests'&&currentForm==='review_request'&&r.status!=='Pending')&&!(field.key==='appointment_id'&&r.status!==(['reschedule','cancel_appointment','reschedule_appointment'].includes(currentForm)?'Scheduled':'Waiting'))&&!(field.source==='consultations'&&r.status!=='Open'&&!['request_appointment','amend_consultation'].includes(currentForm))&&!(field.key==='user_id'&&currentForm==='assign_ward'&&r.role!=='nurse')).filter(r=>!(choiceKey&&!r[choiceKey])&&!(currentForm==='amend_consultation'&&field.source==='consultations'&&r.status!=='Completed')&&!(currentForm==='cancel_test'&&field.source==='tests'&&r.status!=='Ordered')).map(r=>[r[choiceKey||keys[field.source]],`#${r[choiceKey||keys[field.source]]} · ${r.patient_name||r.doctor_name||r.medicine_name||r.test_name||r.full_name||r.username||r.room_number||r.description||''} ${r.status||r.expiry_alert||''}`]);
  }
  function renderForm(){
    const spec=forms[currentForm];if(!spec)return;
    const visible=spec.fields.map(field=>identity.role==='cashier'&&field.key==='stock_event_id'?{...field,optional:false,label:'Required recorded billed-return event ID'}:field).filter(f=>!(identity.role==='patient'&&f.key==='patient_id')&&!(identity.role==='doctor'&&f.key==='doctor_id'));
    document.getElementById('roleFields').innerHTML=visible.map(field=>{
      const contact=currentForm==='profile'?(workspace.queues.patients||[]).find(r=>r.patient_id===identity.patient_id):null;
      const value=contact&&['phone','address'].includes(field.key)?contact[field.key]??'':field.type==='date'?(['date_of_birth','expires_on'].includes(field.key)?'':legacy.today()):field.key==='duration_minutes'?'30':'';
      const recordChoice=typeof field.source==='string';
      const control=recordChoice?`<input class="form-control" name="${field.key}" type="text" inputmode="numeric" pattern="[1-9][0-9]{0,9}" maxlength="10" list="choices_${field.key}" ${field.optional?'':'required'}><datalist id="choices_${field.key}">${options(field).map(([id,label])=>`<option value="${esc(id)}">${esc(label)}</option>`).join('')}</datalist><small class="field-hint">Choose a suggested ID or enter another permitted ID from the queues. Access is checked by the server.</small>`:field.source?`<select class="form-control" name="${field.key}" ${field.optional?'':'required'}><option value="">Choose…</option>${options(field).map(([id,label])=>`<option value="${esc(id)}">${esc(label)}</option>`).join('')}</select>`:field.type==='textarea'?`<textarea class="form-control" name="${field.key}" maxlength="2000" ${field.optional?'':'required'}></textarea>`:`<input class="form-control" name="${field.key}" type="${field.type}" value="${esc(value)}" ${field.type==='number'?`min="0" step="${['price','unit_price','fee','consultation_fee','room_charge','amount'].includes(field.key)?'0.01':'1'}"`:''} ${field.type==='password'?'autocomplete="new-password" minlength="12" maxlength="128"':''} ${field.optional?'':'required'}>`;
      return `<label class="form-field">${esc(field.label)}${control}</label>`;
    }).join('');
    document.querySelector('#roleForm button[type=submit]').disabled=false;
    if(spec.journaled){
      try{const pending=JSON.parse(localStorage.getItem(`hms.correction.${identity.user_id}.${currentForm}`)||'null');if(pending){for(const [key,value]of Object.entries(pending)){const el=document.getElementById('roleForm').elements.namedItem(key);if(el){el.value=value;el.disabled=true;}}document.getElementById('roleMessage').textContent='Unresolved journaled operation: retry the original locked details. A confirmed rejection allows editing; uncertain network outcomes retain this key across reload.';}}
      catch(e){document.getElementById('roleMessage').textContent='Browser storage is unavailable. No new journaled write will be submitted.';document.querySelector('#roleForm button[type=submit]').disabled=true;}
    }
    if(currentForm==='dispense'){
      try{
        const pending=localStorage.getItem(`hms.dispense.${identity.user_id}`);
        if(pending){const data=JSON.parse(pending);for(const [key,value]of Object.entries(data)){const el=document.getElementById('roleForm').elements.namedItem(key);if(el){el.value=value;el.disabled=true;}}document.getElementById('roleMessage').textContent='Unresolved dispensing request: retry original details; fields are locked across reload.';}
      }catch(e){document.getElementById('roleMessage').textContent='Browser storage is unavailable or the pending request is unreadable. No new dispensing will be submitted. Ask a manager to reconcile any uncertain request.';document.querySelector('#roleForm button[type=submit]').disabled=true;}
    }
  }
  function tables(){return Object.entries(workspace.queues).map(([name,rows])=>{
    const columns=Object.keys(rows[0]||{});
    return `<section class="panel workspace-table" data-queue="${esc(name)}"><h3>${esc(name.replaceAll('_',' '))} <small>${workspace.counts[name]??rows.length} persisted records</small></h3>${rows.length?`<div class="table-wrap"><table class="data-table"><thead><tr>${columns.map(k=>`<th>${esc(k.replaceAll('_',' '))}</th>`).join('')}<th>Actions</th></tr></thead><tbody>${rows.map(r=>`<tr>${columns.map(k=>`<td>${esc(['billed','paid','balance','fee','unit_price','price','consultation_fee','amount'].includes(k)?legacy.money(r[k]):r[k]??'—')}</td>`).join('')}<td>${name==='bills'?`<button class="button button-secondary button-small" data-role-invoice="${r.bill_id}">Invoice / receipts</button>${identity.role!=='patient'?` <button class="button button-primary button-small" data-role-ledger="${r.bill_id}">Items / payment</button>`:''}`:name==='patients'&&['doctor','nurse','patient','manager'].includes(identity.role)?`<button class="button button-secondary button-small" data-role-history="${r.patient_id}">History</button>`:name==='appointments'&&['receptionist','manager'].includes(identity.role)?['Checked In','Waiting','Cancelled','No-show'].map(status=>`<button class="button button-secondary button-small" data-role-status="${esc(status)}" data-id="${r.appointment_id}">${esc(status)}</button>`).join(' '):''}</td></tr>`).join('')}</tbody></table></div>`:'<p class="field-hint">No matching persisted records.</p>'}</section>`;
  }).join('');}
  async function refresh(){
    if(!identity)return;
    window.hmsAdminMode=false;legacy.clear();const stamp=++epoch;const actor=identity.user_id;
    const data=await call(`/api/workspace?page=${page}&q=${encodeURIComponent(search)}`);
    if(!identity||stamp!==epoch||identity.user_id!==actor)return;
    if(identity.role==='manager')data.queues.users=await call('/api/admin/users');
    if(!identity||stamp!==epoch||identity.user_id!==actor)return;
    if(!['receptionist','maintenance'].includes(identity.role)){
      const events=await call(`/api/corrections/history?page=${page}`);
      if(!identity||stamp!==epoch||identity.user_id!==actor)return;
      for(const [name,rows]of Object.entries(events))if(Array.isArray(rows)){data.queues[name]=rows;data.counts[name]=events.counts[name];}
    }
    workspace=data;
    document.getElementById('connectionLabel').textContent='Personal session active';
    document.getElementById('pageTitle').textContent=labels[identity.role]+' workspace';document.title=labels[identity.role]+' · CarePoint';
    nav.innerHTML=`<button class="nav-link active" data-role-refresh>My workspace</button>${identity.role==='manager'?'<button class="nav-link" data-role-admin>Administrative registers</button>':''}<button class="nav-link" data-role-logout>Sign out</button>`;
    const choices=Object.entries(forms).filter(([,s])=>s.roles.includes(identity.role));if(!forms[currentForm]||!forms[currentForm].roles.includes(identity.role))currentForm=choices[0][0];
    const alerts=Object.entries(workspace.notifications||{}).filter(([,n])=>n>0).map(([k,n])=>`${k.replaceAll('_',' ')}: ${n} pending / actionable`).join(' · ');
    main.innerHTML=`<div class="workspace-heading"><div><span class="eyebrow">${esc(identity.username)} · ${esc(labels[identity.role])}</span><h2>Your work, connected</h2><p>Only permitted records are returned by the server. Counts reflect persisted data; queues and correction histories show 40 rows per page. Search applies to primary queues. Event timestamps are UTC; originals are retained.</p></div><button class="button button-secondary" data-role-refresh>Refresh</button></div><p class="work-alert" role="status">${esc(alerts||'No pending queue alerts in the current scope.')} Counts are queues, not clinical priority.</p><section class="panel role-controls"><form id="roleFilter"><label>Search patient / medicine / task<input class="form-control" name="q" value="${esc(search)}"></label><button class="button button-secondary">Search</button><button class="button button-secondary" type="button" data-role-page="${Math.max(1,page-1)}">Previous</button><span>Page ${page}</span><button class="button button-secondary" type="button" data-role-page="${page+1}">Next</button></form></section><section class="panel role-controls"><label for="roleAction">Permitted action</label><select class="form-control" id="roleAction">${choices.map(([k,s])=>`<option value="${k}" ${k===currentForm?'selected':''}>${esc(s.label)}</option>`).join('')}</select><form id="roleForm"><div class="form-grid" id="roleFields"></div><p id="roleMessage" class="form-error" role="alert"></p><button class="button button-primary" type="submit">Save action</button></form></section>${tables()}`;
    renderForm();legacy.layout?.();
  }
  window.hmsRefreshWorkspace=refresh;
  document.addEventListener('change',event=>{if(event.target.id==='roleAction'){currentForm=event.target.value;document.getElementById('roleMessage').textContent='';renderForm();}});
  document.addEventListener('submit',async event=>{
    const form=event.target;if(!['identityLogin','roleForm','roleFilter'].includes(form.id))return;event.preventDefault();
    const button=form.querySelector('button[type="submit"],button:not([type])');if(button)button.disabled=true;
    const submittedAction=currentForm, submittedUser=identity?.user_id;
    try{
      if(form.id==='identityLogin'){
        await call('/api/auth/login',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(form)))});await signedIn();
      } else if(form.id==='roleFilter'){search=form.elements.q.value;page=1;await refresh();}
      else {
        const spec=forms[submittedAction];let body=Object.fromEntries([...new FormData(form)].filter(([,v])=>v!==''));
        let url=typeof spec.url==='function'?spec.url(body):spec.url||`/api/work/${submittedAction}`;
        if(submittedAction==='reschedule')delete body.appointment_id;
        if(['account','role','transfer','discharge'].includes(submittedAction)){delete body.user_id;if(['transfer','discharge'].includes(submittedAction))delete body.admission_id;}
        if(submittedAction==='dispense'){
          const key=`hms.dispense.${submittedUser}`;body=JSON.parse(localStorage.getItem(key)||'null')||{...body,idempotency_key:crypto.randomUUID()};localStorage.setItem(key,JSON.stringify(body));
        }
        if(spec.journaled){
          const key=`hms.correction.${submittedUser}.${submittedAction}`;
          if(submittedAction==='profile'){body.phone??='';body.address??='';}
          body=JSON.parse(localStorage.getItem(key)||'null')||{...body,idempotency_key:crypto.randomUUID()};localStorage.setItem(key,JSON.stringify(body));
        }
        try{await call(url,{method:spec.method||'POST',body:JSON.stringify(body)});}
        catch(error){if(spec.journaled&&error.status>=400&&error.status<500&&error.code!=='idempotency_mismatch')localStorage.removeItem(`hms.correction.${submittedUser}.${submittedAction}`);throw error;}
        if(spec.journaled)localStorage.removeItem(`hms.correction.${submittedUser}.${submittedAction}`);
        if(submittedAction==='dispense')localStorage.removeItem(`hms.dispense.${submittedUser}`);
        if(!identity||identity.user_id!==submittedUser)return;
        if(submittedAction==='password'){expired();return;}
        await refresh();document.getElementById('roleMessage').textContent='Saved. Connected queues have been refreshed.';
      }
    }catch(e){
      if(forms[submittedAction]?.journaled&&identity)renderForm();
      if(submittedAction==='dispense'&&identity){
        if(['expired_batch','insufficient_quantity','quantity_missing','order_cancelled'].includes(e.code))localStorage.removeItem(`hms.dispense.${submittedUser}`);
        renderForm();
      }
      const target=document.getElementById(form.id==='identityLogin'?'identityError':'roleMessage');if(target)target.textContent=e.message;
    }
    finally{if(button?.isConnected)button.disabled=false;}
  });
  document.addEventListener('click',async event=>{
    const t=event.target.closest('[data-role-refresh],[data-role-logout],[data-role-admin],[data-role-page],[data-role-invoice],[data-role-ledger],[data-role-history],[data-role-status]');if(!t)return;
    try{
      if(t.hasAttribute('data-role-logout')){await call('/api/auth/logout',{method:'POST',body:'{}'});expired();}
      else if(t.hasAttribute('data-role-admin')){epoch++;window.hmsAdminMode=true;legacy.bootAdmin();}
      else if(t.dataset.roleInvoice)legacy.invoice(t.dataset.roleInvoice);
      else if(t.dataset.roleLedger)legacy.ledger(t.dataset.roleLedger);
      else if(t.dataset.roleHistory)legacy.history(t.dataset.roleHistory);
      else if(t.dataset.roleStatus){await call(`/api/appointments/${t.dataset.id}`,{method:'PUT',body:JSON.stringify({status:t.dataset.roleStatus})});await refresh();}
      else{if(t.dataset.rolePage)page=Number(t.dataset.rolePage);await refresh();}
    }catch(e){const target=document.getElementById('roleMessage');if(target)target.textContent=e.message;}
  });
  async function signedIn(){identity=await call('/api/auth/me');window.hmsUser=identity;window.hmsCsrf=identity.csrf_token;page=1;search='';await legacy.config?.();await refresh();}
  try{await signedIn();}catch(e){loginScreen(e.message==='Log in to continue.'?'':e.message);}
};
