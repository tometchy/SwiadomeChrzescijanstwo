const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const js = fs.readFileSync('assets/js/site.js', 'utf8');

function setup(searchText, query) {
  const cards = [
    {dataset:{search:'Pismo Święte Przekład Toruński Biblia TNP Nowy Testament 9788396908087',category:'Biblie',order:'36'},
     hidden:false,querySelector:()=>({textContent:'Pismo Święte'})},
    {dataset:{search:'Duch Święty i moc John Wesley 9788396908049',category:'Duch Święty',order:'31'},
     hidden:false,querySelector:()=>({textContent:'Duch Święty i moc'})},
    {dataset:{search:'W cieniu Wszechmogącego Elisabeth Elliot biografia Jim Elliot',category:'Biografie',order:'16'},
     hidden:false,querySelector:()=>({textContent:'W cieniu Wszechmogącego'})},
  ];
  const input={value:searchText,addEventListener(event,fn){this.listener=fn;}};
  const count={textContent:''}, empty={hidden:true};
  const grid={querySelectorAll(){return cards;},appendChild(){}};
  const document={
    querySelector(selector){ if(selector==='.nav-toggle'||selector==='.reset-filters')return null; return null; },
    getElementById(id){return ({'book-grid':grid,'book-search':input,'visible-count':count,'book-sort':null,'no-results':empty})[id]??null;},
    querySelectorAll(){return [];}
  };
  vm.runInNewContext(js,{document,window:{location:{search:query||''}},URLSearchParams,console});
  return {cards,input,count,empty};
}
test('Biblia matches the Toruń edition via its synonyms',()=>{
  const x=setup('Biblia');
  assert.equal(x.count.textContent,'1');
  assert.equal(x.cards[0].hidden,false);
});
test('Search is accent-insensitive and matches unordered terms across fields',()=>{
  const x=setup('torunski pismo 9788396908087');
  assert.equal(x.count.textContent,'1');
  assert.equal(x.cards[0].hidden,false);
});
test('Other terms and ISBN prefix work without false positives',()=>{
  assert.equal(setup('9788396908049').count.textContent,'1');
  assert.equal(setup('duch wesley').count.textContent,'1');
  assert.equal(setup('zzzzbadvalue').count.textContent,'0');
});
test('Deep link query prefills search',()=>{
  const x=setup('', '?q=Biblia');
  assert.equal(x.input.value,'Biblia');
  assert.equal(x.count.textContent,'1');
});
test('Search can find author aliases and topics',()=>{
  const x=setup('Jim Elliot');
  assert.equal(x.count.textContent,'1');
  assert.equal(x.cards[2].hidden,false);
});
