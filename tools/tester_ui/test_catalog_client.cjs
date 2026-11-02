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
