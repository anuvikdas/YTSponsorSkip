// Offline integration: actual contextual detector -> worker -> content -> PlaybackController.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { execFileSync } = require("node:child_process");
const root = path.resolve(__dirname, "../..");
const friends = "I9hJ_Rux9y0";
const negative = "U3aXWizDbQ4";
const actual = JSON.parse(execFileSync(path.join(root, ".venv/bin/python"), ["-c", `
import json,hashlib
from pathlib import Path
from dataclasses import asdict
from ytsponsorskip.contextual_detector import ContextualPromotionDetector
from ytsponsorskip.providers.saved import SavedTuneTranscriptProvider
p=Path('backend/src/ytsponsorskip')
version='contextual-v1-sha256:'+hashlib.sha256((p/'detector.py').read_bytes()+(p/'contextual_detector.py').read_bytes()).hexdigest()[:16]
print(json.dumps({'version':version,'videos':{v:[asdict(i) for i in ContextualPromotionDetector().detect(SavedTuneTranscriptProvider().fetch(v,['en'])).intervals] for v in ['I9hJ_Rux9y0','U3aXWizDbQ4']}}))
`], {cwd:root, encoding:"utf8"}));

class Video {
  constructor(time, paused=false, duration=1000) {
    this._currentTime=time; this.paused=paused; this.duration=duration;
    this.seeking=false; this.listeners=new Map(); this.seeks=[];
  }
  get currentTime(){ return this._currentTime; }
  set currentTime(value){ this.seeks.push(value); this.userSeek(value); }
  addEventListener(name,fn){ if(!this.listeners.has(name)) this.listeners.set(name,new Set()); this.listeners.get(name).add(fn); }
  removeEventListener(name,fn){ this.listeners.get(name)?.delete(fn); }
  emit(name){ for(const fn of this.listeners.get(name)||[]) fn(); }
  tick(value){ this._currentTime=value; this.emit("timeupdate"); }
  userSeek(value){ this._currentTime=value; this.seeking=true; this.emit("seeking"); this.seeking=false; this.emit("seeked"); }
}

function harness({time=682,paused=false,duration=1000,liveBadge=false}={}) {
  const settings={enabled:true, sensitivity:"conservative", detectorVariant:"contextual_v1",
    experimentalAutoSkip:true, previewDetectedPromotions:false, previewTranscriptSource:"saved",
    developmentFixtures:false, developmentBrowserAcquisition:false,
    backendUrl:"http://127.0.0.1:8000", showNotifications:false};
  const stored=new Map(), requests=[], docListeners=new Map(), detectionTimeouts=[];
  const video=new Video(time,paused,duration);
  const location={href:`https://www.youtube.com/watch?v=${friends}`};
  let workerListener,contentListener,settingsListener,notice,monitor;
  let backendVersion=actual.version;
  const timer=(fn,ms)=>{if(ms===35000)detectionTimeouts.push(fn);const handle=setTimeout(fn,ms);handle.unref();return handle;};
  const node=()=>({children:[],style:{},appendChild(child){this.children.push(child);},
    addEventListener(name,fn){this[name]=fn;},remove(){if(notice===this)notice=null;}});
  const sync={get:async()=>({...settings})};
  const session={set:async values=>{for(const [k,v] of Object.entries(values))stored.set(k,v);},
    get:async key=>({[key]:stored.get(key)}),
    remove:async keys=>{for(const k of Array.isArray(keys)?keys:[keys])stored.delete(k);}};
  const worker=vm.createContext({URL,AbortController,Promise,Map,Date,console,setTimeout:timer,clearTimeout,
    fetch:async(url,options)=>{
      if(String(url).includes("demo-status")) return {ok:true,json:async()=>({
        detector_variant:"contextual_v1", detector_version:backendVersion,
        native_attempts_remaining:4,native_attempt_limit:5,native_attempts_used:1})};
      return new Promise(resolve=>requests.push({url:String(url),options,resolve}));
    },
    chrome:{runtime:{onMessage:{addListener(fn){workerListener=fn;}}},
      storage:{sync,session},tabs:{sendMessage:async(_id,msg)=>contentListener(msg,{},()=>{}),
        onRemoved:{addListener(){}}}}});
  worker.importScripts=(...names)=>{for(const name of names)vm.runInContext(fs.readFileSync(path.join(root,"extension",name),"utf8"),worker);};
  vm.runInContext(fs.readFileSync(path.join(root,"extension/service-worker.js"),"utf8"),worker);
  const content=vm.createContext({URL,Date,Promise,Set,Map,Number,Array,Object,location,
    crypto:{randomUUID:()=>String(Math.random())},setTimeout:timer,clearTimeout,
    setInterval:(fn,ms)=>{if(ms===10000)monitor=fn;return 0;},
    MutationObserver:class{observe(){}},window:{addEventListener(){}},
    getComputedStyle:()=>({display:"none",visibility:"visible"}),
    document:{documentElement:{},body:{appendChild(n){notice=n;}},createElement:node,
      querySelector(selector){return selector==="video"?video:selector==="#ytss-notification"?notice:
        selector===".ytp-live-badge"&&liveBadge?{disabled:false,offsetParent:{}}:null;},
      addEventListener(name,fn){docListeners.set(name,fn);},dispatchEvent(){}},
    chrome:{storage:{sync,onChanged:{addListener(fn){settingsListener=fn;}}},
      runtime:{sendMessage:msg=>new Promise(resolve=>{
        if(workerListener(msg,{tab:{id:1}},resolve)!==true)resolve();
      }),
        onMessage:{addListener(fn){contentListener=fn;}}}}});
  for(const name of ["defaults.js","playback-controller.js","development-fixtures.js","content.js"])
    vm.runInContext(fs.readFileSync(path.join(root,"extension",name),"utf8"),content);
  const flush=async()=>{for(let i=0;i<5;i++)await new Promise(resolve=>setImmediate(resolve));};
  return {video,stored,requests,settings,flush,
    async backendChanged(){backendVersion="rules-sha256:changed";await monitor();await flush();},
    timeout:async()=>{await detectionTimeouts.at(-1)();await flush();},
    fail(request,code="TRIAL_BUDGET_EXHAUSTED"){
      request.resolve({ok:false,status:503,json:async()=>({error:{code}})});
    },
    resolve(request,indexVideo=friends,overrides={}){
      const u=new URL(request.url);
      request.resolve({ok:true,status:200,json:async()=>({status:"ready", video_id:indexVideo,
        request_id:request.options.headers["X-Request-ID"],mode:u.searchParams.get("mode"),
        transcript_source:u.searchParams.get("source"),detector_version:actual.version,
        language_code:"en",transcript_provider:"saved-reviewed-tune",intervals:actual.videos[indexVideo],
        ...overrides})});
    },
    async navigate(id){location.href=`https://www.youtube.com/watch?v=${id}`;video._currentTime=0;docListeners.get("yt-navigate-finish")();await flush();},
    async change(patch){Object.assign(settings,patch);settingsListener(Object.fromEntries(Object.entries(patch).map(([k,v])=>[k,{newValue:v}])),"sync");await flush();},
    undo(){const state=stored.get("tab-1");let answer;contentListener({type:"undo-last-skip",videoId:state.videoId,requestId:state.requestId},{},r=>answer=r);return answer;},
    notice:()=>notice
  };
}

test("actual detector predictions skip during playback; notification Undo has no loop and replay works",async()=>{
  const h=harness({time:684.25,liveBadge:true});await h.flush();h.resolve(h.requests[0]);await h.flush();
  assert.equal(h.video.currentTime,715);
  assert.equal(h.notice().children[1].textContent,"Undo");
  h.notice().children[1].click();await h.flush();
  assert.equal(h.video.currentTime,684.25);h.video.tick(685);assert.equal(h.video.currentTime,685);
  h.video.tick(716);h.video.userSeek(680);h.video.tick(684);assert.equal(h.video.currentTime,715);
  assert.equal(h.video.paused,false);
});

test("predictions arriving paused skip remaining time; results after the interval never rewind",async()=>{
  for(const [time,expected] of [[684,715],[720,720]]){
    const h=harness({time,paused:true});await h.flush();h.resolve(h.requests[0]);await h.flush();
    assert.equal(h.video.currentTime,expected);assert.equal(h.video.paused,true);
  }
});

test("deliberate seeking into predictions wins before and after results arrive",async()=>{
  const h=harness();await h.flush();h.video.userSeek(685);h.resolve(h.requests[0]);await h.flush();
  h.video.tick(686);assert.equal(h.video.currentTime,686);
  h.video.userSeek(720);h.video.userSeek(680);h.video.tick(684);assert.equal(h.video.currentTime,715);
  h.video.userSeek(686);h.video.tick(687);assert.equal(h.video.currentTime,687);
});

test("same-tab navigation rejects pending old predictions and negative result clears the state",async()=>{
  const h=harness();await h.flush();const old=h.requests[0];await h.navigate(negative);
  h.resolve(old);h.resolve(h.requests[1],negative);await h.flush();
  assert.equal(h.stored.get("tab-1").status,"no-promotions");assert.equal(h.stored.get("tab-1").videoId,negative);
  h.video.tick(684);assert.equal(h.video.currentTime,684);assert.equal(h.video.seeks.length,0);
});

test("disabling experimental skipping clears loaded intervals and pending responses",async()=>{
  const h=harness();await h.flush();h.resolve(h.requests[0]);await h.flush();
  await h.change({experimentalAutoSkip:false});h.video.tick(684);assert.equal(h.video.currentTime,684);
  assert.equal(h.undo().undone,false);
  const pending=harness();await pending.flush();await pending.change({enabled:false});
  pending.resolve(pending.requests[0]);await pending.flush();pending.video.tick(684);
  assert.equal(pending.video.currentTime,684);assert.equal(pending.stored.get("tab-1").status,"disabled");
});

test("source/mode changes invalidate old responses; wrong detector and invalid duration never seek",async()=>{
  const h=harness();await h.flush();const old=h.requests[0];await h.change({previewTranscriptSource:"supadata"});
  h.resolve(old);await h.flush();h.video.tick(684);assert.equal(h.video.currentTime,684);
  h.resolve(h.requests[1],friends,{detector_version:"rules-sha256:wrong"});await h.flush();
  assert.equal(h.stored.get("tab-1").status,"unavailable");assert.equal(h.video.currentTime,684);
  await h.change({sensitivity:"aggressive"});h.video.tick(684);assert.equal(h.video.currentTime,684);
  await h.change({detectorVariant:"frozen_rules"});assert.equal(h.video.currentTime,684);
  for(const duration of [700,NaN]){
    const bad=harness({time:684,duration});await bad.flush();bad.resolve(bad.requests[0]);await bad.flush();
    assert.equal(bad.video.currentTime,684);
  }
  const live=harness({time:684,duration:Infinity});await live.flush();
  assert.equal(live.requests.length,0);assert.equal(live.stored.get("tab-1").status,"unsupported");
});

test("budget errors and timeouts leave playback normal, and late success after timeout is ignored",async()=>{
  const failed=harness({time:684});await failed.flush();failed.fail(failed.requests[0]);await failed.flush();
  assert.equal(failed.stored.get("tab-1").reason,"TRIAL_BUDGET_EXHAUSTED");
  assert.equal(failed.video.seeks.length,0);failed.video.tick(686);assert.equal(failed.video.currentTime,686);
  assert.equal(failed.stored.get("tab-1").nativeBudget.native_attempts_remaining,4);
  const timed=harness({time:684});await timed.flush();await timed.timeout();
  timed.resolve(timed.requests[0]);await timed.flush();
  assert.equal(timed.stored.get("tab-1").reason,"DETECTION_TIMEOUT");
  assert.equal(timed.video.seeks.length,0);
});

test("preview still shows actual predictions but never wires them to playback",async()=>{
  const h=harness({time:684});await h.flush();
  await h.change({experimentalAutoSkip:false,previewDetectedPromotions:true});
  h.resolve(h.requests.at(-1));await h.flush();
  assert.equal(h.stored.get("tab-1").status,"predictions-available");
  assert.equal(h.video.currentTime,684);assert.equal(h.video.seeks.length,0);
});

test("a backend detector change clears previously accepted intervals without reacquisition",async()=>{
  const h=harness();await h.flush();h.resolve(h.requests[0]);await h.flush();
  await h.backendChanged();h.video.tick(684);
  assert.equal(h.video.currentTime,684);assert.equal(h.requests.length,1);
  assert.equal(h.stored.get("tab-1").reason,"DETECTOR_REVALIDATION_FAILED");
});
