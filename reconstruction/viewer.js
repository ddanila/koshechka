'use strict';
(() => {
  const data=window.KITTY;
  const $=id=>document.getElementById(id);
  if(!data){$('readout').textContent='Generate frames with run.py first.';return;}
  const canvas=$('screen'),ctx=canvas.getContext('2d');
  const small=document.createElement('canvas');small.width=160;small.height=100;
  const sc=small.getContext('2d',{willReadFrequently:true});
  const tile=document.createElement('canvas');tile.width=6;tile.height=6;
  const tc=tile.getContext('2d');tc.fillStyle='#f5f1e7';tc.fillRect(0,0,6,6);tc.fillStyle='#343731';
  for(const x of [0,2,4])tc.fillRect(x,0,1,5);tc.fillRect(0,4,5,1);
  const pattern=ctx.createPattern(tile,'repeat');
  const edges=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  let playing=true,time=0,last=performance.now(),lastIndex=-1,dirty=true;
  $('time').max=data.duration;$('time').step=1/data.fps;
  $('angle').value=data.model.view_yaw_degrees;$('angleValue').textContent=$('angle').value+'°';
  function hull(points){
    const ps=[...points].sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
    const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
    const lo=[],hi=[];
    for(const p of ps){while(lo.length>1&&cross(lo.at(-2),lo.at(-1),p)<=0)lo.pop();lo.push(p);}
    for(const p of [...ps].reverse()){while(hi.length>1&&cross(hi.at(-2),hi.at(-1),p)<=0)hi.pop();hi.push(p);}
    return lo.slice(0,-1).concat(hi.slice(0,-1));
  }
  function polygon(context,points){context.beginPath();points.forEach((p,i)=>i?context.lineTo(...p):context.moveTo(...p));context.closePath();context.fill();}
  function draw(index){
    const frame=data.frames[index],mode=$('mode').value;
    const angle=Number($('angle').value)*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle);
    const following=$('follow').checked,span=following?5.2:9.;
    const shift=following?0:data.frames.at(-1).distance/2-frame.distance;
    const project=(p,w,h)=>[w/2+(s*p[0]+c*p[1]+shift)*w/span,h*.82-p[2]*w/span];
    ctx.fillStyle='#f5f1e7';ctx.fillRect(0,0,960,600);
    if(mode==='wire'||mode==='silhouette'){
      frame.solids.forEach(([name,vertices],i)=>{
        const points=vertices.map(p=>project(p,960,600));
        if(mode==='silhouette'){ctx.fillStyle='#242c26';polygon(ctx,hull(points));}
        else {ctx.strokeStyle=`hsl(${(i*47)%360} 40% 32%)`;ctx.lineWidth=1.5;
          for(const [a,b] of edges){ctx.beginPath();ctx.moveTo(...points[a]);ctx.lineTo(...points[b]);ctx.stroke();}}
      });
    }else{
      sc.fillStyle='black';sc.fillRect(0,0,160,100);sc.fillStyle='white';
      for(const [name,vertices] of frame.solids)polygon(sc,hull(vertices.map(p=>project(p,160,100))));
      const pixels=sc.getImageData(0,0,160,100).data;
      ctx.fillStyle=pattern;
      for(let y=0;y<100;y++)for(let x=0;x<160;x++){
        const inside=pixels[4*(y*160+x)]>=128;
        if(inside===(mode==='ink'))ctx.fillRect(x*6,y*6,6,6);
      }
    }
    $('clock').textContent=frame.t.toFixed(2)+' s';$('time').value=frame.t;
    const labels=['R rear ','R front','L rear ','L front'];
    $('readout').textContent='Body speed '+frame.speed.toFixed(3)+'\n'+frame.legs.map((leg,i)=>labels[i]+'  '+(leg[1]<.001?'ground':'swing ')+'  ['+frame.branches[i]+']').join('\n');
  }
  function toggle(){playing=!playing;$('play').textContent=playing?'Pause':'Play';}
  $('play').addEventListener('click',toggle);
  $('time').addEventListener('input',()=>{time=Number($('time').value);playing=false;$('play').textContent='Play';dirty=true;});
  for(const id of ['angle','mode','follow'])$(id).addEventListener('input',()=>{dirty=true;$('angleValue').textContent=$('angle').value+'°';});
  document.addEventListener('keydown',e=>{if(e.code==='Space'&&e.target===document.body){e.preventDefault();toggle();}});
  function tick(now){
    if(playing)time=(time+Math.max(0,Math.min(.1,(now-last)/1000))*Number($('rate').value))%(data.duration+1/data.fps);
    last=now;const index=Math.max(0,Math.min(data.frames.length-1,Math.floor(time*data.fps)));
    if(dirty||index!==lastIndex){draw(index);dirty=false;lastIndex=index;}
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();
