const $ = id => document.getElementById(id);
const state = {stations:[], forecast:[], map:null, layer:null, windy:null, markers:new Map(), selected:null};
const color = t => t<10?'#2b6cb0':t<15?'#3182ce':t<20?'#38a169':t<25?'#ecc94b':t<30?'#ed8936':t<35?'#e53e3e':'#9b2c2c';
const esc = value => String(value ?? '—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateLabel = value => value ? new Date(value).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false}) : '尚未取得';
async function get(url){const response=await fetch(url,{signal:AbortSignal.timeout(45000)});if(!response.ok)throw Error('資料暫時無法取得');return response.json();}
function script(url){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=url;s.onload=resolve;s.onerror=()=>reject(Error('地圖資源載入失敗'));document.head.append(s);});}
function css(url){const link=document.createElement('link');link.rel='stylesheet';link.href=url;document.head.append(link);}
function visible(){return state.stations.filter(s=>(!$('county').value||s.county===$('county').value)&&(!$('threshold').value||s.temperature_c>=Number($('threshold').value))&&`${s.station_name}${s.county||''}${s.town||''}`.includes($('search').value.trim()));}
function detail(s){
 state.selected=s.station_id;const box=$('detail');box.hidden=false;
 box.innerHTML=`<button aria-label="關閉詳情" id="closeDetail">×</button><div class="tw-eyebrow">${esc(s.station_id)}</div><h2>${esc(s.station_name)}</h2><p class="tw-muted">${esc(s.county)} · ${esc(s.town)}</p><div class="tw-big-temp" style="color:${color(s.temperature_c)}">${s.temperature_c.toFixed(1)}<small>°C</small></div><dl><dt>相對濕度</dt><dd>${esc(s.humidity_percent)} %</dd><dt>風速</dt><dd>${esc(s.wind_speed_mps)} m/s</dd><dt>風向</dt><dd>${esc(s.wind_direction_deg)} °</dd><dt>氣壓</dt><dd>${esc(s.pressure_hpa)} hPa</dd><dt>降水量</dt><dd>${esc(s.precipitation_mm)} mm</dd></dl><time>觀測 ${esc(dateLabel(s.observed_at))}</time>`;
 $('closeDetail').onclick=()=>{box.hidden=true;state.selected=null;};
 if(state.map){state.map.panTo([s.lat,s.lon]);state.markers.get(s.station_id)?.openPopup();}
}
function render(){
 const rows=visible();$('stationCount').textContent=rows.length;$('average').textContent=rows.length?(rows.reduce((n,s)=>n+s.temperature_c,0)/rows.length).toFixed(1)+'°':'—';
 $('stations').replaceChildren();
 if(!rows.length)$('stations').innerHTML='<p class="tw-empty">沒有符合條件的測站。<br>請調整搜尋或篩選條件。</p>';
 for(const s of rows){const button=document.createElement('button');button.className='tw-station';button.innerHTML=`<i class="tw-dot" style="background:${color(s.temperature_c)}"></i><span>${esc(s.station_name)}<small>${esc(s.county)} · ${esc(s.town)}</small></span><strong>${s.temperature_c.toFixed(1)}°</strong>`;button.onclick=()=>detail(s);$('stations').append(button);}
 if(state.layer){state.layer.clearLayers();state.markers.clear();if($('showStations').checked)for(const s of rows){const marker=L.circleMarker([s.lat,s.lon],{radius:6,color:'#fff',weight:2,fillColor:color(s.temperature_c),fillOpacity:.95});marker.bindPopup(`<b>${esc(s.station_name)}</b><br>${esc(s.county)} ${esc(s.town)}<br>${s.temperature_c}°C · 濕度 ${esc(s.humidity_percent)}%<br>風速 ${esc(s.wind_speed_mps)} m/s<br>${esc(dateLabel(s.observed_at))}`);if($('showLabels').checked)marker.bindTooltip(`${s.temperature_c}°`,{permanent:true,direction:'top',className:'tw-temp-label'});marker.on('click',()=>detail(s));marker.addTo(state.layer);state.markers.set(s.station_id,marker);}}
 if(state.selected&&!rows.some(s=>s.station_id===state.selected)){$('detail').hidden=true;state.selected=null;}
}
async function refresh(force=false){
 $('refresh').disabled=true;$('refresh').textContent='更新中…';
 try{const d=await get('/api/temperature/latest'+(force?'?refresh=true':''));state.stations=d.stations;
 const old=$('county').value;$('county').replaceChildren(new Option('全台灣',''));[...new Set(d.stations.map(s=>s.county).filter(Boolean))].sort().forEach(c=>$('county').add(new Option(c,c)));$('county').value=old;
 $('updated').textContent='觀測 '+dateLabel(d.updated_at);
 $('notice').textContent=d.source==='DEMO'?'示範模式 · 目前顯示固定的教學模擬資料，並非即時氣象。設定 API 金鑰後可切換真實資料。':d.status==='fresh'?'中央氣象署測站實測資料 · 氣象模型背景與實測數據分開呈現。':(d.message||'資料暫時無法更新')+(d.stations.length?' 正在顯示上次成功取得的快取。':' 目前沒有可用的測站資料。');
 render();if(state.selected){const s=state.stations.find(s=>s.station_id===state.selected);if(s)detail(s);}
 }catch(e){$('notice').textContent='連線失敗，請確認後端服務。'+(state.stations.length?' 保留目前顯示的資料。':'');}finally{$('refresh').disabled=false;$('refresh').textContent='↻ 更新';}
}
async function initMap(config){
 try{
 await script('https://unpkg.com/leaflet@1.4.0/dist/leaflet.js');
 if(config.windy_key){
 await script('https://api.windy.com/assets/map-forecast/libBoot.js');
 const api=await new Promise((resolve,reject)=>{let done=false;const timer=setTimeout(()=>{done=true;reject(Error('Windy 初始化逾時'));},18000);window.windyInit({key:config.windy_key,lat:23.7,lon:121,zoom:7,overlay:'wind'},value=>{if(!done){clearTimeout(timer);resolve(value);}});});
 state.windy=api;state.map=api.map;$('mapStatus').textContent='Windy 氣象模型背景 + CWA 測站觀測';document.querySelector('[data-layer="wind"]').classList.add('active');
 }else{
 css('https://unpkg.com/leaflet@1.4.0/dist/leaflet.css');
 state.map=L.map('windy',{zoomControl:false}).setView([23.7,121],7);
 L.control.zoom({position:'topright'}).addTo(state.map);
 const tiles=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',maxZoom:18}).addTo(state.map);
 tiles.on('tileerror',()=>{$('mapStatus').textContent='底圖連線失敗；測站列表與資料仍可使用。';});
 $('mapStatus').textContent='OpenStreetMap 底圖 · 設定 Windy 金鑰可啟用氣象圖層';
 }
 state.layer=L.layerGroup().addTo(state.map);render();
 }catch(e){$('mapStatus').textContent='氣象地圖無法載入；請使用左側測站列表查看資料。';}
 document.querySelectorAll('[data-layer]').forEach(b=>{b.disabled=!state.windy;b.title=state.windy?'切換 Windy 氣象模型背景':'需設定 Windy API 金鑰';b.onclick=()=>{try{const allowed=state.windy.store.getAllowed('overlay');if(Array.isArray(allowed)&&!allowed.includes(b.dataset.layer))throw Error();state.windy.store.set('overlay',b.dataset.layer);document.querySelectorAll('[data-layer]').forEach(x=>x.classList.toggle('active',x===b));}catch(e){$('mapStatus').textContent='目前的 Windy 金鑰不支援此圖層。';}};});
}
function renderForecast(){
 const rows=state.forecast.filter(r=>r.regionName===$('region').value).slice(0,7);state.filteredForecast=rows;
 $('chartTitle').textContent=$('region').value+' · 氣溫趨勢';
 $('forecastTable').innerHTML=rows.map(r=>`<tr><td>${esc(r.dataDate)}</td><td>${r.mint}°C</td><td>${r.maxt}°C</td><td>${(r.maxt-r.mint).toFixed(1)}°C</td></tr>`).join('');
 $('forecastStats').innerHTML=rows.length?`<div>首日最低溫<strong>${rows[0].mint}°C</strong></div><div>首日最高溫<strong>${rows[0].maxt}°C</strong></div><div>預報涵蓋<strong>${rows.length} 天</strong></div>`:'';
 $('download').disabled=!rows.length;
 if(!rows.length){$('chart').innerHTML='<p class="tw-empty">目前沒有可用的預報資料。</p>';return;}
 const min=Math.floor(Math.min(...rows.map(r=>r.mint))/5)*5-2,max=Math.ceil(Math.max(...rows.map(r=>r.maxt))/5)*5+2;
 const x=i=>60+i*(810/Math.max(1,rows.length-1)), y=t=>235-(t-min)/(max-min)*185;
 let svg='<svg viewBox="0 0 920 285" role="img" aria-label="一週最高最低氣溫折線圖，數據詳見下方表格">';
 for(let t=Math.ceil(min/5)*5;t<=max;t+=5){svg+=`<line x1="60" x2="870" y1="${y(t)}" y2="${y(t)}" stroke="#e6edf0"/><text x="10" y="${y(t)+4}" fill="#80939c" font-size="13">${t}°</text>`;}
 for(const [key,c] of [['maxt','#e57b55'],['mint','#2589ce']]){svg+=`<polyline points="${rows.map((r,i)=>x(i)+','+y(r[key])).join(' ')}" fill="none" stroke="${c}" stroke-width="3"/>`;rows.forEach((r,i)=>{svg+=`<circle cx="${x(i)}" cy="${y(r[key])}" r="5" fill="${c}" stroke="white" stroke-width="2"><title>${esc(r.dataDate)} ${key==='maxt'?'最高':'最低'} ${r[key]}°C</title></circle><text x="${x(i)}" y="${y(r[key])+(key==='maxt'?-14:24)}" text-anchor="middle" fill="${c}" font-size="13">${r[key]}°</text>`;});}
 rows.forEach((r,i)=>svg+=`<text x="${x(i)}" y="275" text-anchor="middle" fill="#718790" font-size="13">${esc(r.dataDate.slice(5).replace('-','/'))}</text>`);$('chart').innerHTML=svg+'</svg>';
}
async function loadForecast(){try{const data=await get('/api/forecast');state.forecast=data.rows;const selected=$('region').value;$('region').replaceChildren();[...new Set(data.rows.map(r=>r.regionName))].forEach(r=>$('region').add(new Option(r,r)));if(selected)$('region').value=selected;$('forecastStatus').textContent=(data.source==='DEMO'?'示範預報，非真實天氣。 ':data.status!=='fresh'?'快取或無可用資料。 ':'CWA 預報。 ')+(data.note||'')+' '+(data.message||'')+' 擷取時間：'+dateLabel(data.fetched_at);renderForecast();}catch(e){$('forecastStatus').textContent='預報載入失敗，切換頁籤可重試。';}}
function tab(forecast){$('observationView').hidden=forecast;$('forecastView').hidden=!forecast;$('mapTab').classList.toggle('active',!forecast);$('forecastTab').classList.toggle('active',forecast);if(forecast)loadForecast();else setTimeout(()=>state.map?.invalidateSize(),50);}
$('mapTab').onclick=()=>tab(false);$('forecastTab').onclick=()=>tab(true);
['county','threshold','showStations','showLabels'].forEach(id=>$(id).onchange=render);$('search').oninput=render;$('region').onchange=renderForecast;$('refresh').onclick=()=>refresh(true);$('resetMap').onclick=()=>state.map?.setView([23.7,121],7);
$('download').onclick=()=>{const rows=state.filteredForecast||[];const csv='\ufeffregionName,dataDate,mint,maxt\r\n'+rows.map(r=>[r.regionName,r.dataDate,r.mint,r.maxt].join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=$('region').value+'-forecast.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
(async()=>{try{const config=await get('/api/config');$('mode').textContent=config.mode==='demo'?'教學示範':'CWA 即時資料';refresh();initMap(config);setInterval(()=>{if($('autoRefresh').checked){refresh();if(!$('forecastView').hidden)loadForecast();}},300000);}catch(e){$('notice').textContent='無法連線至服務，請重新啟動網站。';}})();
