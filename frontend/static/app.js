// App-Script für Pixel-basierte Zonen und Kategorien safe/warning/error
(function(){
  const stream = document.getElementById('mjpegStream');
  const canvas = document.getElementById('annotationCanvas');
  const ctx = canvas.getContext('2d');
  const statusText = document.getElementById('statusText');

  let annotations = []; // { _id, category, x,y,width,height } in Pixel
  let currentCategory = 'safe';
  let isDrawing = false;
  let startX = 0, startY = 0;

  function throttle(fn, wait){ let t=false, lastArgs=null; return function(){ lastArgs=arguments; if(!t){ fn.apply(this, lastArgs); lastArgs=null; t=true; setTimeout(()=>{ t=false; if(lastArgs){ fn.apply(this, lastArgs); lastArgs=null; } }, wait); } } }

  function categoryColor(cat){
    return ({ safe:'#27ae60', warning:'#f39c12', error:'#e74c3c' })[cat] || '#3498db';
  }

  function resizeCanvas(){
    const r = stream.getBoundingClientRect();
    canvas.width = r.width; canvas.height = r.height;
    redraw();
  }
  const resizeCanvasThrottled = throttle(resizeCanvas, 100);

  function redraw(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    for(const ann of annotations){
      ctx.strokeStyle = categoryColor(ann.category); ctx.lineWidth = 2;
      ctx.strokeRect(ann.x, ann.y, ann.width, ann.height);
      ctx.fillStyle = categoryColor(ann.category);
      ctx.fillRect(ann.x, ann.y-20, 80, 18);
      ctx.fillStyle = 'white'; ctx.font = '12px Arial';
      ctx.fillText(ann.category.toUpperCase(), ann.x+4, ann.y-6);
    }
  }

  function setList(){
    const list = document.getElementById('annotationsList');
    if(!annotations.length){ list.innerHTML = '<p style="color:#7f8c8d; text-align:center;">Keine Annotationen vorhanden</p>'; return; }
    list.innerHTML = annotations.map(ann => `
      <div class="annotation-item ${ann.category}">
        <span>${ann.category.toUpperCase()} - ${ann.width|0}x${ann.height|0}px @ (${ann.x|0},${ann.y|0})</span>
        <button class="delete-annotation" data-id="${ann._id}">×</button>
      </div>
    `).join('');
    list.querySelectorAll('.delete-annotation').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const id = btn.getAttribute('data-id');
        annotations = annotations.filter(a=>String(a._id)!==String(id));
        setList(); redraw();
      });
    });
  }

  function beginDraw(ev){
    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    startX = ev.clientX - rect.left; startY = ev.clientY - rect.top;
  }
  function moveDraw(ev){
    if(!isDrawing) return;
    const rect = canvas.getBoundingClientRect();
    const curX = ev.clientX - rect.left, curY = ev.clientY - rect.top;
    redraw();
    ctx.setLineDash([5,5]); ctx.lineWidth = 3; ctx.strokeStyle = categoryColor(currentCategory);
    ctx.strokeRect(startX, startY, curX - startX, curY - startY);
    ctx.setLineDash([]);
  }
  function endDraw(ev){
    if(!isDrawing) return; isDrawing = false;
    const rect = canvas.getBoundingClientRect();
    const endX = ev.clientX - rect.left, endY = ev.clientY - rect.top;
    const w = endX - startX, h = endY - startY;
    if(Math.abs(w) > 10 && Math.abs(h) > 10){
      const x = Math.min(startX, endX);
      const y = Math.min(startY, endY);
      const width = Math.abs(w);
      const height = Math.abs(h);
      annotations.push({ _id: Date.now()+Math.random(), category: currentCategory, x, y, width, height });
      setList(); redraw();
    }
  }

  function bindUI(){
    // Kategorien
    document.querySelectorAll('.category-btn').forEach(btn=>{
      btn.addEventListener('click', (e)=>{
        document.querySelectorAll('.category-btn').forEach(b=>b.classList.remove('active'));
        const el = e.currentTarget; el.classList.add('active');
        currentCategory = el.getAttribute('data-category') || 'safe';
      });
    });
    // Buttons
    document.getElementById('clearAllBtn').addEventListener('click', ()=>{ annotations = []; setList(); redraw(); });
    document.getElementById('toggleVideoBtn').addEventListener('click', ()=>{
      if(stream.dataset.paused === '1'){
        stream.src = '/video_feed'; stream.dataset.paused = '0';
        document.getElementById('toggleVideoBtn').textContent = '⏯️ Stream pausieren';
        statusText.textContent = 'Stream läuft';
      } else {
        stream.src = ''; stream.dataset.paused = '1';
        document.getElementById('toggleVideoBtn').textContent = '▶️ Stream starten';
        statusText.textContent = 'Stream pausiert';
      }
    });
    document.getElementById('sendDataBtn').addEventListener('click', saveRegions);
  }

  async function loadRegions(){
    try{
      const res = await fetch('/regions');
      const data = await res.json();
      const list = Array.isArray(data.regions) ? data.regions : (data.regions||[]);
      // Server liefert Pixel-Koordinaten
      annotations = list.map((r, idx)=>({ _id: idx+1, category: r.category || 'safe', x: r.x|0, y: r.y|0, width: r.width|0, height: r.height|0 }));
      setList(); redraw();
    }catch(err){ /* noop */ }
  }

  async function saveRegions(){
    try{
      const payload = {
        videoResolution: { width: canvas.width|0, height: canvas.height|0 },
        regions: annotations.map(a=>({ x:a.x|0, y:a.y|0, width:a.width|0, height:a.height|0, category:a.category }))
      };
      const res = await fetch('/regions', { method: 'POST', headers: { 'Content-Type':'application/json' }, body: JSON.stringify(payload) });
      const data = await res.json();
      if(!data.ok) throw new Error(data.error || 'Fehler');
      statusText.textContent = `Gespeichert: ${data.count} Bereiche`;
      await loadRegions();
    }catch(err){ statusText.textContent = `Fehler beim Speichern: ${err.message}`; }
  }

  function init(){
    // Canvas-Größe nach Bild-Layout
    stream.addEventListener('load', resizeCanvas);
    window.addEventListener('resize', resizeCanvasThrottled);
    // Zeichnen
    canvas.addEventListener('mousedown', beginDraw);
    canvas.addEventListener('mousemove', moveDraw);
    canvas.addEventListener('mouseup', endDraw);
    // UI und Daten
    bindUI();
    loadRegions();
    if(stream.complete) resizeCanvas();
  }

  init();
})();


