'use strict';
// The two webviews as HTML strings. Every catalog, case, log and question text goes through esc() and is inserted
// as text, never as markup. The pages carry a Content-Security-Policy with a per-load nonce, no inline style
// attributes (widths and heights are set from data-* attributes by the page script through the style API), and
// one script. No `vscode` import.

const crypto = require('crypto');
const { cssVariables, scoreRole } = require('./theme');

function esc(value) {
  return String(value === undefined || value === null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function nonce() {
  return crypto.randomBytes(16).toString('base64');
}

function csp(nonceValue, cspSource) {
  return ["default-src 'none'", 'style-src ' + cspSource + " 'nonce-" + nonceValue + "'", "script-src 'nonce-" + nonceValue + "'",
    'font-src ' + cspSource, 'img-src ' + cspSource + ' data:'].join('; ');
}

const ICON = {
  refresh: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/></svg>',
  search: '<svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/></svg>',
  chevron: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>',
  caret: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
  help: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 0 1 4.6 1.3c0 1.7-2.1 2-2.1 3.4"/><path d="M12 17.5v.01"/></svg>',
  close: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  check: '<svg class="c-ok" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><path d="M12 16.5v.01"/></svg>',
  offline: '<svg class="c-warn" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 8.5a15 15 0 0 1 20 0"/><path d="M5.5 12a10 10 0 0 1 13 0"/><path d="M9 15.5a5 5 0 0 1 6 0"/><path d="M3 3l18 18"/></svg>',
  alert: '<svg class="c-bad" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l9 16H3z"/><path d="M12 10v4"/><path d="M12 17v.01"/></svg>'
};

const STYLE = `
*{box-sizing:border-box}
[hidden]{display:none!important}
html,body{margin:0;padding:0;height:100%}
body{background:var(--bg);color:var(--text);font-family:var(--vscode-font-family);font-size:13px;line-height:1.5;-webkit-font-smoothing:antialiased}
button,input{font:inherit;color:inherit}
button{cursor:pointer}
button:disabled,[aria-disabled="true"]{cursor:default;opacity:.55}
button:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
a{color:inherit;text-decoration:underline;text-underline-offset:3px;text-decoration-color:var(--line-strong)}
a:hover{text-decoration-color:currentColor}
code,.mono{font-family:var(--vscode-editor-font-family,monospace)}
h1,h2,p{margin:0}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.c-ok{color:var(--ok)!important}.c-warn{color:var(--warn)!important}.c-bad{color:var(--bad)!important}.c-dim{color:var(--text-2)!important}.c-text{color:var(--text)!important}
.bg-ok{background:var(--ok)}.bg-warn{background:var(--warn)}.bg-bad{background:var(--bad)}.bg-dim{background:var(--text-3)}.bg-none{background:var(--text-3)}.bg-off{background:var(--text-3)}.bg-unknown{background:var(--text-3)}.bg-update{background:var(--warn)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.pulse{animation:pulse 1.2s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){.pulse{animation:none}}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.08em;color:var(--text-2)}
.tile{display:inline-flex;align-items:center;justify-content:center;flex:none;font-family:var(--vscode-editor-font-family,monospace);font-weight:500;letter-spacing:-.04em;background:var(--raised);color:var(--text);box-shadow:inset 0 0 0 1px var(--line-strong)}
.tile.s30{width:30px;height:30px;border-radius:8px;font-size:11.5px}
.tile.s76{width:76px;height:76px;border-radius:18px;font-size:26px;box-shadow:inset 0 0 0 1px var(--line-strong),0 10px 28px var(--shadow)}
.btn{height:30px;padding:0 12px;border:0;border-radius:7px;background:var(--raised);box-shadow:inset 0 0 0 1px var(--line-strong);color:var(--text);font-size:12.5px;font-weight:600;white-space:nowrap}
.btn.primary{background:var(--accent);color:var(--on-accent);box-shadow:none}
.btn.danger{background:var(--danger);color:var(--on-danger);box-shadow:none}
.btn.quiet{background:transparent;box-shadow:none;color:var(--text-2);font-weight:500}
.btn.sm{height:26px;padding:0 10px;border-radius:6px;font-size:12px}
.btn.lg{height:34px;padding:0 16px;border-radius:8px}
.seg{display:flex;gap:2px;padding:2px;border-radius:8px;background:var(--track)}
.seg.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}
.seg button{height:26px;padding:0 10px;border:0;border-radius:6px;background:transparent;color:var(--text-2);font-size:12px;font-weight:500}
.seg button[aria-pressed="true"]{background:var(--raised);color:var(--text);box-shadow:0 0 0 1px var(--line-strong),0 1px 2px var(--shadow-soft)}
.card{border-radius:14px;background:var(--surface);box-shadow:inset 0 0 0 1px var(--line),0 1px 2px var(--shadow-soft)}
.notice{display:flex;gap:12px;align-items:flex-start;border-radius:12px;padding:14px;background:var(--surface);box-shadow:inset 0 0 0 1px var(--line-strong)}
.notice.warn{background:var(--warn-bg);box-shadow:inset 0 0 0 1px var(--warn-line)}
.notice.bad{background:var(--bad-bg);box-shadow:inset 0 0 0 1px var(--bad-line)}
.notice .icon{flex:none;margin-top:1px;color:var(--text-2)}
.notice .stack{display:flex;flex-direction:column;gap:4px;min-width:0}
.notice .title{font-weight:600}
.notice .body{font-size:12.5px;color:var(--text-2);line-height:1.5}
.notice .actions{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}
.register{border-radius:12px;padding:16px;background-color:var(--surface);background-image:radial-gradient(var(--dot) 1px,transparent 1px);background-size:14px 14px;box-shadow:inset 0 0 0 1px var(--line-strong),0 1px 2px var(--shadow-soft);display:flex;flex-direction:column;gap:10px}
.register .title{font-size:15px;font-weight:600;letter-spacing:-.01em}
.register .body{font-size:12.5px;color:var(--text-2);line-height:1.5}
.register code{font-size:11px;color:var(--text-2);overflow-wrap:anywhere}
.register .btn{height:34px;border-radius:8px}

/* the sidebar */
.side{display:flex;flex-direction:column;min-height:100%;background:var(--side)}
.side .top{padding:10px 12px 8px;display:flex;flex-direction:column;gap:10px}
.side .titlerow{display:flex;align-items:center;justify-content:space-between;padding:0 4px}
.iconbtn{width:28px;height:28px;border-radius:6px;background:transparent;border:0;color:var(--text-2);display:inline-flex;align-items:center;justify-content:center}
.iconbtn:hover:not(:disabled){background:var(--track)}
.search{position:relative;display:flex;align-items:center}
.search .search-icon{position:absolute;left:10px;color:var(--text-2)}
.search input{width:100%;height:32px;padding:0 34px 0 31px;background:var(--raised);border:1px solid var(--input-border);border-radius:7px;color:var(--text)}
.search input::placeholder{color:var(--text-2)}
.search kbd{position:absolute;right:8px;padding:0 6px;border-radius:4px;border:1px solid var(--line-strong);font-size:11px;color:var(--text-2);font-family:var(--vscode-editor-font-family,monospace)}
.side .main{display:flex;flex-direction:column;flex:1;min-height:0}
.side .gap{padding:0 12px 10px;display:flex;flex-direction:column;gap:10px}
.featured{margin:0 12px 10px;text-align:left;border:0;border-radius:12px;padding:14px;background-color:var(--surface);background-image:radial-gradient(var(--dot) 1px,transparent 1px);background-size:14px 14px;box-shadow:inset 0 0 0 1px var(--line-strong),0 1px 2px var(--shadow-soft);display:flex;flex-direction:column;gap:6px;color:var(--text)}
.featured .badge{align-self:flex-start;padding:2px 8px;border-radius:999px;background:var(--text);color:var(--on-accent);font-size:10.5px;font-weight:600}
.featured .name{font-size:14px;font-weight:600;letter-spacing:-.01em}
.featured .text{font-size:12px;color:var(--text-2);line-height:1.45}
.filters{display:flex;gap:4px;margin:0 12px;border-bottom:1px solid var(--line)}
.filters button{height:32px;display:flex;align-items:center;gap:6px;padding:0 6px;margin-bottom:-1px;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--text-2);font-size:12.5px;font-weight:500}
.filters button[aria-selected="true"]{border-bottom-color:var(--text);color:var(--text)}
.filters .count{min-width:16px;padding:0 5px;border-radius:8px;font-size:11px;line-height:16px;text-align:center;background:var(--track);color:var(--text-2)}
.filters .count.hot{background:var(--accent);color:var(--on-accent)}
.list{padding:8px 6px 12px;display:flex;flex-direction:column;gap:1px;flex:1}
.updateall{margin:0 4px 6px;padding:8px 10px;border-radius:8px;background:var(--surface);box-shadow:inset 0 0 0 1px var(--line);display:flex;align-items:center;gap:8px}
.updateall span{flex:1;font-size:12px;color:var(--text-2)}
.prow{display:flex;align-items:center;gap:8px;padding:7px 8px;border-radius:9px}
.prow.current{background:var(--selected);box-shadow:inset 0 0 0 1px var(--line-strong),0 1px 2px var(--shadow-soft)}
.prow .pick{flex:1;min-width:0;display:flex;align-items:center;gap:10px;padding:0;border:0;background:transparent;text-align:left;color:inherit}
.prow .names{flex:1;min-width:0;display:flex;flex-direction:column}
.prow .pname{font-weight:500}
.prow .psub{font-size:11.5px;color:var(--text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.getpill{height:24px;padding:0 10px;border-radius:999px;border:0;background:var(--track);color:var(--text);font-size:11.5px;font-weight:600}
.getpill.primary{background:var(--accent);color:var(--on-accent)}
.getpill:disabled{color:var(--text-2)}
.pscore{font-size:11.5px;font-weight:600;font-variant-numeric:tabular-nums}
.nomatch{margin:12px 10px;color:var(--text-2)}
.foot{padding:10px 16px;border-top:1px solid var(--line);display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--text-2)}
.foot .dot{width:6px;height:6px;border-radius:50%;background:var(--ok)}
.foot .grow{flex:1}

/* the plugin page */
.page{display:flex;flex-direction:column;height:100vh}
.grow-main{flex:1;min-height:0;display:flex;flex-direction:column}
.scroll{flex:1;overflow-y:auto;min-height:0}
.hero{padding:40px 48px 32px;background-color:var(--side);background-image:radial-gradient(var(--dot) 1px,transparent 1px);background-size:18px 18px;border-bottom:1px solid var(--line)}
.hero .inner{max-width:980px;margin:0 auto;display:flex;align-items:flex-start;gap:26px;flex-wrap:wrap}
.hero .text{flex:1;min-width:300px;display:flex;flex-direction:column;gap:10px}
.hero .meta{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-2);flex-wrap:wrap}
.hero h1{font-size:40px;line-height:1.08;font-weight:700;letter-spacing:-.035em}
.hero .desc{max-width:62ch;font-size:15px;line-height:1.6;color:var(--text-2)}
.statuspills{display:flex;gap:8px;flex-wrap:wrap;padding-top:2px}
.statuspill{display:inline-flex;align-items:center;gap:7px;height:26px;padding:0 11px 0 9px;border-radius:999px;background:var(--raised);box-shadow:inset 0 0 0 1px var(--line-strong);font-size:12px;font-weight:500}
.statuspill .dot,.dot{width:6px;height:6px;border-radius:50%;display:inline-block;flex:none}
.split{position:relative;display:flex;flex-direction:column;gap:8px;width:250px}
.split .splitbar{display:flex;height:40px;border-radius:9px;overflow:hidden;box-shadow:0 6px 18px var(--shadow-soft)}
.split .main{flex:1;border:0;background:var(--accent);color:var(--on-accent);font-size:13.5px;font-weight:600}
.split .arrow{width:38px;border:0;border-left:1px solid var(--split);background:var(--accent);color:var(--on-accent)}
.split .menu{position:absolute;top:46px;left:0;right:0;z-index:2;background:var(--raised);border-radius:10px;padding:6px;box-shadow:0 0 0 1px var(--line-strong),0 16px 40px var(--shadow);display:flex;flex-direction:column;gap:2px}
.split .menu button{height:34px;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:0 10px;border:0;border-radius:6px;background:transparent;color:var(--text);font-size:12.5px;text-align:left}
.split .menu button:hover{background:var(--track)}
.split .menu .h{font-size:11.5px;color:var(--text-2)}
.split .note{text-align:center;font-size:11.5px;color:var(--text-2)}
.pbody{max-width:980px;margin:0 auto;padding:28px 48px 56px;display:flex;flex-direction:column;gap:22px}
.evalrow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.evalrow .label{font-size:12px;color:var(--text-2)}
.evalrow .grow{flex:1}
.helpbtn{height:28px;display:flex;align-items:center;gap:5px;padding:0 8px;border-radius:6px;border:0;background:transparent;color:var(--text-2);font-size:12px}
.helpbox{border-radius:12px;background:var(--surface);box-shadow:inset 0 0 0 1px var(--line);padding:14px 16px;font-size:12.5px;line-height:1.6}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media (max-width:760px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{padding:28px 20px}.pbody{padding:20px}}
.stat{padding:16px 18px;display:flex;flex-direction:column;gap:4px}
.stat.ring{flex-direction:row;align-items:center;gap:14px}
.stat .k{font-size:11px;font-weight:600;letter-spacing:.07em;color:var(--text-2)}
.stat .v{font-size:32px;line-height:1.05;font-weight:700;letter-spacing:-.04em;font-variant-numeric:tabular-nums}
.stat .v small{font-size:15px;font-weight:600;color:var(--text-2);letter-spacing:0}
.stat .n{font-size:12px;color:var(--text-2)}
.stat .col{display:flex;flex-direction:column;gap:2px}
.ring svg{flex:none}
.ring .track{stroke:var(--track)}
.ring .arc.ok{stroke:var(--ok)}.ring .arc.warn{stroke:var(--warn)}.ring .arc.bad{stroke:var(--bad)}
.empty{border-radius:14px;border:1px dashed var(--line-strong);padding:22px;display:flex;flex-direction:column;gap:4px;align-items:center;text-align:center}
.empty .t{font-weight:600}
.empty .s{font-size:12.5px;color:var(--text-2)}
.sections{padding:0 24px 8px;border-radius:16px}
.tabs{display:flex;gap:22px;border-bottom:1px solid var(--line)}
.tabs button{height:50px;padding:0;margin-bottom:-1px;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--text-2);font-size:13.5px;font-weight:600}
.tabs button[aria-selected="true"]{border-bottom-color:var(--text);color:var(--text)}
.tabs .n{margin-left:6px;font-size:11.5px;color:var(--text-2);font-weight:500}
.contrib{display:flex;align-items:center;gap:10px;padding:14px 0 4px;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;gap:6px;height:22px;padding:0 8px;border-radius:6px;background:var(--track);font-size:11.5px;font-weight:600}
.contrib .sum{font-size:12px;color:var(--text-2)}
.contrib .grow{flex:1}
.srow{border-bottom:1px solid var(--line)}
.srow .line{display:grid;grid-template-columns:24px minmax(0,1fr) 240px 150px;gap:20px;align-items:center;padding:18px 0}
@media (max-width:760px){.srow .line{grid-template-columns:24px minmax(0,1fr);}}
.srow .nm{display:flex;flex-direction:column;gap:3px;min-width:0}
.srow .sname{font-family:var(--vscode-editor-font-family,monospace);font-size:13px;font-weight:500}
.srow .sdesc{font-size:12.5px;color:var(--text-2);line-height:1.55}
.srow .score{display:flex;align-items:center;gap:12px}
.bar{flex:1;height:8px;border-radius:4px;background:var(--track);overflow:hidden;display:block}
.bar span{display:block;height:100%;border-radius:4px}
.srow .pct{width:44px;text-align:right;font-size:15px;font-weight:700;font-variant-numeric:tabular-nums}
.srow .meta{text-align:right;font-size:12px;font-variant-numeric:tabular-nums}
.chev{width:24px;height:24px;display:flex;align-items:center;justify-content:center;padding:0;border:0;border-radius:6px;background:transparent;color:var(--text-2)}
.chev[aria-expanded="true"]{background:var(--track);transform:rotate(90deg)}
.cases{margin:0 0 18px 44px;border-radius:12px;background:var(--bg);box-shadow:inset 0 0 0 1px var(--line);overflow:hidden}
.cases .head{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid var(--line);font-size:12px}
.cases .head .grow{flex:1}
.crow{display:grid;grid-template-columns:118px minmax(0,1fr) 150px 64px;gap:14px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--line)}
@media (max-width:760px){.crow{grid-template-columns:minmax(0,1fr) 64px}}
.kind{justify-self:start;display:inline-flex;align-items:center;height:22px;padding:0 8px;border-radius:6px;font-size:11px;font-weight:600;white-space:nowrap}
.kind.fires{background:var(--track);color:var(--text)}
.kind.quiet{background:transparent;color:var(--text-2);box-shadow:inset 0 0 0 1px var(--line-strong)}
.kind.behavior{background:var(--accent);color:var(--on-accent)}
.crow .cn{display:flex;flex-direction:column;min-width:0}
.crow .cname{font-family:var(--vscode-editor-font-family,monospace);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.crow .cdesc{font-size:12px;color:var(--text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.crow .res{display:flex;flex-direction:column;align-items:flex-end}
.crow .rt{font-size:12.5px;font-weight:700;font-variant-numeric:tabular-nums}
.crow .rm{font-size:11px;color:var(--text-2)}
.runs{padding:22px 0 14px;display:flex;flex-direction:column;gap:12px}
.runs .hd{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px}
.runs .hd b{font-weight:600}.runs .hd span{font-size:11.5px;color:var(--text-2)}
.chart{height:150px;display:flex;align-items:flex-end;gap:12px;padding:0 4px;border-bottom:1px solid var(--line)}
.col2{flex:1;max-width:64px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:6px;height:100%}
.col2 .p{font-size:11.5px;font-weight:600;font-variant-numeric:tabular-nums}
.col2 .b{display:block;width:100%;border-radius:6px 6px 2px 2px}
.labels{display:flex;gap:12px;padding:0 4px}
.labels span{flex:1;max-width:64px;text-align:center;font-size:11px;color:var(--text-2);line-height:1.35}
.runs .note{font-size:12px;color:var(--text-2)}
.irow{display:flex;align-items:center;gap:14px;padding:16px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}
.irow .info{flex:1;min-width:200px;display:flex;flex-direction:column;gap:2px}
.irow .hn{font-weight:600}
.irow .st{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-2)}
.irow code{font-size:11.5px;color:var(--text-2);overflow-wrap:anywhere}
.irow .slots{display:grid;grid-template-columns:96px 96px;gap:8px}
.irow .slot{display:flex}
.irow .slot .btn{width:100%;height:32px}
.irow .slot .ok{width:100%;height:32px;display:flex;align-items:center;justify-content:center;gap:5px;font-size:12px;color:var(--text-2)}

/* the Eval run tray */
.tray{flex:none;border-top:1px solid var(--line);background:var(--side);display:flex;flex-direction:column}
.tray .hd{height:38px;display:flex;align-items:center;gap:12px;padding:0 8px 0 16px;border-bottom:1px solid var(--line)}
.tray .hd .eyebrow{padding:11px 0 10px;border-bottom:1px solid var(--text)}
.tray .hd .t{font-weight:600;font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tray .hd .m{font-size:12px;color:var(--text-2);white-space:nowrap}
.tray .hd .grow{flex:1}
.progress{height:3px;background:var(--track)}
.progress span{display:block;height:100%;background:var(--text);transition:width .4s}
.tray .cols{display:flex;flex-wrap:wrap;max-height:220px}
.tray .items{flex:1 1 300px;min-width:0;max-height:220px;overflow-y:auto;padding:8px 10px;border-right:1px solid var(--line);display:flex;flex-direction:column;gap:1px}
.titem{display:flex;align-items:center;gap:10px;min-height:30px;padding:0 6px;border-radius:6px}
.titem .ic{width:14px;text-align:center;font-size:12px}
.titem .nm{flex:1;min-width:0;font-family:var(--vscode-editor-font-family,monospace);font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.titem .stt{font-size:11.5px;font-weight:600;font-variant-numeric:tabular-nums}
.titem .link{height:22px;padding:0 8px;border-radius:5px;border:0;background:transparent;color:var(--text-2);font-size:11.5px;text-decoration:underline;text-underline-offset:2px}
.tray .out{flex:2 1 420px;min-width:0;max-height:220px;overflow-y:auto;padding:10px 16px 14px;display:flex;flex-direction:column;gap:10px}
.ask{border-radius:10px;padding:12px 14px;background:var(--raised);box-shadow:inset 0 0 0 1px var(--line-strong),0 4px 14px var(--shadow-soft);display:flex;flex-direction:column;gap:10px}
.ask .q{font-size:13px;line-height:1.5;overflow-wrap:anywhere}
.ask .btns{display:flex;gap:6px;flex-wrap:wrap}
.log{font-family:var(--vscode-editor-font-family,monospace);font-size:11.5px;line-height:1.65;display:flex;flex-direction:column}
.log span{white-space:pre-wrap;overflow-wrap:anywhere}
.log .cmd{color:var(--text-2)}.log .ask-l{color:var(--warn)}.log .err{color:var(--bad)}.log .dim{color:var(--text-2)}
.errcard{margin:4px 14px 14px;border-radius:10px;padding:12px;background:var(--bad-bg);box-shadow:inset 0 0 0 1px var(--bad-line);display:flex;flex-direction:column;gap:4px}
.errcard.plain{background:var(--surface);box-shadow:inset 0 0 0 1px var(--line-strong)}
.errcard .t{font-weight:600;font-size:12.5px;overflow-wrap:anywhere}
.errcard .b{font-size:12px;color:var(--text-2);line-height:1.5}
.errcard .actions{display:flex;gap:6px;margin-top:4px}
.engine{margin:14px 0 4px}
.engine .notice{background:var(--bad-bg);box-shadow:inset 0 0 0 1px var(--bad-line)}

/* the confirmation dialog */
.scrim{position:fixed;inset:0;background:var(--scrim);display:flex;align-items:center;justify-content:center;padding:16px;z-index:10}
.dialog{width:460px;max-width:100%;background:var(--raised);border-radius:14px;box-shadow:0 0 0 1px var(--line-strong),0 24px 60px var(--shadow);display:flex;flex-direction:column;max-height:100%;overflow:auto}
.dialog .hd{padding:20px 22px 0;display:flex;flex-direction:column;gap:8px}
.dialog h2{font-size:16px;font-weight:600;letter-spacing:-.01em;overflow-wrap:anywhere}
.dialog p{font-size:13px;line-height:1.55;color:var(--text-2)}
.dialog .cmds{margin:14px 22px 0;padding:10px 12px;border-radius:8px;background:var(--side);box-shadow:inset 0 0 0 1px var(--line);font-family:var(--vscode-editor-font-family,monospace);font-size:12px;display:flex;flex-direction:column;gap:4px}
.dialog .cmds code{overflow-wrap:anywhere}
.dialog .cmds i{color:var(--text-2);font-style:normal}
.dialog .ft{padding:16px 22px 18px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.dialog .ft label{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--text-2);cursor:pointer;min-height:28px}
.dialog .ft input{width:15px;height:15px;margin:0;accent-color:var(--accent)}
.dialog .ft .grow{flex:1}
`;

function bgClass(role) {
  return 'bg-' + role;
}

function button(label, act, attrs, cls) {
  const data = Object.keys(attrs || {}).map((k) => ' data-' + k + '="' + esc(attrs[k]) + '"').join('');
  return '<button type="button" class="' + esc(cls || 'btn') + '" data-act="' + esc(act) + '"' + data + '>' + esc(label) + '</button>';
}

function tile(markText, size) {
  return '<span class="tile s' + size + '" aria-hidden="true">' + esc(markText) + '</span>';
}

function dialogHtml(d) {
  if (!d) return '';
  const cmds = d.commands.map((c) => '<code><i>$ </i>' + esc(c) + '</code>').join('');
  return '<div class="scrim"><div class="dialog" id="dlg" role="dialog" aria-modal="true" aria-labelledby="dlg-title">' +
    '<div class="hd"><h2 id="dlg-title">' + esc(d.title) + '</h2><p>' + esc(d.body) + '</p></div>' +
    '<div class="cmds">' + cmds + '</div>' +
    '<div class="ft">' + (d.canSkip ? '<label><input type="checkbox" id="dont-ask">Don’t ask again</label>' : '') + '<span class="grow"></span>' +
    '<button type="button" class="btn lg" data-act="cancel">Cancel</button>' +
    '<button type="button" class="btn lg ' + (d.danger ? 'danger' : 'primary') + '" data-act="confirm" data-id="' + esc(d.id) + '" data-autofocus="1">' + esc(d.confirmLabel) + '</button>' +
    '</div></div></div>';
}

function noticeHtml(n) {
  if (n.kind === 'register') {
    return '<div class="register"><span class="title">' + esc(n.title) + '</span><span class="body">' + esc(n.body) + '</span>' +
      n.buttons.map((b) => button(b.label, b.act, { source: b.source }, b.primary ? 'btn primary' : 'btn')).join('') +
      '<code>$ ' + esc(n.command) + '</code></div>';
  }
  const icon = n.kind === 'offline' ? ICON.offline : n.kind === 'rejected' ? ICON.alert : ICON.info;
  const tone = n.kind === 'offline' ? ' warn' : n.kind === 'rejected' ? ' bad' : '';
  const title = n.kind === 'no-exe' ? '<code>' + esc(n.code) + '</code>' + esc(n.title) : esc(n.title);
  return '<div class="notice' + tone + '"><span class="icon">' + icon + '</span><span class="stack"><span class="title">' + title + '</span>' +
    '<span class="body">' + esc(n.body) + '</span>' +
    (n.buttons.length ? '<span class="actions">' + n.buttons.map((b) => button(b.label, b.act, {}, b.quiet ? 'btn sm quiet' : 'btn sm')).join('') + '</span>' : '') +
    '</span></div>';
}

// --- the sidebar ---

function rowHtml(r, selected) {
  const current = r.name === selected;
  let right = '';
  if (r.pill) {
    right = '<button type="button" class="getpill' + (r.pill.primary ? ' primary' : '') + '" data-act="ask" data-action="' + esc(r.pill.action) +
      '" data-plugin="' + esc(r.name) + '"' + (r.pill.disabled ? ' disabled' : '') + ' aria-label="' + esc(r.pill.label + ' ' + r.name) + '">' + esc(r.pill.label) + '</button>';
  } else if (r.score) {
    right = '<span class="pscore c-' + r.score.role + '" title="' + esc(r.score.title) + '">' + esc(r.score.text) + '</span>';
  } else {
    right = '<span class="pscore c-dim" title="No eval on this host yet">—</span>';
  }
  return '<div class="prow' + (current ? ' current' : '') + '" role="listitem"><button type="button" class="pick" data-act="select" data-plugin="' + esc(r.name) +
    '"' + (current ? ' aria-current="page"' : '') + '>' + tile(r.mark, 30) + '<span class="names"><span class="pname">' + esc(r.name) +
    '</span><span class="psub">' + esc(r.sub) + '</span></span></button>' + right + '</div>';
}

function sidebarMain(m) {
  if (m.empty) {
    if (m.problem) return '<div class="gap">' + noticeHtml({ kind: 'rejected', title: 'The catalog could not be loaded', body: m.problem.message,
      buttons: [{ label: 'Try again', act: 'refresh' }, { label: 'Settings', act: 'settings-catalog', quiet: true }] }) + '</div>' +
      '<div class="foot"><span class="dot"></span><span class="grow">' + esc(m.footer.source) + '</span></div>';
    return '<p class="nomatch">Loading the catalog…</p>';
  }
  const hosts = '<div class="gap"><div class="seg grid" role="group" aria-label="Host">' + m.hosts.map((h) =>
    '<button type="button" data-act="host" data-id="' + esc(h.id) + '" aria-pressed="' + h.pressed + '">' + esc(h.label) + '</button>').join('') + '</div>' +
    m.notices.map(noticeHtml).join('') + '</div>';
  const featured = m.featured ? '<button type="button" class="featured" data-act="select" data-plugin="' + esc(m.featured.plugin) + '">' +
    '<span class="badge">' + esc(m.featured.note) + '</span><span class="name">' + esc(m.featured.plugin) + '</span><span class="text">' + esc(m.featured.text) + '</span></button>' : '';
  const filters = '<div class="filters" role="tablist" aria-label="Filter">' + m.filters.map((f) =>
    '<button type="button" role="tab" data-act="filter" data-id="' + esc(f.id) + '" aria-selected="' + f.selected + '">' + esc(f.label) +
    '<span class="count' + (f.hot ? ' hot' : '') + '">' + f.count + '</span></button>').join('') + '</div>';
  const updateAll = m.updateAll ? '<div class="updateall"><span>' + esc(m.updateAll.text) + '</span>' + button('Update all', 'update-all', {}, 'btn sm primary') + '</div>' : '';
  const noMatch = m.noMatch ? '<p class="nomatch">No plugin or skill matches “' + esc(m.noMatch) + '”.</p>' : '';
  return hosts + featured + filters + '<div class="list" role="list">' + updateAll + noMatch + m.rows.map((r) => rowHtml(r, m.selected)).join('') + '</div>' +
    '<div class="foot"><span class="dot"></span><span class="grow">' + esc(m.footer.source) + '</span><span class="mono">' + esc(m.footer.version) + '</span></div>';
}

// The sidebar's regions: `main` is everything under the search field, which the page keeps as it is so typing is never interrupted.
function sidebarRegions(model, dialog) {
  return { main: sidebarMain(model), dialog: dialogHtml(dialog) };
}

function sidebarBody(model, dialog) {
  const regions = sidebarRegions(model, dialog);
  return '<div class="side"><div class="top"><div class="titlerow"><span class="eyebrow">EURUS SKILLS</span>' +
    '<button type="button" class="iconbtn" data-act="refresh" aria-label="Refresh">' + ICON.refresh + '</button></div>' +
    '<div class="search">' + ICON.search + '<label class="sr" for="q">Search plugins and skills</label>' +
    '<input id="q" type="search" autocomplete="off" placeholder="Search plugins and skills" value="' + esc(model.q) + '"><kbd aria-hidden="true">/</kbd></div></div>' +
    '<div class="main" id="r-main">' + regions.main + '</div></div><div id="r-dialog">' + regions.dialog + '</div>';
}

// --- the plugin page ---

function ringHtml(pct, role) {
  return '<svg width="58" height="58" viewBox="0 0 58 58" aria-hidden="true"><circle class="track" cx="29" cy="29" r="24" fill="none" stroke-width="6"/>' +
    '<circle class="arc ' + role + '" cx="29" cy="29" r="24" fill="none" stroke-width="6" stroke-linecap="round" pathLength="100" stroke-dasharray="' +
    Math.max(0, Math.min(100, pct)) + ' 100" transform="rotate(-90 29 29)"/></svg>';
}

function caseRowHtml(c, busy) {
  const res = c.result;
  return '<div class="crow"><span class="kind ' + esc(c.kind) + '">' + esc(c.kindLabel) + '</span><div class="cn"><span class="cname" title="' + esc(c.name) + '">' + esc(c.name) +
    '</span><span class="cdesc">' + esc(c.description) + '</span></div><div class="res"><span class="rt c-' + res.role + (res.pulse ? ' pulse' : '') + '">' + esc(res.text) +
    '</span><span class="rm">' + esc(res.meta) + '</span></div><button type="button" class="btn sm" data-act="run-case" data-case="' + esc(c.name) + '"' + (busy ? ' disabled' : '') +
    ' aria-label="' + esc('Run ' + c.name) + '">' + (busy ? '…' : 'Run') + '</button></div>';
}

function skillRowHtml(s, evalHostLabel, busy) {
  const chevron = s.canExpand ? '<button type="button" class="chev" data-act="toggle-skill" data-skill="' + esc(s.name) + '" aria-expanded="' + s.open +
    '" aria-label="' + esc((s.open ? 'Hide' : 'Show') + ' the eval cases of ' + s.name) + '">' + ICON.chevron + '</button>' : '';
  const line = '<div class="line" role="row"><div role="cell">' + chevron + '</div><div class="nm" role="cell"><span class="sname">' + esc(s.name) + '</span><span class="sdesc">' +
    esc(s.description) + '</span></div><div class="score" role="cell"><span class="bar"><span class="' + bgClass(s.role) + '" data-w="' + s.barPct + '"></span></span><span class="pct">' +
    esc(s.pct) + '</span></div><span class="meta ' + (s.low ? 'c-warn' : 'c-dim') + '" role="cell">' + esc(s.meta) + '</span></div>';
  const cases = s.open ? '<div class="cases"><div class="head"><b>' + s.caseCount + ' eval cases</b><span class="c-dim">on ' + esc(evalHostLabel) + '</span><span class="grow"></span>' +
    '<button type="button" class="btn sm" data-act="run-skill" data-skill="' + esc(s.name) + '"' + (busy ? ' disabled' : '') + '>' + esc(busy ? '…' : s.runLabel) + '</button></div>' +
    s.cases.map((c) => caseRowHtml(c, busy)).join('') + '</div>' : '';
  return '<div class="srow">' + line + cases + '</div>';
}

function engineErrorHtml(err) {
  return '<div class="engine"><div class="notice bad"><span class="icon">' + ICON.alert + '</span><span class="stack"><span class="title">' + renderCode(err.title) + '</span>' +
    '<span class="body">' + renderCode(err.body) + '</span><span class="actions">' + button('Open setting', 'open-setting', {}, 'btn sm primary') +
    button('Retry', 'retry-engine', {}, 'btn sm') + '</span></span></div></div>';
}

// `text` with `code` spans: the text is escaped first, so a backtick pair is the only markup that can appear.
function renderCode(text) {
  return esc(text).replace(/`([^`]+)`/g, '<code>$1</code>');
}

function sectionHtml(m) {
  if (m.section === 'skills') {
    const busy = m.jobRunning;
    const contributor = m.contributor ? '<div class="contrib"><span class="badge">Contributor</span><span class="sum">' + esc(m.contributor.summary) + '</span><span class="grow"></span>' +
      '<button type="button" class="btn primary" data-act="run-all"' + (busy ? ' disabled' : '') + '>' + esc(busy ? '…' : m.contributor.runAllLabel) + '</button></div>' : '';
    return '<div>' + contributor + (m.engineError ? engineErrorHtml(m.engineError) : '') + '<div role="table" aria-label="Skills">' +
      m.skills.map((s) => skillRowHtml(s, m.evalHostLabel, busy)).join('') + '</div></div>';
  }
  if (m.section === 'runs') {
    if (!m.runs.length) return '<div class="runs"><p class="c-dim">No archived run yet.</p></div>';
    return '<div class="runs"><div class="hd"><b>Archived runs, oldest to newest</b><span>bar height = score · label = cases in that run</span></div>' +
      '<div class="chart">' + m.runs.map((r) => '<div class="col2" title="' + esc(r.title) + '"><span class="p">' + esc(r.pct) + '</span><span class="b ' + bgClass(r.role) + '" data-h="' + Math.round(r.barPct * 1.12) + '"></span></div>').join('') + '</div>' +
      '<div class="labels">' + m.runs.map((r) => '<span>' + esc(r.when) + '<br>' + esc(r.cases) + '</span>').join('') + '</div>' +
      '<span class="note">A run can cover a few cases only, for example a rerun after a fix, so one bar is not the plugin’s score.</span></div>';
  }
  return '<div>' + m.install.map((h) => {
    const un = h.canUninstall ? button('Uninstall', 'ask', { action: 'uninstall', host: h.id }, 'btn') : '';
    let right = '';
    if (h.primary) right = '<button type="button" class="btn primary" data-act="ask" data-action="' + esc(h.primary.action) + '" data-host="' + esc(h.id) + '"' + (h.primary.disabled ? ' disabled' : '') + '>' + esc(h.primary.label) + '</button>';
    else if (h.upToDate) right = '<span class="ok">' + ICON.check + 'Up to date</span>';
    return '<div class="irow"><div class="info"><span class="hn">' + esc(h.label) + '</span><span class="st"><span class="dot ' + bgClass(h.dotRole) + '"></span>' + esc(h.status) +
      '</span><code>$ ' + esc(h.command) + '</code></div><div class="slots"><div class="slot">' + un + '</div><div class="slot">' + right + '</div></div></div>';
  }).join('') + '</div>';
}

function pageMain(m) {
  const pills = m.pills.map((p) => '<span class="statuspill"><span class="dot ' + bgClass(p.key === 'ok' ? 'ok' : p.key === 'update' ? 'warn' : 'dim') + '"></span>' + esc(p.text) + '</span>').join('');
  const menu = m.split.open ? '<div class="menu" role="menu">' + m.split.menu.map((i) =>
    '<button type="button" role="menuitem" data-act="ask" data-action="' + esc(i.action) + '" data-host="' + esc(i.host) + '"><span>' + esc(i.label) + '</span><span class="h">' + esc(i.hostLabel) + '</span></button>').join('') + '</div>' : '';
  const mainBtn = '<button type="button" class="main" ' + (m.split.action ? 'data-act="ask" data-action="' + esc(m.split.action) + '" data-host="' + esc(m.split.host) + '"' : 'aria-disabled="true"') + '>' + esc(m.split.label) + '</button>';
  const hero = '<section class="hero"><div class="inner">' + tile(m.mark, 76) + '<div class="text"><div class="meta"><span>' + esc(m.marketplace) + '</span><span aria-hidden="true">·</span><span class="mono">v' + esc(m.version) +
    '</span><span aria-hidden="true">·</span><a href="' + esc(m.links.readme) + '">README</a><span aria-hidden="true">·</span><a href="' + esc(m.links.changelog) + '">Changelog</a></div>' +
    '<h1>' + esc(m.name) + '</h1><p class="desc">' + esc(m.description) + '</p><div class="statuspills">' + pills + '</div></div>' +
    '<div class="split"><div class="splitbar">' + mainBtn + '<button type="button" class="arrow" data-act="menu" aria-label="More install options" aria-expanded="' + m.split.open + '">' + ICON.caret + '</button></div>' +
    menu + '<span class="note">' + esc(m.split.note) + '</span></div></div></section>';
  const evalHosts = '<div class="seg" role="group" aria-label="Eval host">' + m.evalHosts.map((h) => '<button type="button" data-act="eval-host" data-id="' + esc(h.id) + '" aria-pressed="' + h.pressed + '">' + esc(h.label) + '</button>').join('') + '</div>';
  const evalRow = '<div class="evalrow"><span class="label">Eval on</span>' + evalHosts + '<span class="grow"></span><button type="button" class="helpbtn" data-act="help" aria-expanded="' + m.help + '">' + ICON.help + 'How scores work</button></div>' +
    (m.help ? '<div class="helpbox">' + esc(m.helpText) + '</div>' : '');
  let stats;
  if (m.eval.has) {
    stats = '<div class="stats"><div class="card stat ring">' + ringHtml(m.eval.pct, m.eval.role) + '<div class="col"><span class="k">EVAL SCORE</span><span class="v">' + esc(m.eval.score) +
      '</span><span class="n ' + (m.eval.low ? 'c-warn' : '') + '">' + esc(m.eval.note) + '</span></div></div>' +
      m.eval.kpis.map((k) => '<div class="card stat"><span class="k">' + esc(k.label) + '</span><span class="v">' + esc(k.value) + '<small>' + esc(k.unit) + '</small></span><span class="n">' + esc(k.note) + '</span></div>').join('') + '</div>';
  } else {
    stats = '<div class="empty"><span class="t">' + esc(m.eval.title) + '</span><span class="s">' + esc(m.eval.body) + '</span></div>';
  }
  const tabs = '<div class="tabs" role="tablist" aria-label="Plugin sections">' + m.tabs.map((t) => '<button type="button" role="tab" data-act="section" data-id="' + esc(t.id) + '" aria-selected="' + t.selected + '">' + esc(t.label) +
    '<span class="n">' + t.count + '</span></button>').join('') + '</div>';
  return '<div class="scroll">' + hero + '<div class="pbody">' + evalRow + stats + '<div class="card sections">' + tabs + sectionHtml(m) + '</div></div></div>';
}

function trayHtml(v) {
  if (!v) return '';
  const icons = { queued: ['○', 'c-dim'], running: ['●', 'c-text pulse'], passed: ['✓', 'c-ok'], failed: ['✗', 'c-bad'], stopped: ['–', 'c-dim'] };
  const items = v.items.map((i) => {
    const ic = icons[i.status] || icons.queued;
    const scored = i.status === 'passed' || i.status === 'failed';
    const role = scored && i.score !== null ? scoreRole(i.score) : 'dim';
    return '<div class="titem"><span class="ic ' + ic[1] + '" aria-hidden="true">' + ic[0] + '</span><span class="nm" title="' + esc(i.name) + '">' + esc(i.name) + '</span><span class="stt c-' + role + '">' + esc(i.state) +
      '</span>' + (i.transcript ? '<button type="button" class="link" data-act="transcript" data-case="' + esc(i.name) + '">Transcript</button>' : '') + '</div>';
  }).join('');
  const ask = v.question ? '<div class="ask" role="group" aria-label="Grading question"><span class="eyebrow c-warn">WAITING FOR YOU</span><span class="q">' + esc(v.question.text) + '</span><div class="btns">' +
    v.question.buttons.map((b, n) => '<button type="button" class="btn sm ' + (n === 0 ? 'primary' : n === 1 ? '' : 'quiet') + '" data-act="answer" data-reply="' + esc(b.reply) + '" data-qid="' + esc(v.question.id) + '">' + esc(b.label) + '</button>').join('') + '</div></div>' : '';
  const log = '<div class="log">' + v.lines.map((l) => '<span class="' + (l.kind === 'ask' ? 'ask-l' : l.kind === 'plain' ? '' : l.kind) + '">' + (esc(l.text) || '&nbsp;') + '</span>').join('') + '</div>';
  const err = v.error ? '<div class="errcard' + (v.error.tone === 'plain' ? ' plain' : '') + '"><span class="t">' + esc(v.error.title) + '</span><span class="b">' + esc(v.error.body) + '</span><span class="actions">' +
    v.error.buttons.map((b) => button(b.label, b.act, {}, b.quiet ? 'btn sm quiet' : 'btn sm')).join('') + '</span></div>' : '';
  return '<div class="tray"><div class="hd"><span class="eyebrow">EVAL RUN</span><span class="t">' + esc(v.title) + '</span><span class="m">' + esc(v.meta) + '</span><span class="grow"></span>' +
    (v.running ? button(v.stopping ? 'Stopping…' : 'Stop', 'stop', {}, 'btn sm') : '') +
    '<button type="button" class="iconbtn" data-act="close-tray" aria-label="Close eval run">' + ICON.close + '</button></div>' +
    '<div class="progress"><span data-w="' + v.pct + '"></span></div><div class="cols"><div class="items">' + items + '</div><div class="out">' + ask + log + '</div></div>' + err + '</div>';
}

function pluginRegions(model, trayView, dialog) {
  return { main: model ? pageMain(model) : '<p class="nomatch">No plugin to show.</p>', tray: trayHtml(trayView), dialog: dialogHtml(dialog) };
}

function pluginBody(model, trayView, dialog) {
  const r = pluginRegions(model, trayView, dialog);
  return '<div class="page"><div id="r-main" class="grow-main">' + r.main + '</div><div id="r-tray">' + r.tray + '</div></div><div id="r-dialog">' + r.dialog + '</div>';
}

// --- the page script and the document ---

const SCRIPT = `
const vscode = acquireVsCodeApi();
const cache = {};
function post(message) { vscode.postMessage(message); }
function sizes(root) {
  root.querySelectorAll('[data-w]').forEach((el) => { el.style.width = Math.max(0, Math.min(100, Number(el.dataset.w) || 0)) + '%'; });
  root.querySelectorAll('[data-h]').forEach((el) => { el.style.height = Math.max(0, Number(el.dataset.h) || 0) + 'px'; });
}
function render(regions) {
  const active = document.activeElement;
  const id = active && active.id;
  const start = active && typeof active.selectionStart === 'number' ? active.selectionStart : null;
  const end = active && typeof active.selectionEnd === 'number' ? active.selectionEnd : null;
  const keep = {};
  document.querySelectorAll('.scroll,.items,.out').forEach((el, n) => { keep[el.className + n] = el.scrollTop; });
  Object.keys(regions).forEach((name) => {
    const el = document.getElementById('r-' + name);
    if (!el || cache[name] === regions[name]) return;
    cache[name] = regions[name];
    el.innerHTML = regions[name];
    sizes(el);
  });
  document.querySelectorAll('.scroll,.items,.out').forEach((el, n) => { if (keep[el.className + n] !== undefined) el.scrollTop = keep[el.className + n]; });
  const out = document.querySelector('.out');
  if (out) out.scrollTop = out.scrollHeight;
  if (id && id !== 'q') {
    const again = document.getElementById(id);
    if (again) { again.focus(); if (start !== null && again.setSelectionRange) again.setSelectionRange(start, end); }
  }
  const dialog = document.getElementById('dlg');
  if (dialog && !dialog.contains(document.activeElement)) { const first = dialog.querySelector('[data-autofocus]'); if (first) first.focus(); }
}
document.addEventListener('click', (event) => {
  const el = event.target.closest('[data-act]');
  if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true') return;
  const message = { type: el.dataset.act };
  Object.keys(el.dataset).forEach((key) => { if (key !== 'act') message[key] = el.dataset[key]; });
  if (message.type === 'confirm') { const box = document.getElementById('dont-ask'); message.dontAsk = !!(box && box.checked); }
  post(message);
});
document.addEventListener('input', (event) => { if (event.target && event.target.id === 'q') post({ type: 'query', q: event.target.value }); });
document.addEventListener('keydown', (event) => {
  const typing = /^(INPUT|TEXTAREA)$/.test((event.target || {}).tagName || '');
  if (event.key === '/' && !typing) { const q = document.getElementById('q'); if (q) { event.preventDefault(); q.focus(); q.select(); } }
  if (event.key === 'Escape') { if (document.getElementById('dlg')) post({ type: 'cancel' }); else if (document.querySelector('.menu')) post({ type: 'menu' }); }
  if (event.key === 'Tab' && document.getElementById('dlg')) {
    const items = Array.from(document.querySelectorAll('#dlg button, #dlg input'));
    const at = items.indexOf(document.activeElement);
    if (event.shiftKey && at <= 0) { event.preventDefault(); items[items.length - 1].focus(); }
    else if (!event.shiftKey && at === items.length - 1) { event.preventDefault(); items[0].focus(); }
  }
});
window.addEventListener('message', (event) => { const m = event.data; if (m && m.type === 'render' && m.regions) render(m.regions); });
sizes(document);
post({ type: 'ready' });
`;

// A whole webview document. `body` is one of sidebarBody / pluginBody; `regions` seeds the page script's cache.
function documentHtml(options) {
  const n = options.nonce;
  return '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + csp(n, options.cspSource).replace(/"/g, '&quot;') + '">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1"><title>' + esc(options.title) + '</title>' +
    '<style nonce="' + esc(n) + '">:root{' + cssVariables(options.theme, options.highContrast) + '}' + STYLE + '</style></head><body>' +
    options.body + '<script nonce="' + esc(n) + '">' + SCRIPT.replace(/<\/script/gi, '<\\/script') + '</script></body></html>';
}

function sidebarDocument(model, dialog, options) {
  return documentHtml(Object.assign({ title: 'Eurus Skills', body: sidebarBody(model, dialog) }, options));
}

function pluginDocument(model, trayView, dialog, options) {
  return documentHtml(Object.assign({ title: model ? model.name : 'Eurus Skills', body: pluginBody(model, trayView, dialog) }, options));
}

module.exports = { esc, nonce, csp, renderCode, dialogHtml, noticeHtml, sidebarRegions, pluginRegions, sidebarDocument, pluginDocument, trayHtml, ICON };
