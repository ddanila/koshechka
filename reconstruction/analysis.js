'use strict';
// Diagnostics consume Python-exported samples; no second controller lives here.
window.KittyAnalysis = (() => {
  const data = window.KITTY;
  const panel = document.getElementById('analysis');
  const canvas = document.getElementById('motion');
  const ctx = canvas.getContext('2d');
  const colors = ['#edb96c', '#8fd8b3', '#9ebdf5', '#ef9ebd'];
  const labels = ['Right rear', 'Right front', 'Left rear', 'Left front'];
  const names = ['', 'Stance', 'Rear reversal / lift', 'Swing', 'Stop', 'Front reversal', 'Landing'];
  // Fixed bounds for the entire clip, independent of playback and camera.
  let xmin = 0, xmax = 0, ymax = .1;
  for (const frame of data?.frames || []) for (const [x,y] of frame.legs) {
    xmin = Math.min(xmin,x); xmax = Math.max(xmax,x); ymax = Math.max(ymax,y);
  }
  function line(points, color, width=1) {
    ctx.strokeStyle=color; ctx.lineWidth=width; ctx.beginPath();
    points.forEach(([x,y],i)=>i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.stroke();
  }
  function dot(x,y,color,r=5) {
    ctx.fillStyle=color; ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI); ctx.fill();
  }
  function draw(index) {
    if (!panel.open || !data) return;
    const frame=data.frames[index], fit=frame.analysis;
    canvas.hidden=!fit;
    document.getElementById('analysis-note').textContent = !fit
      ? 'This older export has no phase diagnostics. Regenerate it with run.py; playback still works.'
      : `t = ${frame.t.toFixed(2)} s · Phase coupling ${data.coupling ? 'enabled' : 'disabled (cross shown for comparison)'}`;
    document.getElementById('branches').textContent=labels.map((label,i)=>
      `${label.padEnd(12)} ${index===0 ? 'Initial conditions' : names[frame.branches[i]]}`+
      (fit ? ` · Δφ ${fit.errors[i].toFixed(3)} rad` : '')).join('\n');
    if (!fit) return;
    const narrow = window.innerWidth < 650;
    canvas.width = narrow ? 600 : 1000;
    canvas.height = narrow ? 800 : 420;
    ctx.clearRect(0,0,canvas.width,canvas.height); ctx.font='18px system-ui';
    for (let i=0;i<4;i++) {
      const left=40+(i%2)*295, top=50+Math.floor(i/2)*195;
      const project=([x,y])=>[left+15+(x-xmin)/(xmax-xmin||1)*235,top+125-y/ymax*105];
      ctx.fillStyle=colors[i]; ctx.fillText(labels[i],left,top-15);
      line([[left,top+125],[left+270,top+125]],'#68766c');
      line(data.frames.map(f=>project(f.legs[i])),colors[i]+'66',2);
      dot(...project(frame.legs[i]),colors[i]);
    }
    const cx=narrow?300:815,cy=narrow?595:205,r=120, point=a=>[cx+r*Math.cos(a),cy-r*Math.sin(a)];
    ctx.strokeStyle='#68766c';ctx.beginPath();ctx.arc(cx,cy,r,0,2*Math.PI);ctx.stroke();
    ctx.fillStyle='#e9e7dd';ctx.fillText('Fitted phase cross',cx-105,cy-170);
    for(let i=0;i<4;i++) {
      const target=point(fit.targets[i]), actual=point(fit.phases[i]);
      line([[cx,cy],target],colors[i]+'88',2);
      ctx.setLineDash([4,4]);line([target,actual],colors[i]);ctx.setLineDash([]);
      dot(...actual,colors[i],7);
    }
    ctx.fillStyle='#bcbfb7';ctx.fillText('Points: current phases',cx-115,cy+165);
    ctx.fillText('Spokes: fitted targets',cx-115,cy+190);
  }
  return {draw};
})();
