const {test} = require('node:test');
const assert = require('node:assert/strict');
const {endpoint, readEvents} = require('./js/catalog_client.js');

test('endpoint switches modes without changing the configured host', () => {
  assert.equal(endpoint('http://127.0.0.1:8000/api/replace-fabric/', true), 'http://127.0.0.1:8000/api/generate-catalog/');
  assert.equal(endpoint('https://example.test/api/generate-catalog/', false), 'https://example.test/api/replace-fabric/');
  assert.throws(() => endpoint('https://example.test/wrong-path', true));
});

test('fragmented NDJSON, heartbeat, failed view and unterminated last line', async () => {
  const expected = [{event:'started',catalog_id:'one'}, {event:'heartbeat'},
    {event:'image_ready',image:{view:'front',url:'https://example.test/एक.png'}},
    {event:'image_failed',view:'cuff',error:'output_rejected'}, {event:'complete',status:'partial'}];
  const bytes = new TextEncoder().encode(expected.map(event => JSON.stringify(event)).join('\n'));
  const stream = new ReadableStream({start(controller) {
    for(let i=0;i<bytes.length;i+=7)controller.enqueue(bytes.slice(i,i+7));controller.close();
  }});
  const received=[];
  await readEvents(new Response(stream), event=>received.push(event));
  assert.deepEqual(received, expected);
});

test('malformed stream rejects instead of silently claiming completion', async () => {
  await assert.rejects(readEvents(new Response('invalid'), () => {}), /invalid stream/);
});

test('seven-view saree edition retains dynamic totals and collage metadata', async () => {
  const views = ['front', 'side_portrait', 'back_pallu', 'neckline', 'pallu', 'border', 'pleats'];
  const events = [{event:'started', total:7, views, catalog_edition:'editorial-v1'},
    ...views.map(view => ({event:'image_ready', image:{view, url:`https://example.test/${view}.png`}})),
    {event:'collage_ready', image:{view:'catalog', layout:'saree-editorial-v1', includes_original_swatch:false}},
    {event:'complete', status:'completed', total:7}];
  const received = [];
  await readEvents(new Response(events.map(event => JSON.stringify(event)).join('\n')), event => received.push(event));
  assert.equal(received[0].total, 7);
  assert.deepEqual(received.filter(event => event.event === 'image_ready').map(event => event.image.view), views);
  assert.equal(received.at(-2).image.includes_original_swatch, false);
  assert.equal(received.at(-1).status, 'completed');
});
