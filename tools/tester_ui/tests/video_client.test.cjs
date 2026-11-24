const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const client = require('../js/video_client.js');
const id = '11111111-1111-4111-8111-111111111111';
let origin, server, calls, states;
before(async () => {
  server = http.createServer(async (req, res) => {
    let body = ''; for await (const chunk of req) body += chunk;
    calls.push({method:req.method, path:req.url, auth:req.headers.authorization, body, contentType:req.headers['content-type']});
    res.setHeader('Content-Type', 'application/json');
    if (req.headers.authorization !== 'Bearer test-token') {res.writeHead(401);res.end('{}');return;}
    if (req.method === 'POST') {res.writeHead(202);res.end(JSON.stringify({job_id:id,status:'queued'}));return;}
    const status = states.length > 1 ? states.shift() : states[0];
    res.end(JSON.stringify({job_id:id,status, video:status==='completed'?{url:'https://res.cloudinary.com/test/video.mp4',duration:8}:null,
      error:status==='failed'?{code:'poll_timeout',message:'Still pending',retryable:true}:null,
      timing:{video_generation_seconds:125}}));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
});
after(()=>new Promise(resolve=>server.close(resolve)));
function reset() {calls=[];states=['completed'];}
test('mode endpoints preserve the chosen Render host',()=>{
  for(const [mode,path] of [['video','generate-tryon-video/'],['single','replace-fabric/'],['catalog','generate-catalog/']]) {
    assert.equal(client.resolveEndpoint('https://my-render.onrender.com/api/replace-fabric/',mode),`https://my-render.onrender.com/api/${path}`);
  }
});
test('multipart video request uses backend token and supported fields',async()=>{
  reset(); const form=new FormData(); form.append('garment_type','shirt');form.append('gender','men');form.append('camera_view','front');form.append('fabric_image',new Blob(['test-fabric'],{type:'image/png'}),'fabric.png');
  const result=await client.createVideoJob(origin+'/api/generate-tryon-video/',form,'test-token');
  assert.equal(result.status,'queued');assert.equal(calls[0].path,'/api/generate-tryon-video/');
  assert.equal(calls[0].auth,'Bearer test-token');assert.match(calls[0].contentType,/multipart\/form-data; boundary=/);
  assert.match(calls[0].body,/name="fabric_image"/);assert.match(calls[0].body,/name="camera_view"\r\n\r\nfront/);
});
test('polling reports progress, timing and playable result',async()=>{
  reset();states=['image_generating','video_generating','completed'];const seen=[];
  const result=await client.pollJobUntilFinished(origin,id,'Bearer test-token',{intervalMs:1,onUpdate:j=>seen.push(j.status)});
  assert.deepEqual(seen,['image_generating','video_generating','completed']);assert.equal(result.video.duration,8);assert.equal(result.timing.video_generation_seconds,125);
  assert.ok(calls.every(c=>c.path===`/api/video-jobs/${id}/`&&c.auth==='Bearer test-token'));
});
test('failed jobs retain backend retry permission',async()=>{
  reset();states=['failed'];const result=await client.pollJobUntilFinished(origin,id,'test-token',{intervalMs:1});
  assert.equal(result.error.retryable,true);assert.equal(calls.length,1);
});
test('retry targets existing job instead of creating a new generation',async()=>{
  reset();await client.retryVideoJob(origin,id,'test-token');
  assert.equal(calls[0].path,`/api/video-jobs/${id}/retry/`);assert.equal(calls[0].method,'POST');
});
test('incorrect video token produces a useful authentication error',async()=>{
  reset();await assert.rejects(()=>client.createVideoJob(origin+'/api/generate-tryon-video/',new FormData(),'wrong'),/401/);
});
test('cancelled polling sends no further requests',async()=>{
  reset();const controller=new AbortController();controller.abort();
  await assert.rejects(()=>client.pollJobUntilFinished(origin,id,'test-token',{signal:controller.signal}),e=>e.name==='AbortError');
  assert.equal(calls.length,0);
});
