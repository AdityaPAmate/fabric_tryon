const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function fixture(job, {walkingSupported=true,commercialSupported=true} = {}) {
  const elements = new Map(), messages = [], calls = [];
  function el(id) {
    if (!elements.has(id)) {
      const classes = new Set(['hidden']);
      elements.set(id, {value:'',textContent:'',children:[],events:{},addEventListener(name,fn){this.events[name]=fn;},removeAttribute(){},
        replaceChildren(...nodes){this.children=nodes;this.value=nodes[0]?.value || '';},
        classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x),
          toggle(x,on){if(on) classes.add(x);else classes.delete(x);}}});
    }
    return elements.get(id);
  }
  const helpers = {api:{value:'https://example.com/api/replace-fabric/',addEventListener(){}},mode:{value:'video'},
    status:{textContent:''},timer:{start(){},stop(){return 1000;}},feedback:el('feedback'),
    save:async()=>({}),displayOutput(){},setRecord(){},showError:m=>messages.push(m),
    clearError:()=>{messages.length=0;},form:{elements:[]},cancel:el('cancel'),
    isBusy:()=>false,setController(){},refreshMode(){},getRecord:()=>({})};
  const client = {resolveBaseUrl:()=> 'https://example.com',
    createVideoJob:async(endpoint,payload)=>{calls.push(['create',payload.get('video_motion')]);return job;},
    getVideoJob:async()=>job,
    retryVideoJob:async()=>{calls.push('retry');return {job_id:job.job_id,status:'queued'};},
    pollJobUntilFinished:async()=>({...job,status:'completed',error:null,
      video:{url:'https://cdn.example/recovered.mp4',continuity:{status:'review_required'}}})};
  const context = vm.createContext({document:{getElementById:el,createElement:()=>({})},VideoClient:client,FormData,URL,
    fetch:async url=>({ok:true,json:async()=>({garment_type:new URL(url).searchParams.get('garment_type'),
      default_style:'mirror_check',source_hint:'Source framing',
      styles:['mirror_check',...(walkingSupported?['walking']:[]),...(commercialSupported&&new URL(url).searchParams.get('garment_type')==='shirt'?['shirt_commercial']:[])]
        .map(id=>({id,label:id,help:id}))}),blob:async()=>new Blob(['photo'],{type:'image/png'})}),
    localStorage:{getItem:()=>null,setItem(){}},performance,AbortController,setInterval,clearInterval});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/video_ui.js'),'utf8'),context);
  const ui=context.createVideoUI(helpers);
  el('video-garment-type').value='shirt';
  el('garment-source').value='fabric';
  el('garment-type').value='shirt';
  el('video-token').value='test-token';
  el('video-job-id').value=job.job_id;
  return {ui,el,messages,calls,helpers};
}

const id='11111111-1111-4111-8111-111111111111';
function completed(status) {
  return {job_id:id,status:'completed',image:{url:'https://cdn.example/photo.png'},
    video:{url:'https://cdn.example/video.mp4',continuity:{status}}};
}

test('flagged video stays playable with a visible review warning',async()=>{
  const f=fixture(completed('review_required'));
  await f.ui.generate('',new FormData(),null,{});
  assert.equal(f.el('result-video').src,'https://cdn.example/video.mp4');
  assert.equal(f.el('result-video').classList.contains('hidden'),false);
  assert.equal(f.el('video-actions').classList.contains('hidden'),false);
  assert.match(f.messages.join(' '),/visual consistency is not verified/);
  assert.match(f.helpers.status.textContent,/review needed/);
});

test('normal completed video has no review warning',async()=>{
  const f=fixture(completed('passed'));
  await f.ui.generate('',new FormData(),null,{});
  assert.equal(f.messages.length,0);
  assert.equal(f.helpers.status.textContent,'Video ready');
  assert.deepEqual(f.calls,[['create','mirror_check']]);
});

test('walking selection is sent with the same image request fields',async()=>{
  const f=fixture(completed('passed'));
  f.el('video-motion').value='walking';
  const form=new FormData();form.append('fabric_type','cotton');
  await f.ui.generate('https://example.com/api/generate-tryon-video/',form,null,{});
  assert.deepEqual(f.calls,[['create','walking']]);
  assert.equal(form.get('fabric_type'),'cotton');
});

test('walking selection also applies to an already generated image',async()=>{
  const f=fixture(completed('passed'));
  f.el('video-motion').value='walking';
  f.ui.onImage({url:'https://cdn.example/photo.png'});
  await f.el('animate-result').onclick();
  assert.deepEqual(f.calls,[['create','walking']]);
});

test('old backend cannot silently accept a walking request as inspection',async()=>{
  const f=fixture(completed('passed'),{walkingSupported:false});
  f.el('video-motion').value='walking';
  await assert.rejects(()=>f.ui.generate('https://example.com/api/generate-tryon-video/',new FormData(),null,{}),/latest backend deployment/);
  assert.equal(f.calls.length,0);
});

test('commercial is a third independent style and preserves image fields',async()=>{
  const f=fixture(completed('passed'));
  f.el('video-motion').value='shirt_commercial';
  const form=new FormData();form.set('garment_type','shirt');form.set('fabric_type','cotton');
  await f.ui.generate('https://example.com/api/generate-tryon-video/',form,null,{});
  assert.deepEqual(f.calls,[['create','shirt_commercial']]);
  assert.equal(form.get('fabric_type'),'cotton');
});

test('commercial cannot silently fall back to an older backend model',async()=>{
  const f=fixture(completed('passed'),{commercialSupported:false});
  f.el('video-motion').value='shirt_commercial';
  await assert.rejects(()=>f.ui.generate('https://example.com/api/generate-tryon-video/',new FormData(),null,{}),/latest backend deployment/);
  assert.equal(f.calls.length,0);
});

test('legacy blocked job uses retry instead of creating a new generation',async()=>{
  const f=fixture({job_id:id,status:'failed',error:{retryable:true,message:'Recover existing clip'}});
  await f.el('lookup-video').onclick();
  assert.equal(f.el('retry-video').classList.contains('hidden'),false);
  await f.el('retry-video').onclick();
  assert.deepEqual(f.calls,['retry']);
  assert.equal(f.el('result-video').src,'https://cdn.example/recovered.mp4');
  assert.match(f.messages.join(' '),/Review needed/);
});

test('video styles load from backend for the selected garment',async()=>{
  const f=fixture(completed('passed'));
  f.el('garment-type').value='saree';
  f.ui.setMode(true);
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(Array.from(f.el('video-motion').children,o=>o.value),['mirror_check','walking']);
  assert.match(f.el('video-motion-help').textContent,/Source framing/);
});

test('saved image uses its original garment even if the form has changed',async()=>{
  const f=fixture(completed('passed'));
  f.helpers.mode.value='single';
  f.helpers.getRecord=()=>({request:{garment_type:'saree'}});
  f.el('garment-type').value='shirt';
  f.ui.onImage({url:'https://cdn.example/saree.png'});
  await new Promise(resolve=>setImmediate(resolve));
  f.el('video-motion').value='shirt_commercial';
  await f.el('animate-result').onclick();
  assert.equal(f.calls.length,0);
  assert.match(f.messages.join(' '),/unavailable for this garment/);
});

test('unknown ready-made garment needs explicit video context',async()=>{
  const f=fixture(completed('passed'));
  f.el('garment-source').value='garment';
  f.el('video-garment-type').value='';
  await assert.rejects(()=>f.ui.generate(f.helpers.api.value,new FormData(),null,{}),/Choose the garment/);
  assert.equal(f.calls.length,0);
});

test('generic saved ready-made image allows an explicit video garment choice',async()=>{
  const f=fixture(completed('passed'));
  f.helpers.mode.value='single';
  f.helpers.getRecord=()=>({request:{garment_type:'garment_image'}});
  f.el('video-garment-type').value='pant';
  f.ui.onImage({url:'https://cdn.example/ready.png'});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.el('video-garment-field').classList.contains('hidden'),false);
  assert.deepEqual(Array.from(f.el('video-motion').children,o=>o.value),['mirror_check','walking']);
  await f.el('animate-result').onclick();
  assert.deepEqual(f.calls,[['create','mirror_check']]);
});
