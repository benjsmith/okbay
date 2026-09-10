.pragma library
function parseStatus(t){try{return JSON.parse(t)}catch(e){return null}}
function needsSetup(s){return !s||s.state==="setup"||s.state==="missing"}
function label(s,stale){if(!s||needsSetup(s))return"SETUP";if(stale)return"STALE";if(s.desk&&s.desk.id)return String(s.desk.id).toUpperCase();return String(s.pages||0)}
function isStale(s,now,sec){if(!s||!s.ts)return true;var ms=Number(s.ts)>1e12?Number(s.ts):Number(s.ts)*1000;return (now-ms)>sec*1000}
function getJson(url,cb){var x=new XMLHttpRequest();x.onreadystatechange=function(){if(x.readyState!==4)return;var p=null;try{p=JSON.parse(x.responseText)}catch(e){}cb(p,x.status)};x.open("GET",url);x.send()}
function postJson(url,body,cb){var x=new XMLHttpRequest();x.onreadystatechange=function(){if(x.readyState!==4)return;var p=null;try{p=JSON.parse(x.responseText)}catch(e){}cb(p,x.status)};x.open("POST",url);x.setRequestHeader("Content-Type","application/json");x.send(JSON.stringify(body||{}))}
