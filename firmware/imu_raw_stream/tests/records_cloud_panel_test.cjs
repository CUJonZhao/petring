// Home-sync panel on /records with a mocked device (synthetic data).
// npm install playwright, then: node tests/records_cloud_panel_test.cjs [screenshot.png]
// Optional: PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chrome
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');const {chromium}=require('playwright');
(async()=>{const src=fs.readFileSync(path.join(__dirname,'../src/records_page.h'),'utf8');const html=src.split('R"HTML(')[1].split(')HTML"')[0];
const b=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});const page=await b.newPage({viewport:{width:390,height:844}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
let mode='syncing';
await page.route('http://delta.test/**',async r=>{const u=new URL(r.request().url());const reply=(x,s=200)=>r.fulfill({status:s,contentType:'application/json',body:JSON.stringify(x)});
 if(u.pathname==='/records')return r.fulfill({contentType:'text/html',body:html});
 if(u.pathname==='/api/cloud')return reply({configured:true,mode,error:'',site:'https://example.test',pending:1,synced:2,rejected:0,uploaded_this_boot:2,pruned_this_boot:1,upload_id:'cafe1234',offset:16384,bytes:32768,clock_ready:true,last_sync_unix_ms:1789150000000});
 if(u.pathname==='/api/recording')return reply({ready:true,recording:false,id:'abcdef12',saved_samples:1200,buffered_samples:0,elapsed_ms:0,read_errors:0,free_bytes:2400000,estimated_seconds:4000,last_stop:'complete',error:''});
 if(u.pathname==='/api/sessions')return reply({sessions:[{id:'abcdef12',state:'complete',records:1200,bytes:28832,trailing_bytes:0,header_valid:true,start_unix_ms:1789150000000,synced:true},{id:'cafe1234',state:'complete',records:1300,bytes:31232,trailing_bytes:0,header_valid:true,start_unix_ms:1789150100000,synced:false}]});
 return r.fulfill({status:404,body:'nf'});});
await page.goto('http://delta.test/records');
await page.locator('#cloud-panel').waitFor({state:'visible'});
await page.locator('.session').first().waitFor();
assert.match(await page.locator('#cloud-state').innerText(),/正在上传/);
assert.match(await page.locator('#cloud-detail').innerText(),/待上传 1 段/);
assert.match(await page.locator('#cloud-detail').innerText(),/50%/);
assert.match(await page.locator('#intro').innerText(),/自动记录/);
assert.match(await page.locator('.session').nth(0).innerText(),/已上传网站/);
assert.match(await page.locator('.session').nth(1).innerText(),/待回家上传/);
assert.equal(await page.locator('#cloud-site').getAttribute('href'),'https://example.test');
assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
if(process.argv[2])await page.screenshot({path:process.argv[2],fullPage:true});
assert.deepEqual(errors,[]);await b.close();console.log('PASS cloud panel');})().catch(e=>{console.error(e);process.exit(1)});
