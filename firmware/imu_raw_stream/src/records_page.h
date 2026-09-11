#pragma once

const char kRecordsHtml[] PROGMEM = R"HTML(
<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Delta · 离线记录</title>
<style>
:root{font-family:system-ui,sans-serif;color:#203934;background:#edf1ee;color-scheme:light}
*{box-sizing:border-box}body{margin:0}main{max-width:900px;margin:auto;padding:20px}
h1{font-size:25px;margin:18px 0 8px}h2{font-size:18px;margin:0 0 12px}p{line-height:1.65}
a{color:#285f50}.panel{background:white;border:1px solid #d4dcda;border-radius:10px;padding:18px;margin:16px 0}
.actions{display:flex;gap:10px;flex-wrap:wrap}button,.button{font:inherit;font-size:14px;border:1px solid #28604f;border-radius:6px;padding:10px 14px;cursor:pointer;background:#28604f;color:white;text-decoration:none}
button.secondary{color:#285f50;background:white}button:disabled{opacity:.5;cursor:default}
.metrics{display:flex;gap:20px;flex-wrap:wrap}.metrics div{min-width:125px}.label{display:block;font-size:13px;color:#5c706b;margin-bottom:5px}
strong{font-variant-numeric:tabular-nums}#message{min-height:26px;color:#9a4329;overflow-wrap:anywhere}
.session{border-top:1px solid #e0e7e3;padding:16px 0}.session p{margin:0 0 9px;overflow-wrap:anywhere}
.muted{color:#5c706b;font-size:14px}.danger{color:#9a4329!important;border-color:#9a4329!important}
canvas{display:block;width:100%;height:220px;background:#f7faf8}.axis{display:flex;justify-content:space-between;color:#5c706b;font-size:13px;margin-top:8px}
@media(max-width:500px){main{padding:12px}.panel{padding:14px}.metrics{gap:14px}h1{font-size:23px}}
</style></head><body><main>
<a href="/">← 实时仪表盘</a><h1>离线运动记录</h1>
<p class="muted" id="intro">开机自动开始一条新记录。离开 Wi-Fi、关闭网页，设备仍会保存数据。准备关机或下载时，先停止记录。</p>
<section class="panel"><h2 id="state">正在连接设备…</h2>
<div class="metrics">
<div><span class="label">本次已写入</span><strong id="saved">—</strong></div>
<div><span class="label">本次经过时间</span><strong id="elapsed">—</strong></div>
<div><span class="label">存储空间估计还可录</span><strong id="remaining">—</strong></div>
</div><p id="detail" class="muted"></p>
<div class="actions"><button id="stop" disabled>停止并保存</button><button id="start" disabled>开始新记录</button></div>
<p id="message" role="status" aria-live="polite"></p>
<p class="muted">约每秒写入一次。突然断电可能丢失最后一批数据；未正常结束的记录会保留并标记。空间不足时停止，不覆盖历史。</p>
</section>
<section class="panel" id="cloud-panel" hidden><h2>回家自动同步</h2>
<p><strong id="cloud-state">—</strong></p><p id="cloud-detail" class="muted"></p>
<p class="muted">完整历史网址：<a id="cloud-site" target="_blank" rel="noopener"></a></p></section>
<section class="panel"><h2>保存在设备上的历史</h2>
<p class="muted">先停止记录，再查看、下载或删除历史，避免文件传输打断采样。下载到手机后即可留存，设备不需要互联网。</p>
<button id="refresh" class="secondary" disabled>刷新历史</button><div id="sessions"></div></section>
<section class="panel" id="report" hidden><h2 id="report-title">本次记录</h2>
<p id="report-summary"></p><canvas id="chart" width="820" height="220" aria-label="整段记录的相对活动强度曲线"></canvas>
<div class="axis"><span>0 分钟</span><span id="chart-end"></span></div>
<p class="muted">曲线按时间分组取平均。活动／低活动来自当前简单阈值；不能等同于具体行为、距离或卡路里。缺失时段不计入活动统计。</p>
</section></main>
<script>
let recording = true, busy = false, knownState = null, online = false, storageReady = false;
const $ = id => document.getElementById(id);
const states = {complete:'正常结束',interrupted:'未正常结束（断电或重启）',storage_full:'存储空间不足，已停止',io_error:'写入异常',sensor_error:'传感器读取异常',recording:'正在记录'};
const errors = {storage_unavailable:'存储不可用',storage_unavailable_no_autoformat:'存储无法挂载，已有数据未被清除',storage_full:'空间不足，请先下载并清理历史',stop_recording_first:'请先停止记录',imu_unavailable:'传感器未就绪',write_failed:'写入失败',finalize_failed:'结束标记失败，记录仍保留',corrupt_record_download_binary_for_recovery:'检测到数据损坏，请下载原始文件恢复',invalid_header_download_binary_for_recovery:'记录头损坏，请下载原始文件检查'};
const minutes = ms => (ms / 60000).toFixed(1) + ' 分钟';
const cloudModes = {starting:'正在启动',away_pending:'未连上家里 Wi-Fi，约 10 秒后自动开始记录',recording:'离家中，设备正在自动记录',held:'已手动停止；回家后恢复自动记录',home_recording:'在家手动记录中，停止后上传',waiting_clock:'已回家，等待网络校时后上传',syncing:'已回家，正在上传到网站',home:'在家 · 记录已同步',error:'同步暂时失败，稍后自动重试'};
let cloudOn = false;
function message(text=''){ $('message').textContent = text; }
function controls(){
  $('stop').disabled = busy || !online || !recording;
  $('start').disabled = busy || !online || !storageReady || recording;
  $('refresh').disabled = busy || !online || recording;
  document.querySelectorAll('.session button').forEach(b => b.disabled = busy || !online || recording);
}
async function request(url, options={}){
  const response = await fetch(url, {cache:'no-store',...options});
  if (!response.ok) {
    let data = {}; try { data = await response.json(); } catch {}
    throw Error(errors[data.error] || data.error || '请求失败：' + response.status);
  }
  return response;
}
async function status(){
  try {
    const s = await (await request('/api/recording')).json();
    online = true; recording = s.recording; storageReady = s.ready;
    $('state').textContent = !s.ready ? '存储不可用' : recording ? '正在设备上记录 · ' + s.id : '记录已停止';
    $('saved').textContent = s.saved_samples.toLocaleString() + ' 条';
    $('elapsed').textContent = recording ? minutes(s.elapsed_ms) : '已停止';
    $('remaining').textContent = Math.floor(s.estimated_seconds / 60) + ' 分钟';
    $('detail').textContent = '剩余 ' + (s.free_bytes / 1048576).toFixed(2) + ' MiB；缓冲 ' + s.buffered_samples + ' 条；读取错误 ' + s.read_errors + ' 次。容量估计不代表电池续航。';
    if(s.error) message(errors[s.error] || s.error);
    await cloud();
    if(knownState !== recording) {
      knownState = recording;
      if(!recording) await history();
      else $('sessions').textContent = '停止记录后显示历史。';
    }
  } catch(error) {
    online = false;
    $('state').textContent = '手机与设备未连接';
    $('detail').textContent = '这里只表示网页断开连接。设备是否仍在记录，需要重新连接后确认。';
  }
  controls();
}
async function cloud(){
  try {
    const c = await (await request('/api/cloud')).json();
    cloudOn = !!c.configured; $('cloud-panel').hidden = !cloudOn;
    if(!cloudOn) return;
    $('intro').textContent = '已开启回家同步：离开家里 Wi-Fi 约 10 秒后自动开始记录；回家连上 15 秒后自动结束并上传到网站。上传经网站校验后，空间不足时才从设备上删除最旧的已上传记录。';
    $('cloud-state').textContent = cloudModes[c.mode] || c.mode;
    $('cloud-detail').textContent = '待上传 ' + c.pending + ' 段 · 设备上已上传 ' + c.synced + ' 段' + (c.rejected ? ' · 网站拒收 ' + c.rejected + ' 段' : '') + (c.pruned_this_boot ? ' · 本次开机清理 ' + c.pruned_this_boot + ' 段' : '') + (c.mode === 'syncing' && c.bytes ? ' · 当前 ' + Math.round(100 * c.offset / c.bytes) + '%' : '') + (c.error ? ' · ' + c.error : '') + (c.last_sync_unix_ms ? ' · 最近上传 ' + new Date(c.last_sync_unix_ms).toLocaleString() : '');
    $('cloud-site').textContent = c.site; $('cloud-site').href = c.site;
  } catch { $('cloud-panel').hidden = true; }
}
async function action(fn){
  if(busy) return;
  busy = true; controls(); message();
  try { await fn(); } catch(error) { message(error.message); }
  finally { busy = false; await status(); }
}
$('start').onclick = () => action(async()=>{
  await request('/api/recording/start',{method:'POST',body:new URLSearchParams({unix_ms:String(Date.now())})});
});
$('stop').onclick = () => action(async()=>{
  await request('/api/recording/stop',{method:'POST'});
  message('记录已停止并保存，可以下载或关机。');
});
$('refresh').onclick = () => action(history);
function button(text, fn, danger=false){
  const b = document.createElement('button'); b.textContent=text;
  b.className='secondary' + (danger?' danger':''); b.onclick=fn; return b;
}
async function history(){
  const data = await (await request('/api/sessions')).json();
  $('sessions').replaceChildren();
  if(!data.sessions.length) $('sessions').textContent='暂无历史记录。';
  for(const s of data.sessions){
    const card=document.createElement('div'); card.className='session';
    const title=document.createElement('p');
    const when=s.start_unix_ms ? new Date(s.start_unix_ms).toLocaleString() : '未设置日历时间';
    title.textContent=s.id+' · '+(states[s.state]||s.state)+' · '+when+(cloudOn ? (s.synced ? ' · 已上传网站' : ' · 待回家上传') : '');
    const detail=document.createElement('p'); detail.className='muted';
    detail.textContent=s.records.toLocaleString()+' 条（按文件长度）；'+(s.bytes/1048576).toFixed(2)+' MiB。'+(!s.header_valid?'记录头异常。':'')+(s.trailing_bytes?'末尾不完整字节将从 CSV 中略去。':'');
    const actions=document.createElement('div'); actions.className='actions';
    actions.append(button('查看整段曲线',()=>action(()=>view(s))),button('下载 CSV',()=>action(()=>download(s,'csv'))),button('下载原始文件',()=>action(()=>download(s,'bin'))),button('删除',()=>{
      if(!confirm('删除设备上的记录 '+s.id+'？请确认已经下载留存，删除后不能撤销。')) return;
      action(async()=>{await request('/api/session?id='+s.id+'&confirm='+s.id,{method:'DELETE'});await history();});
    },true));
    card.append(title,detail,actions);$('sessions').append(card);
  }
  controls();
}
async function download(s, format){
  message('正在传输，请保持连接…');
  const response=await request('/api/session?id='+s.id+'&format='+format);
  const blob=format==='csv' ? new Blob([await checkedCsv(response)],{type:'text/csv'}) : await response.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url;a.download='delta-'+s.id+'.'+format;
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
  message('已交给浏览器下载，请在手机的下载记录或文件中确认保存。');
}
async function checkedCsv(response){
  const text=await response.text(), expected=response.headers.get('X-Delta-Records');
  const count=text.split('\n').length-2;
  if(expected===null || !/^\d+$/.test(expected) || !text.endsWith('\n') || count!==Number(expected))
    throw Error('传输不完整，记录条数不匹配，请保持连接后重新下载');
  return text;
}
async function view(s){
  message('正在读取整段记录…');
  const response=await request('/api/session?id='+s.id+'&format=csv');
  const rows=(await checkedCsv(response)).trim().split('\n').slice(1).filter(Boolean);
  if(!rows.length) throw Error('这条记录还没有样本。');
  let previous=null, active=0, low=0, missing=0, duration=0;
  const samples=[];
  for(const row of rows){
    const c=row.split(','), ms=Number(c[0]), score=Number(c[9]);
    if(!Number.isFinite(ms)||!Number.isFinite(score)) throw Error('CSV 数据不完整');
    if(previous){ const dt=ms-previous.ms; if(dt>100) missing+=dt; else if(dt>0) previous.active?active+=dt:low+=dt; }
    else missing+=ms;
    previous={ms,active:c[11]==='Active'};duration=ms;samples.push([ms,score]);
  }
  const bins=Array.from({length:400},()=>({sum:0,n:0}));
  for(const [ms,score] of samples){const b=bins[Math.min(399,Math.floor(ms/Math.max(1,duration)*399))];b.sum+=score;b.n++;}
  const canvas=$('chart'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
  ctx.clearRect(0,0,w,h);ctx.strokeStyle='#dce5e0';ctx.lineWidth=1;
  for(const level of [.25,.5,.75]){ctx.beginPath();ctx.moveTo(0,h*(1-level));ctx.lineTo(w,h*(1-level));ctx.stroke();}
  ctx.strokeStyle='#c4582b';ctx.lineWidth=2;ctx.beginPath();let pen=false;
  bins.forEach((b,i)=>{if(!b.n){pen=false;return;}const x=i/399*w,y=h-3-(b.sum/b.n)*(h-6);pen?ctx.lineTo(x,y):ctx.moveTo(x,y);pen=true;});ctx.stroke();
  $('report').hidden=false;$('report-title').textContent='记录 '+s.id+' · '+(states[s.state]||s.state);
  $('report-summary').textContent='记录跨度 '+minutes(duration)+'；估计活动 '+minutes(active)+'；低活动 '+minutes(low)+'；未覆盖时段 '+(missing/1000).toFixed(1)+' 秒。共 '+samples.length.toLocaleString()+' 条有效样本。';
  $('chart-end').textContent=minutes(duration);message('已读取整段记录。');
  $('report').scrollIntoView({behavior:'smooth',block:'start'});
}
(async function poll(){if(!busy) await status();setTimeout(poll,2000);})();
</script></body></html>
)HTML";
