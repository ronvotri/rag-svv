'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {create,MODEL}=require('../llm.js');
const path=require('node:path'),{pathToFileURL}=require('node:url'),os=require('node:os');
const localBase=pathToFileURL(path.join(os.tmpdir(),'midgard-local-ai')+path.sep).href;
test('optional model stays unloaded and rejects remote Node URLs',async()=>{
  assert.equal(MODEL,'Qwen2.5-0.5B-Instruct');
  assert.throws(()=>create({baseUrl:'https://huggingface.co/model/'}),/cục bộ/);
  assert.throws(()=>create({baseUrl:localBase,modelPath:'https://other.example/model/'}),/cục bộ/);
  assert.throws(()=>create({baseUrl:localBase,runtimeModule:'https://other.example/runtime.js'}),/Runtime/);
  assert.throws(()=>create({baseUrl:'file://server/share/model/'}),/cục bộ/);
  const ai=create({baseUrl:localBase});
  assert.equal(ai.status.state,'unloaded');assert.equal(ai.status.offline,true);
  await assert.rejects(()=>ai.chat('Xin chào'),/Chưa nạp/);
  await assert.rejects(()=>ai.chat(''),/nhập câu hỏi/);
  await ai.dispose();assert.equal(ai.status.state,'unloaded');
});
test('browser adapter rejects file pages and off-origin model URLs',()=>{
  global.location={protocol:'file:',href:'file:///game/index.html',origin:'null'};
  try{assert.throws(()=>create(),/localhost/);
    global.location={protocol:'https:',href:'https://game.local/index.html',origin:'https://game.local'};
    assert.throws(()=>create({baseUrl:'https://other.example/local-ai/'}),/cùng ứng dụng/);
    assert.throws(()=>create({modelPath:'https://other.example/models/'}),/cùng ứng dụng/);
    assert.throws(()=>create({runtimeModule:'https://other.example/runtime.js'}),/Runtime/);
    assert.throws(()=>create({modelPath:'data:text/plain,hello'}),/cùng ứng dụng/);
    assert.equal(create().status.state,'unloaded');
  }finally{delete global.location;}
});
