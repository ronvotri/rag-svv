'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'..');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,'patches',name),'utf8'));
function placeholders(text){
  const source=text.replace(/%%/g,'');
  return [...source.matchAll(/%(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?[sdfioxXc]/g)]
    .filter(match=>!(match[0].startsWith('% ')&&/\d/.test(source[match.index-1]||'')))
    .map(match=>match[0]);
}
const markup=text=>text.match(/\[\/?(?:b|i|u|s|center|right|left|fill|color|bgcolor|font|font_size|outline_color|outline_size|url|img|table|cell|indent|code|kbd)(?:=[^\]]+)?\]/g)||[];
test('authored Vietnamese extra UI preserves ordered printf placeholders and escaped percentages',()=>{
  const extra=read('vi-ui-extra.json');assert.ok(Object.keys(extra).length>=300);
  for(const [english,vietnamese]of Object.entries(extra)){
    assert.equal(typeof vietnamese,'string',english);assert.ok(vietnamese.trim(),english);
    assert.notEqual(vietnamese,english,'Do not count unchanged acronyms as translated: '+english);
    assert.ok(english.length<=120,'Extra dictionary is scoped to short UI: '+english);
    assert.deepEqual(placeholders(vietnamese),placeholders(english),'Ordered format arguments changed: '+english);
    assert.equal((vietnamese.match(/%%/g)||[]).length,(english.match(/%%/g)||[]).length,'Escaped percent changed: '+english);
    assert.deepEqual(markup(vietnamese),markup(english),'Godot markup changed: '+english);
    assert.equal((vietnamese.match(/\n/g)||[]).length,(english.match(/\n/g)||[]).length,'Line breaks changed: '+english);
  }
});
test('primary and extra UI dictionaries combine without conflicting translations',()=>{
  const base=read('vi-ui.json'),extra=read('vi-ui-extra.json');
  for(const [english,vietnamese]of Object.entries(extra))if(Object.hasOwn(base,english))assert.equal(vietnamese,base[english],'Conflicting authored translation: '+english);
  const combined={...base,...extra};
  for(const key of ['Equipment & inventory  (Q / I)','Inventory  %d/%d','FPS limit','Job Change','You have fallen'])assert.ok(combined[key],key);
});
