const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
test('timer includes server elapsed time when resuming and freezes when stopped',()=>{
  let now=1000,tick; const element={textContent:'',classList:{remove(){}}};
  const context={};vm.createContext(context);vm.runInContext(fs.readFileSync(require.resolve('../js/request_timer.js'),'utf8'),context);
  const timer=context.createRequestTimer(element,{now:()=>now},{setInterval(fn){tick=fn;return 1;},clearInterval(){}});
  timer.start(5000);now+=1200;tick();assert.match(element.textContent,/6\.2 s/);assert.equal(timer.stop(),6200);
  now+=500;assert.equal(timer.stop(),6200);
  timer.start();now+=500;assert.equal(timer.stop(),500);
});
