// Mocked DOM/API evidence only. No Oracle and not a real browser.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
const ledger = {bill_id:1, legacy_charge_total:'100.00', legacy_status:'Paid', billed:'125.00',paid:'0.00',balance:'125.00',status:'Unpaid',items:[{item_id:3,description:'Synthetic item',quantity:1,unit_price:'25.00',line_total:'25.00'}],payments:[]};
function setup(saved) {
 const dom=new JSDOM(fs.readFileSync('static/index.html','utf8'),{url:'https://demo.test/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; w.matchMedia=()=>({matches:false,addEventListener(){}}); w.scrollTo=()=>{};
 w.crypto.randomUUID=()=>require('node:crypto').randomUUID();
 if(saved) for(const [k,v] of Object.entries(saved))w.localStorage.setItem(k,v);
 const calls=[]; let rejectPayment=false;
 w.fetch=async (url,options={})=>{
  calls.push([String(url),options]);
  if(String(url).endsWith('/payments') && rejectPayment) throw new Error('Response lost');
  let data=String(url).includes('/ledger')?ledger:String(url).includes('/details/')?{record:{bill_id:1,patient_name:'Synthetic Patient',bill_date:'2026-10-29',total_amount:'125.00',paid:'40.00',balance:'85.00',payment_status:'Partial',legacy_status:'Paid'},related:{items:ledger.items,payments:[{payment_id:7,amount:'40.00',payment_method:'Cash',reference:'Demo receipt',recorded_at:'2026-10-29T00:00:00'}]}}:[];
  return {ok:true,status:200,json:async()=>({data})};
 };
 const source=fs.readFileSync('static/app.js','utf8').split('\nrefreshConnectionDate();')[0];
 w.eval(source+'\nwindow.hmsTest={openLedger,submitLedgerForm,closeModal,openRecordDetails,openForm,formatMoney,todayLocal,submitRecordForm,state,MODULES,REPORTS,renderReportTable,navigate,checkConnection,renderDashboard};');
 return {w,a:w.hmsTest,calls,failPayment(){rejectPayment=true},save(){return Object.fromEntries(Object.keys(w.localStorage).map(k=>[k,w.localStorage.getItem(k)]))}};
}
const settle=()=>new Promise(r=>setTimeout(r,10));
test('exact money never loses a cent at large values',()=>{const {a}=setup();assert.match(a.formatMoney('9999999899000000.01'),/\.01$/)});
test('unpaid decimal-string invoices expose charge controls',async()=>{const {w,a}=setup();await a.openLedger(1);assert.ok(w.document.querySelector('#billItemForm'));assert.ok(w.document.querySelector('[data-action="edit-bill-item"]'))});
test('uncertain payment survives close, reopen and full reload with identical payload',async()=>{
 const h=setup(); await h.a.openLedger(1);let f=h.w.document.querySelector('#billPaymentForm'); f.elements.amount.value='40.00';f.elements.reference.value='demo';h.failPayment();await h.a.submitLedgerForm(f);
 const original=JSON.parse(h.calls.find(([u,o])=>u.endsWith('/payments')&&o.method==='POST')[1].body);
 h.a.closeModal();await h.a.openLedger(1);f=h.w.document.querySelector('#billPaymentForm');assert.equal(f.elements.idempotency_key.value,original.idempotency_key);assert.equal(f.elements.amount.value,'40.00');
 const next=setup(h.save());await next.a.openLedger(1);assert.equal(next.w.document.querySelector('#billPaymentForm').elements.idempotency_key.value,original.idempotency_key);
 assert.match(next.w.document.querySelector('#billPaymentForm').textContent,/retry/i);
});
test('printable invoice contains every line, receipt, balance and historical disclaimer',async()=>{const {w,a}=setup();a.openRecordDetails('bills',1);await settle();let text=w.document.querySelector('.bill-printable').textContent;assert.match(text,/Synthetic item/);assert.match(text,/Demo receipt/);assert.match(text,/85\.00/);assert.match(text,/not a payment/i)});
test('invoice editing sends only supported metadata after payment',async()=>{const {w,a,calls}=setup();const record={bill_id:1,patient_name:'Synthetic',paid:'40.00',notes:'old',bill_date:'2026-10-29',consultation_charge:'100.00',room_charge:'0.00',medicine_charge:'0.00',payment_status:'Partial'};await a.openForm('bills',record);const f=w.document.querySelector('#recordForm');assert.ok(f.elements.notes);assert.equal(f.elements.namedItem('bill_date'),null);assert.equal(f.elements.namedItem('payment_status'),null);assert.equal(f.elements.namedItem('consultation_charge'),null);f.elements.notes.value='new';await a.submitRecordForm(f);const req=calls.find(([u,o])=>u==='/api/bills/1'&&o.method==='PUT');assert.deepEqual(JSON.parse(req[1].body),{notes:'new'})});
test('refunds are manager-only separate retained events, not receipt mutations',async()=>{const {w,a}=setup();await a.openLedger(1);assert.match(w.document.querySelector('#modalRoot').textContent,/Managers authorize credits, refunds.*write-offs/i)});
test('financial report labels describe ledger and receipt-month semantics',()=>{const {a}=setup();assert.doesNotMatch(a.REPORTS['patient-bills'].title,/legacy/i);assert.doesNotMatch(a.REPORTS['billing-by-status'].title,/excludes ledger/i);assert.match(a.REPORTS['monthly-revenue'].description,/receipt/i)});
test('cashier payment refreshes personal workspace, never the forbidden admin dashboard',async()=>{const h=setup();h.w.hmsUser={user_id:7,role:'cashier'};let refreshes=0;h.w.hmsRefreshWorkspace=async()=>refreshes++;await h.a.openLedger(1);const form=h.w.document.querySelector('#billPaymentForm');form.elements.amount.value='40.00';await h.a.submitLedgerForm(form);assert.equal(refreshes,1);assert.equal(h.calls.some(([url])=>url==='/api/dashboard'),false)});
test('unowned pre-personal-login payment keys cannot silently become a fresh payment',async()=>{const h=setup({'hms.pending.payment.v1.1':JSON.stringify({idempotency_key:'unresolved-old-key',amount:'40.00',payment_method:'Cash'})});h.w.hmsUser={user_id:7,role:'cashier'};await h.a.openLedger(1);assert.equal(h.w.document.querySelector('#billPaymentForm'),null);assert.match(h.w.document.body.textContent,/unowned pending payment/i)});

test('database status and snapshots do not infer Oracle from a healthy test fixture',async()=>{
 const {w,a}=setup();await a.checkConnection();assert.equal(w.document.querySelector('#connectionLabel').textContent,'Database connected');
 a.renderDashboard({counts:{},outstanding_total:'0.00',collected_total:'0.00'});assert.match(w.document.querySelector('.dashboard-mark').textContent,/Database snapshot/);assert.doesNotMatch(w.document.body.textContent,/Oracle connected|Oracle snapshot/);
 w.fetch=async()=>{throw new Error('Unavailable')};await a.checkConnection();assert.equal(w.document.querySelector('#connectionLabel').textContent,'Database unavailable');
});
