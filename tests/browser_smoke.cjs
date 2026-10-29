// Real Chromium engine with intercepted synthetic API fixtures. NOT live Oracle E2E.
const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const chromiumModule=require('@sparticuz/chromium'), chromium=chromiumModule.default||chromiumModule;
const puppeteer=require('puppeteer-core');
(async()=>{
 const lib=await chromiumModule.inflate(path.join(path.dirname(require.resolve('@sparticuz/chromium')),'../bin/al2023.tar.br'));
 chromiumModule.setupLambdaEnvironment(path.join(lib,'lib'));
 const browser=await puppeteer.launch({executablePath:await chromium.executablePath(),args:chromium.args,headless:true});
 try {
 const page=await browser.newPage(); const errors=[],calls=[];page.on('pageerror',e=>errors.push(e.message));
 const bill={bill_id:1,patient_id:1,patient_name:'Synthetic Patient',bill_date:'2026-10-29',consultation_charge:'100.00',room_charge:'0.00',medicine_charge:'0.00',total_amount:'125.00',paid:'0.00',balance:'125.00',payment_status:'Unpaid',legacy_status:'Paid',notes:'Synthetic only'};
 const item={item_id:3,description:'Synthetic item',quantity:1,unit_price:'25.00',line_total:'25.00'};
 const payment={payment_id:7,amount:'40.00',payment_method:'Cash',reference:'Synthetic receipt',recorded_at:'2026-10-29T01:00:00',recorded_timezone:'UTC'};
 let failPayment=true;
 await page.setRequestInterception(true);
 page.on('request',async req=>{
  try {
   if (req.url().startsWith('data:') || req.url().startsWith('blob:')) {await req.continue();return;}
   const url=new URL(req.url());
   if(!url.pathname.startsWith('/api/')) {
    const file=url.pathname==='/'?'static/index.html':url.pathname.slice(1);
    if(!file.startsWith('static/'))throw Error('Unexpected asset '+file);
    let body=fs.readFileSync(file,'utf8');
    // This historical fixture isolates administrative registers; personal sessions are tested by Playwright separately.
    if(file==='static/workspace.js')body='/* Legacy register fixture only; personal auth is covered by the real HTTP Playwright suite. */';
    if(file==='static/app.js')body+='\nwindow.__hmsTest={MODULES,REPORTS,navigate,openLedger,closeModal,openRecordDetails,formatMoney,openForm,exportReportCsv};';
    await req.respond({status:200,contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.svg')?'image/svg+xml':'text/html',body});return;
   }
   calls.push([url.pathname+url.search,req.method(),req.postData()]);
   let data=[];
   if(url.pathname==='/api/health')data={status:'ok',database:'oracle'};
   else if(url.pathname==='/api/config')data={today:'2026-10-29',timezone:'Asia/Kolkata'};
   else if(url.pathname==='/api/options')data={patients:[{id:1,label:'Synthetic Patient'}],doctors:[],departments:[],rooms:[],medicines:[]};
   else if(url.pathname==='/api/dashboard')data={counts:{},outstanding_total:'125.00',collected_total:'0.00',upcoming_appointments:[],outstanding_bills:[],low_stock_medicines:[],recent_records:[]};
   else if(url.pathname==='/api/bills/1/ledger')data={bill_id:1,legacy_charge_total:'100.00',legacy_status:'Paid',billed:'125.00',paid:'0.00',balance:'125.00',status:'Unpaid',items:[item],payments:[]};
   else if(url.pathname==='/api/details/bills/1')data={record:{...bill,paid:'40.00',balance:'85.00',payment_status:'Partial'},related:{items:[item],payments:[payment]}};
   else if(url.pathname==='/api/bills/1/payments'&&req.method()==='POST'){
    if(failPayment){await req.abort('failed');return;} data={id:7,replayed:true};
   }
   else if(url.pathname==='/api/bills')data=[bill];
   else if(url.pathname.endsWith('/csv')){await req.respond({status:200,contentType:'text/csv',headers:{'Content-Disposition':'attachment; filename="synthetic.csv"'},body:'bill_id,amount\r\n1,125.00\r\n'});return;}
   await req.respond({status:200,contentType:'application/json',body:JSON.stringify({data,meta:{pagination:{page:1,page_size:20,total:data.length||0,pages:1}}})});
  } catch(e){errors.push(e.message);if(!req.isInterceptResolutionHandled())await req.abort();}
 });
 await page.goto('https://hms.test/',{waitUntil:'networkidle0'});
 assert.match(await page.title(),/Dashboard/);
 const modules=await page.evaluate(()=>Object.keys(window.__hmsTest.MODULES));
 for(const name of modules){await page.evaluate(n=>window.__hmsTest.navigate(n),name);await page.waitForFunction(()=>!document.querySelector('#mainContent .loading-state'));assert.equal(await page.$eval('#pageTitle',e=>e.textContent),(await page.evaluate(n=>window.__hmsTest.MODULES[n].title,name)));}
 await page.evaluate(()=>window.__hmsTest.navigate('reports'));await page.waitForSelector('#reportSelect');
 const reports=await page.evaluate(()=>Object.keys(window.__hmsTest.REPORTS));
 for(const report of reports){await page.select('#reportSelect',report);await page.waitForFunction(()=>!document.querySelector('#reportTable .loading-state'));}
 await page.evaluate(()=>window.__hmsTest.exportReportCsv());await page.waitForFunction(()=>document.querySelector('#toastRegion')?.textContent.includes('Exported'));
 await page.evaluate(()=>window.__hmsTest.openLedger(1));await page.waitForSelector('#billPaymentForm');
 assert.ok(await page.$('#billItemForm'));
 await page.type('#paymentAmount','40.00');await page.type('#paymentReference','Synthetic receipt');
 await page.click('#billPaymentForm button[type="submit"]');await page.waitForFunction(()=>document.querySelector('#formError')?.textContent.length>0);
 const original=JSON.parse(calls.find(([u,m])=>u==='/api/bills/1/payments'&&m==='POST')[2]);
 await page.evaluate(()=>window.__hmsTest.closeModal());await page.reload({waitUntil:'networkidle0'});await page.evaluate(()=>window.__hmsTest.openLedger(1));await page.waitForSelector('#billPaymentForm');
 assert.equal(await page.$eval('[name=idempotency_key]',e=>e.value),original.idempotency_key);
 assert.equal(await page.$eval('#paymentAmount',e=>e.value),'40.00');
 failPayment=false;await page.click('#billPaymentForm button[type="submit"]');await page.waitForFunction(()=>!Object.keys(localStorage).some(k=>k.startsWith('hms.pending.payment')));
 assert.deepEqual(JSON.parse(calls.filter(([u,m])=>u==='/api/bills/1/payments'&&m==='POST').at(-1)[2]),original);
 await page.evaluate(()=>{window.__printed=0;window.print=()=>window.__printed++;window.__hmsTest.openRecordDetails('bills',1)});await page.waitForSelector('.bill-printable');
 const text=await page.$eval('.bill-printable',e=>e.textContent);for(const needle of ['Synthetic item','Synthetic receipt','85.00','not a payment'])assert.ok(text.includes(needle),needle);
 await page.click('[data-action="print-bill"]');assert.equal(await page.evaluate(()=>window.__printed),1);
 await page.emulateMediaType('print');
 const printLayout=await page.$eval('.bill-printable',e=>({top:e.getBoundingClientRect().top,height:e.getBoundingClientRect().height,visibility:getComputedStyle(e).visibility}));console.log('Print layout',printLayout);assert.ok(printLayout.top>=0&&printLayout.top<100, 'Invoice must begin at top of printed page');
 await page.screenshot({path:'/tmp/hms-browser-print.png',fullPage:true});await page.emulateMediaType('screen');
 await page.setViewport({width:390,height:844});await page.screenshot({path:'/tmp/hms-browser-mobile.png',fullPage:true});
 assert.equal(await page.evaluate(()=>window.__hmsTest.formatMoney('9999999899000000.01')).then(x=>x.endsWith('.01')),true);
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({browser:await browser.version(),modules:modules.length,reports:reports.length,mockApiCalls:calls.length,paymentReloadReplay:true,invoicePrintAction:true,mobileViewport:'390x844',pageErrors:errors.length,oracle:false},null,2));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
