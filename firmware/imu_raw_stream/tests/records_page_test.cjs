// npm install playwright, then: node tests/records_page_test.cjs
// Optional: PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chrome
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { chromium } = require('playwright');

(async () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/records_page.h'), 'utf8');
  const html = source.split('R"HTML(')[1].split(')HTML"')[0];
  const output = process.env.DELTA_UI_TEST_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'delta-ui-'));
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}) });
  try {
    const page = await browser.newPage({viewport:{width:390,height:844}});
    let recording = true, offline = false, ready = true, deleted = false, corrupt = false, truncated = false;
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const csv = 'elapsed_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,activity_score,battery_v,state\n' +
      Array.from({length:72000}, (_,i) => `${(i+1)*50},0,0,1,0,0,0,25,1,${i>=36000?.3:0},4,${i>=36000?'Active':'Resting'}\n`).join('');
    await page.route('http://delta.test/**', async route => {
      const url = new URL(route.request().url());
      if(offline) return route.abort();
      const reply = (body,status=200) => route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
      if(url.pathname==='/records') return route.fulfill({contentType:'text/html',body:html});
      if(url.pathname==='/api/recording/start') {
        assert.match(route.request().postData(), /unix_ms=\d+/); recording=true;
      }
      if(url.pathname==='/api/recording/stop') recording=false;
      if(url.pathname.startsWith('/api/recording')) return reply({ready,recording,id:'abcdef12',saved_samples:72000,buffered_samples:0,elapsed_ms:3600000,read_errors:0,free_bytes:2400000,estimated_seconds:4000,error:ready?'':'storage_unavailable_no_autoformat'});
      if(url.pathname==='/api/sessions') return recording ? reply({error:'stop_recording_first'},409) : reply({sessions:deleted?[]:[{id:'abcdef12',state:'complete',records:72000,bytes:1728032,trailing_bytes:0,header_valid:true,start_unix_ms:1788969600000},{id:'cafe1234',state:'interrupted',records:100,bytes:2449,trailing_bytes:17,header_valid:true,start_unix_ms:0}]});
      if(url.pathname==='/api/session') {
        if(recording) return reply({error:'stop_recording_first'},409);
        if(route.request().method()==='DELETE') { assert.equal(url.searchParams.get('confirm'),url.searchParams.get('id')); deleted=true;return reply({deleted:true}); }
        if(corrupt) return reply({error:'corrupt_record_download_binary_for_recovery'},422);
        return route.fulfill({contentType:'text/csv',headers:{'X-Delta-Records':'72000'},body:truncated ? csv.slice(0,-50) : csv});
      }
      return route.fulfill({status:404,body:'not found'});
    });
    await page.goto('http://delta.test/records');
    await page.waitForFunction(()=>document.querySelector('#state').textContent.includes('正在设备上记录'));
    assert(await page.locator('#start').isDisabled());
    assert(await page.locator('#refresh').isDisabled());
    await page.locator('#stop').click();
    await page.locator('.session').first().waitFor();
    assert.equal(await page.locator('.session').count(),2);
    assert.match(await page.locator('.session').nth(1).innerText(),/未正常结束/);
    assert.match(await page.locator('.session').nth(1).innerText(),/末尾不完整/);
    await page.getByRole('button',{name:'查看整段曲线'}).first().click();
    await page.locator('#report').waitFor({state:'visible'});
    assert.match(await page.locator('#report-summary').innerText(),/60.0 分钟/);
    assert.match(await page.locator('#report-summary').innerText(),/72,000 条有效样本/);
    assert.match(await page.locator('#report-summary').innerText(),/估计活动 30.0 分钟/);
    await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,'records-mobile.png'),fullPage:true});
    await page.setViewportSize({width:1100,height:900});
    await page.screenshot({path:path.join(output,'records-desktop.png'),fullPage:true});
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button',{name:'下载 CSV',exact:true}).first().click();
    const download = await downloadPromise;
    await download.saveAs(path.join(output,'hour.csv'));
    assert.equal(fs.readFileSync(path.join(output,'hour.csv'),'utf8').split('\n').length,72002);
    await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
    corrupt=true;
    await page.getByRole('button',{name:'查看整段曲线'}).first().click();
    await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('数据损坏'));
    corrupt=false;
    await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
    truncated=true;
    await page.getByRole('button',{name:'查看整段曲线'}).first().click();
    await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('传输不完整'));
    truncated=false;
    await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('button',{name:'删除',exact:true}).first().click();
    assert.equal(deleted,false);
    await page.locator('#start').click();
    await page.waitForFunction(()=>document.querySelector('#state').textContent.includes('正在设备上记录'));
    assert(await page.locator('#refresh').isDisabled());
    offline=true;
    await page.waitForFunction(()=>document.querySelector('#state').textContent.includes('未连接'),{},{timeout:7000});
    assert(await page.locator('#start').isDisabled());
    assert(await page.locator('#stop').isDisabled());
    offline=false;
    await page.waitForFunction(()=>document.querySelector('#state').textContent.includes('正在设备上记录'),{},{timeout:7000});
    await page.locator('#stop').click();
    await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
    ready=false;
    await page.waitForFunction(()=>document.querySelector('#state').textContent==='存储不可用',{},{timeout:7000});
    assert(await page.locator('#start').isDisabled());
    assert.deepEqual(errors,[]);
    console.log('PASS: recording controls, 72,000-row chart/download, interrupted session, corrupt/truncated CSV, delete cancellation, disconnect/reconnect, storage failure, mobile layout');
    console.log('Screenshots and downloaded fixture:',output);
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
