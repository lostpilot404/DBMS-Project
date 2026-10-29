// Real browser -> real Flask -> persisted SQLite compatibility fixture. NOT Oracle.
const {test,expect}=require('@playwright/test');
async function login(browser,baseURL,role){const context=await browser.newContext();const page=await context.newPage();const policyErrors=[];page.on('console',message=>{if(message.type()==='error'&&message.text().includes('Content Security Policy'))policyErrors.push(message.text())});await page.goto(baseURL);await page.locator('#identityLogin [name=username]').fill(role);await page.locator('#identityLogin [name=password]').fill('fixture-password-only');await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByRole('heading',{name:'Your work, connected'})).toBeVisible();await expect(page.locator('[data-fixture-mode]')).toContainText('Not Oracle');expect(policyErrors).toEqual([]);return {context,page};}
async function action(page,key,values={}){
 await page.locator('#roleAction').selectOption(key);
 for(const [name,value]of Object.entries(values)){const field=page.locator(`#roleForm [name=${name}]`);if(await field.evaluate(e=>e.tagName)==='SELECT')await field.selectOption(String(value));else await field.fill(String(value));}
 await page.locator('#roleForm button[type=submit]').click();await expect(page.locator('#roleMessage')).toContainText('Saved. Connected queues have been refreshed.');
}
async function queueId(page,name,key){const row=page.locator(`[data-queue=${name}] tbody tr`).first();await expect(row).toBeVisible();return row.locator('td').evaluateAll((cells,k)=>{const table=cells[0].closest('table');const cols=[...table.querySelectorAll('th')].map(e=>e.textContent.trim());return cells[cols.indexOf(k.replaceAll('_',' '))].textContent.trim()},key);}
test('all nine personal logins, role navigation, errors, reload and logout',async({browser,baseURL})=>{
 for(const role of ['manager','doctor','patient','receptionist','nurse','pharmacist','cashier','lab','maintenance']){
  const {context,page}=await login(browser,baseURL,role);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await expect(page.locator('#primaryNav')).toContainText('Sign out');
  if(role==='manager'){await page.locator('[data-role-admin]').click();await expect(page.locator('#connectionLabel')).toHaveText('Database connected');await expect(page.locator('.dashboard-mark')).toContainText('Database snapshot');await expect(page.locator('[data-fixture-mode]')).toContainText('Not Oracle');}
  if(role!=='manager'){const r=await page.request.get('/api/admin/users');expect(r.status()).toBe(403);await expect(page.locator('[data-role-admin]')).toHaveCount(0);}
  if(role==='maintenance'){await expect(page.locator('#mainContent')).not.toContainText('Patient One');expect((await page.request.get('/api/patients')).status()).toBe(403);}
  await page.reload();await expect(page.getByRole('heading',{name:'Your work, connected'})).toBeVisible();expect(errors).toEqual([]);
  await page.locator('[data-role-logout]').click();await expect(page.locator('#identityLogin')).toBeVisible();expect((await page.request.get('/api/auth/me')).status()).toBe(401);await context.close();
 }
 const {page,context}=await login(browser,baseURL,'patient');await page.locator('[data-role-logout]').click();await page.locator('[name=username]').fill('patient');await page.locator('[name=password]').fill('wrong');await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#identityError')).toContainText('Invalid credentials');await context.close();
});
test('outpatient cross-role forms persist across reload through payment and printable receipt',async({browser,baseURL})=>{
 const contexts=[];const open=async(role)=>{const x=await login(browser,baseURL,role);contexts.push(x.context);return x.page};
 const reception=await open('receptionist');
 await action(reception,'register',{patient_name:'Browser Registered Patient',date_of_birth:'1990-01-01',gender:'O'});const pid=await queueId(reception,'patients','patient_id');
 const manager=await open('manager');await action(manager,'user',{username:'browser.patient',password:'fixture-password-only',role:'patient',patient_id:pid});
 const p=await open('browser.patient');
 await action(p,'request_appointment',{doctor_id:1,requested_time:'09:00',reason:'Browser synthetic visit'});
 await reception.reload();const rid=await queueId(reception,'requests','request_id');await action(reception,'review_request',{request_id:rid,decision:'Accepted'});
 const aid=await queueId(reception,'appointments','appointment_id');
 await action(reception,'reschedule',{appointment_id:aid,doctor_id:1,appointment_time:'09:30',duration_minutes:30});
 const appt=reception.locator('[data-queue=appointments] tbody tr').filter({hasText:'Browser Registered Patient'}).first();
 await appt.locator('[data-role-status="Checked In"]').click();await expect(reception.locator('[data-queue=appointments]')).toContainText('Checked In');
 await reception.locator(`[data-role-status="Waiting"][data-id="${aid}"]`).click();await expect(reception.locator('[data-queue=appointments]')).toContainText('Waiting');
 const doctor=await open('doctor');await action(doctor,'consultation',{patient_id:pid,appointment_id:aid,diagnosis:'Synthetic diagnosis',clinical_notes:'Browser care note'});
 const eid=await queueId(doctor,'consultations','encounter_id');await action(doctor,'prescribe',{encounter_id:eid,medicine_id:1,ordered_quantity:2,dosage:'One unit',duration:'Two days'});await action(doctor,'order_test',{encounter_id:eid,test_id:1});
 const lab=await open('lab');const oid=await queueId(lab,'tests','order_id');await action(lab,'result',{order_id:oid,result_text:'Browser synthetic normal'});
 const pharmacy=await open('pharmacist');const future=new Date(Date.now()+86400000*60).toISOString().slice(0,10);
 await action(pharmacy,'receive_batch',{medicine_id:1,batch_number:'Browser-B1',expires_on:future,quantity:10});
 const batch=await queueId(pharmacy,'batches','batch_id'),rx=await queueId(pharmacy,'prescriptions','prescription_id');await action(pharmacy,'dispense',{prescription_id:rx,batch_id:batch,quantity:2});
 await pharmacy.reload();await expect(pharmacy.locator('[data-queue=medicines]')).toContainText('8');
 await action(doctor,'complete_consultation',{encounter_id:eid,diagnosis:'Synthetic final diagnosis',clinical_notes:'Released browser clinical note'});
 const cashier=await open('cashier');await action(cashier,'prepare_bill',{encounter_id:eid,notes:'Browser invoice'});const bill=await queueId(cashier,'bills','bill_id');await cashier.locator(`[data-role-ledger="${bill}"]`).click();await expect(cashier.locator('#ledgerTitle')).toBeVisible();
 await cashier.locator('#paymentAmount').fill('60.00');await cashier.locator('#paymentReference').fill('Browser receipt');await cashier.locator('#billPaymentForm button[type=submit]').click();await expect(cashier.locator('#modalRoot')).toContainText('Outstanding ₹0.00');
 await cashier.locator('#modalRoot [data-action=close-modal]').click();await cashier.locator(`[data-role-invoice="${bill}"]`).click();await expect(cashier.locator('.bill-printable')).toContainText('Browser receipt');
 await cashier.emulateMedia({media:'print'});const rect=await cashier.locator('.bill-printable').boundingBox();expect(rect.y).toBeLessThan(100);await cashier.pdf({path:'/tmp/hms-role-receipt.pdf'});await cashier.screenshot({path:'/tmp/hms-role-receipt.png',fullPage:true});
 await p.reload();await expect(p.locator('[data-queue=bills]')).toContainText('Paid');await expect(p.locator('[data-queue=tests]')).toContainText('Browser synthetic normal');await expect(p.locator('[data-queue=consultations]')).toContainText('Released browser clinical note');
 const other=await open('patient2');expect((await other.request.get(`/api/bills/${bill}/ledger`)).status()).toBe(404);expect((await other.request.get(`/api/patients/${pid}/summary`)).status()).toBe(404);
 for(const context of contexts)await context.close();
});
test('manager creates a personal staff account using real forms',async({browser,baseURL})=>{
 const {page,context}=await login(browser,baseURL,'manager');await action(page,'staff',{full_name:'Browser Reception','staff_kind':'receptionist'});
 const staff=page.locator('[data-queue=staff] tbody tr').filter({hasText:'Browser Reception'});const id=await staff.locator('td').evaluateAll(cells=>{const headers=[...cells[0].closest('table').querySelectorAll('th')].map(e=>e.textContent.trim());return cells[headers.indexOf('staff id')].textContent.trim()});
 await action(page,'user',{username:'browser.reception',password:'browser-test-password-only',role:'receptionist',staff_id:id});await expect(page.locator('[data-queue=users]')).toContainText('browser.reception');await context.close();
});
test('a delayed authenticated workspace response cannot resurrect data after logout',async({browser,baseURL})=>{
 const {page,context}=await login(browser,baseURL,'patient');let release,captured;const gate=new Promise(r=>release=r),ready=new Promise(r=>captured=r);
 await page.route('**/api/workspace?**',async route=>{const response=await route.fetch();captured();await gate;await route.fulfill({response});});
 await page.locator('[data-role-refresh]').first().click();await ready;await page.locator('[data-role-logout]').click();await expect(page.locator('#identityLogin')).toBeVisible();release();await page.unrouteAll({behavior:'wait'});await expect(page.locator('#identityLogin')).toBeVisible();await expect(page.locator('#mainContent')).not.toContainText('Patient One');await context.close();
});
test('inpatient assigned ward care, transfer, discharge and final payment use the same history',async({browser,baseURL})=>{
 const contexts=[];const open=async role=>{const x=await login(browser,baseURL,role);contexts.push(x.context);return x.page};
 const manager=await open('manager');await action(manager,'admission',{patient_id:2,room_id:1});const aid=await queueId(manager,'admissions','admission_id');
 await action(manager,'assign_ward',{admission_id:aid,user_id:5,is_active:'Y'});await action(manager,'assign_doctor',{patient_id:2,doctor_id:1,is_active:'Y'});
 const nurse=await open('nurse');await expect(nurse.locator('[data-queue=patients]')).toContainText('Patient Two');await expect(nurse.locator('[data-queue=patients]')).not.toContainText('Patient One');
 await action(nurse,'observation',{admission_id:aid,observation:'Browser ward observation'});await action(nurse,'transfer',{admission_id:aid,room_id:2});await nurse.reload();await expect(nurse.locator('[data-queue=observations]')).toContainText('Browser ward observation');
 const doctor=await open('doctor');await action(doctor,'consultation',{patient_id:2,admission_id:aid});const eid=await queueId(doctor,'consultations','encounter_id');await action(doctor,'complete_consultation',{encounter_id:eid,diagnosis:'Browser inpatient diagnosis',clinical_notes:'Browser released discharge note'});
 await action(nurse,'discharge',{admission_id:aid});await expect(nurse.locator('[data-queue=patients]')).not.toContainText('Patient Two');expect((await nurse.request.get('/api/patients/2/summary')).status()).toBe(404);
 const cashier=await open('cashier');await action(cashier,'prepare_bill',{admission_id:aid,room_charge:'100.00'});const bill=await queueId(cashier,'bills','bill_id');await cashier.locator(`[data-role-ledger="${bill}"]`).click();await cashier.locator('#paymentAmount').fill('120.00');await cashier.locator('#billPaymentForm button[type=submit]').click();await expect(cashier.locator('#modalRoot')).toContainText('Outstanding ₹0.00');
 const patient=await open('patient2');const stays=(await (await patient.request.get('/api/patients/2/room-history')).json()).data;expect(stays.map(s=>s.room_id)).toEqual([1,2]);
 await patient.locator('[data-role-history="2"]').click();await expect(patient.locator('.patient-chart-printable')).toContainText('Browser released discharge note');await expect(patient.locator('.patient-chart-printable')).toContainText('Browser ward observation');
 const ledger=(await(await patient.request.get(`/api/bills/${bill}/ledger`)).json()).data;expect(ledger.status).toBe('Paid');expect(ledger.payments).toHaveLength(1);
 for(const context of contexts)await context.close();
});
test('maintenance workflow exposes rooms and tasks, never clinical identities',async({browser,baseURL})=>{
 const m=await login(browser,baseURL,'manager');await action(m.page,'maintenance_request',{room_id:1,description:'Browser synthetic maintenance'});const task=await queueId(m.page,'maintenance','task_id');
 const worker=await login(browser,baseURL,'maintenance');await action(worker.page,'maintenance_start',{task_id:task});await expect(worker.page.locator('[data-queue=rooms]')).toContainText('Maintenance');await action(worker.page,'maintenance_complete',{task_id:task});await expect(worker.page.locator('[data-queue=maintenance]')).toContainText('Completed');await expect(worker.page.locator('#mainContent')).not.toContainText('Patient Two');await m.context.close();await worker.context.close();
});

test('real corrective forms connect partial cancellation, clinical amendments, return, cashier refund and stock writeoff',async({browser,baseURL})=>{
 const contexts=[];const open=async role=>{const x=await login(browser,baseURL,role);contexts.push(x.context);return x.page};
 const reception=await open('receptionist');await action(reception,'book',{patient_id:1,doctor_id:1,appointment_time:'13:30',duration_minutes:30});const aid=await queueId(reception,'appointments','appointment_id');
 const patient=await open('patient');await action(patient,'profile',{phone:'9876501234',address:'Browser self-service contact'});await action(patient,'reschedule_appointment',{appointment_id:aid,appointment_time:'15:30',reason:'Patient requested a later slot'});
 await reception.reload();await expect(reception.locator('[data-queue=appointments]')).toContainText('15:30');
 for(const status of ['Checked In','Waiting']){await reception.locator(`[data-role-status="${status}"][data-id="${aid}"]`).click();await expect(reception.locator('[data-queue=appointments]')).toContainText(status);}
 const doctor=await open('doctor');await action(doctor,'consultation',{patient_id:1,appointment_id:aid,diagnosis:'Original browser diagnosis'});const eid=await queueId(doctor,'consultations','encounter_id');
 await action(doctor,'prescribe',{encounter_id:eid,medicine_id:1,ordered_quantity:4,dosage:'One verified unit',duration:'Four days'});const rx=await queueId(doctor,'prescriptions','prescription_id');
 await action(doctor,'order_test',{encounter_id:eid,test_id:1});let oid=await queueId(doctor,'tests','order_id');await action(doctor,'cancel_test',{order_id:oid,reason:'Test no longer indicated'});
 await action(doctor,'order_test',{encounter_id:eid,test_id:1});oid=await queueId(doctor,'tests','order_id');
 const lab=await open('lab');await action(lab,'result',{order_id:oid,result_text:'Original browser lab finding'});const result=await queueId(lab,'tests','result_id');await action(lab,'amend_result',{result_id:result,content:'Verified corrected lab interpretation',reason:'Recalibrated synthetic instrument'});
 const pharmacy=await open('pharmacist');await action(pharmacy,'receive_batch',{medicine_id:1,batch_number:'Correction-browser',expires_on:'2099-01-01',quantity:10});const batch=await queueId(pharmacy,'batches','batch_id');
 await action(pharmacy,'dispense',{prescription_id:rx,batch_id:batch,quantity:2});const dispense=await queueId(pharmacy,'dispensing','dispense_id');
 await action(doctor,'cancel_rx',{prescription_id:rx,reason:'Stop remaining two units'});await action(doctor,'complete_consultation',{encounter_id:eid,diagnosis:'Original completed diagnosis',clinical_notes:'Original retained completed note'});
 await action(doctor,'amend_consultation',{encounter_id:eid,content:'Corrected explanation <img src=x onerror=alert(1)>',reason:'Verified transcription clarification'});
 expect(await doctor.locator('[data-queue=amendments] img').count()).toBe(0);
 const cashier=await open('cashier');await action(cashier,'prepare_bill',{encounter_id:eid});const bill=await queueId(cashier,'bills','bill_id');
 for(const reference of ['First correction receipt','Second correction receipt']){await cashier.locator(`[data-role-ledger="${bill}"]`).click();await cashier.locator('#paymentAmount').fill('30.00');await cashier.locator('#paymentReference').fill(reference);await cashier.locator('#billPaymentForm button[type=submit]').click();await expect(cashier.locator('#modalRoot')).toContainText(reference);await cashier.locator('#modalRoot [data-action=close-modal]').click();}
 const payment=await queueId(cashier,'payments','payment_id');
 await action(pharmacy,'return_stock',{dispense_id:dispense,quantity:1,disposition:'Restock',reason:'Verified sealed patient return'});const returned=await queueId(pharmacy,'stock_events','event_id');
 await cashier.reload();await expect(cashier.locator('[data-queue=return_review]')).toContainText('5.00');await action(cashier,'refund',{bill_id:bill,payment_id:payment,stock_event_id:returned,amount:'5.00',reason:'Original-price verified medicine return'});
 await action(pharmacy,'write_off',{batch_id:batch,quantity:2,reason:'Damaged synthetic packaging'});await expect(pharmacy.locator('[data-queue=reconciliation]')).toContainText('7');
 const manager=await open('manager');await action(manager,'debit',{bill_id:bill,amount:'2.00',reason:'Reasoned additional administrative correction'});await action(manager,'writeoff',{bill_id:bill,amount:'2.00',reason:'Authorized financial debt waiver'});
 await patient.reload();await expect(patient.locator('[data-queue=amendments]')).toContainText('Verified corrected lab interpretation');await patient.locator('[data-role-history="1"]').click();await expect(patient.locator('.patient-chart-printable')).toContainText('Original retained completed note');await expect(patient.locator('.patient-chart-printable')).toContainText('Corrected explanation');await expect(patient.locator('.patient-chart-printable')).toContainText('Medicine return');await patient.locator('#modalRoot [data-action=close-modal]').first().click();
 await patient.locator(`[data-role-invoice="${bill}"]`).click();await expect(patient.locator('.bill-printable')).toContainText('REFUND');await expect(patient.locator('.bill-printable')).toContainText('Second correction receipt');await expect(patient.locator('.bill-printable')).toContainText('55.00');
 const ledger=(await(await patient.request.get(`/api/bills/${bill}/ledger`)).json()).data;expect([ledger.billed,ledger.paid,ledger.balance]).toEqual(['55.00','55.00','0.00']);expect(ledger.payments).toHaveLength(2);expect(ledger.corrections).toHaveLength(4);
 for(const context of contexts)await context.close();
});

test('long persisted invoice, multiple receipts, refund, real exports and responsive print',async({browser,baseURL})=>{
 const {page,context}=await login(browser,baseURL,'manager');const token=await page.evaluate(()=>window.hmsCsrf);const headers={'X-CSRF-Token':token};
 const config=(await(await page.request.get('/api/config')).json()).data;
 const created=await page.request.post('/api/bills',{headers,data:{patient_id:2,bill_date:config.today,consultation_charge:'0.02',room_charge:'0',medicine_charge:'0',notes:'Long synthetic invoice verification'}});expect(created.status()).toBe(201);const bill=(await created.json()).data.id;
 for(let i=1;i<=100;i++){const r=await page.request.post(`/api/bills/${bill}/items`,{headers,data:{description:`Long invoice line ${String(i).padStart(3,'0')} ${'X'.repeat(100)}`,quantity:1,unit_price:'1.01'}});expect(r.status()).toBe(201);}
 let pay;for(const [amount,reference]of [['40.00','Long invoice receipt A'],['61.02','Long invoice receipt B']]){const r=await page.request.post(`/api/bills/${bill}/payments`,{headers,data:{amount,payment_method:'Cash',reference,idempotency_key:require('node:crypto').randomUUID()}});expect(r.status()).toBe(201);pay=(await r.json()).data.id;}
 await action(page,'refund',{bill_id:bill,payment_id:pay,amount:'1.02',reason:'Approved long invoice price correction'});
 await page.locator(`[data-role-invoice="${bill}"]`).click();await expect(page.locator('.bill-printable')).toContainText('Long invoice line 100');await expect(page.locator('.bill-printable')).toContainText('Long invoice receipt A');await expect(page.locator('.bill-printable')).toContainText('Long invoice receipt B');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.emulateMedia({media:'print'});const print=await page.locator('.bill-printable').boundingBox();expect(print.y).toBeLessThan(100);
 const pdf=await page.pdf({path:'/tmp/hms-master-long-invoice.pdf',format:'A4',printBackground:true});expect((Buffer.from(pdf).toString('latin1').match(/\/Type\s*\/Page\b/g)||[]).length).toBeGreaterThan(1);await page.screenshot({path:'/tmp/hms-master-long-invoice.png',fullPage:true});
 for(const name of ['patient-bills','invoice-balances','billing-by-status','monthly-revenue']){const report=await page.request.get('/api/reports/'+name);expect(report.status()).toBe(200);const csv=await page.request.get('/api/reports/'+name+'/csv');expect(csv.status()).toBe(200);expect((await csv.text()).length).toBeGreaterThan(30);}
 const balance=(await(await page.request.get(`/api/bills/${bill}/ledger`)).json()).data;expect([balance.billed,balance.paid,balance.balance]).toEqual(['100.00','100.00','0.00']);expect(balance.charges_locked).toBe(true);expect(balance.status).toBe('Paid');
 await context.close();
});

test('changing action during a delayed real correction response never discards another unresolved journal key',async({browser,baseURL})=>{
 const {page,context}=await login(browser,baseURL,'manager');const token=await page.evaluate(()=>window.hmsCsrf);const headers={'X-CSRF-Token':token};const today=(await(await page.request.get('/api/config')).json()).data.today;
 const r=await page.request.post('/api/bills',{headers,data:{patient_id:1,bill_date:today,consultation_charge:'20',room_charge:'0',medicine_charge:'0'}});const bill=(await r.json()).data.id;
 const debit={bill_id:String(bill),amount:'1.00',reason:'Previously committed debit with uncertain response',idempotency_key:require('node:crypto').randomUUID()};expect((await page.request.post('/api/corrections/debit',{headers,data:debit})).status()).toBe(201);
 await page.evaluate(body=>localStorage.setItem(`hms.correction.${window.hmsUser.user_id}.debit`,JSON.stringify(body)),debit);
 let release,seen,finish;const gate=new Promise(r=>release=r),captured=new Promise(r=>seen=r),delivered=new Promise(r=>finish=r);
 await page.route('**/api/corrections/credit',async route=>{const response=await route.fetch();seen();await gate;await route.fulfill({response});finish();});
 await page.locator('#roleAction').selectOption('credit');await page.locator('#roleForm [name=bill_id]').fill(String(bill));await page.locator('#roleForm [name=amount]').fill('1.00');await page.locator('#roleForm [name=reason]').fill('Separate corrective request in flight');await page.locator('#roleForm button[type=submit]').click();await captured;
 await page.locator('#roleAction').selectOption('debit');await expect(page.locator('#roleForm [name=amount]')).toBeDisabled();release();await delivered;await expect(page.locator('#roleMessage')).toContainText('Saved.');
 expect(await page.evaluate(()=>localStorage.getItem(`hms.correction.${window.hmsUser.user_id}.debit`))).not.toBeNull();
 await page.locator('#roleForm button[type=submit]').click();await expect(page.locator('#roleMessage')).toContainText('Saved.');
 expect((await(await page.request.get(`/api/bills/${bill}/ledger`)).json()).data.billed).toBe('20.00');await context.close();
});

test('patient contact form restores persisted values after save and reload instead of silently clearing the other field',async({browser,baseURL})=>{
 const {page,context}=await login(browser,baseURL,'patient');await action(page,'profile',{phone:'9988776655',address:'Retained contact address'});
 await expect(page.locator('#roleForm [name=phone]')).toHaveValue('9988776655');await expect(page.locator('#roleForm [name=address]')).toHaveValue('Retained contact address');
 await page.reload();await page.locator('#roleAction').selectOption('profile');await expect(page.locator('#roleForm [name=phone]')).toHaveValue('9988776655');
 await page.locator('#roleForm [name=phone]').fill('9911223344');await page.locator('#roleForm button[type=submit]').click();await expect(page.locator('#roleMessage')).toContainText('Saved.');
 const values=(await(await page.request.get('/api/patients/1')).json()).data;expect(values.address).toBe('Retained contact address');expect(values.phone).toBe('9911223344');await context.close();
});

test('uncertain 503 after real correction commit retains original UUID across reload and replays once',async({browser,baseURL})=>{
 const {page,context}=await login(browser,baseURL,'manager');const token=await page.evaluate(()=>window.hmsCsrf),today=(await(await page.request.get('/api/config')).json()).data.today;
 const created=await page.request.post('/api/bills',{headers:{'X-CSRF-Token':token},data:{patient_id:1,bill_date:today,consultation_charge:'20',room_charge:'0',medicine_charge:'0'}});const bill=(await created.json()).data.id;
 let first=true;await page.route('**/api/corrections/credit',async route=>{if(first){first=false;const response=await route.fetch();expect(response.status()).toBe(201);await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{code:'database_unavailable',message:'Simulated uncertain commit acknowledgment'}})});}else await route.continue();});
 await page.locator('#roleAction').selectOption('credit');for(const [name,value]of Object.entries({bill_id:bill,amount:'1.00',reason:'Uncertain acknowledged price correction'}))await page.locator(`#roleForm [name=${name}]`).fill(String(value));await page.locator('#roleForm button[type=submit]').click();await expect(page.locator('#roleMessage')).toContainText('uncertain commit');
 expect(await page.evaluate(()=>localStorage.getItem(`hms.correction.${window.hmsUser.user_id}.credit`))).not.toBeNull();
 await page.reload();await expect(page.locator('#roleAction')).toBeVisible();await page.locator('#roleAction').selectOption('credit');await expect(page.locator('#roleForm [name=amount]')).toBeDisabled();await page.locator('#roleForm button[type=submit]').click();await expect(page.locator('#roleMessage')).toContainText('Saved.');
 const data=(await(await page.request.get(`/api/bills/${bill}/ledger`)).json()).data;expect(data.billed).toBe('19.00');expect(data.corrections).toHaveLength(1);await context.close();
});
