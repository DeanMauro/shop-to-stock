export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/") return new Response(renderHome(await loadHomeData(env), env), { headers: htmlHeaders() });
    if (url.pathname === "/connect") return new Response(renderConnect(env), { headers: htmlHeaders() });
    if (url.pathname === "/save-token" && request.method === "POST") {
      const receivedAt = new Date().toISOString();
      let body = {};
      try {
        body = await request.json();
      } catch (err) {
        await env.SHOP_TO_STOCK_KV.put("debug:last-connect-attempt", JSON.stringify({ ok: false, stage: "parse", receivedAt, error: String(err) }));
        return json({ ok: false, error: "invalid json body" }, 400);
      }
      const accessToken = body?.accessToken || body?.enrollment?.accessToken || null;
      const enrollment = body?.enrollment || {};
      if (!accessToken) {
        await env.SHOP_TO_STOCK_KV.put("debug:last-connect-attempt", JSON.stringify({ ok: false, stage: "validate", receivedAt, error: "missing accessToken", bodyKeys: Object.keys(body || {}), enrollmentKeys: Object.keys(enrollment || {}) }));
        return json({ ok: false, error: "missing accessToken", details: { bodyKeys: Object.keys(body || {}), enrollmentKeys: Object.keys(enrollment || {}) } }, 400);
      }
      const nonce = crypto.randomUUID();
      const connectedPayload = {
        connected: true,
        institution: enrollment?.institution?.name || enrollment?.enrollment?.institution?.name || null,
        institutionId: enrollment?.institution?.id || enrollment?.enrollment?.institution?.id || null,
        enrollmentId: enrollment?.id || enrollment?.enrollment?.id || null,
        userId: enrollment?.user?.id || null,
        savedAt: receivedAt
      };
      await env.SHOP_TO_STOCK_KV.put(`pending-token:${nonce}`, JSON.stringify({ accessToken, enrollment, savedAt: receivedAt }), { expirationTtl: 3600 });
      await env.SHOP_TO_STOCK_KV.put("status:connected", JSON.stringify(connectedPayload));
      await env.SHOP_TO_STOCK_KV.put("debug:last-connect-attempt", JSON.stringify({ ok: true, stage: "saved", receivedAt, nonce, connectedPayload, hasAccessToken: true, bodyKeys: Object.keys(body || {}), enrollmentKeys: Object.keys(enrollment || {}) }));
      return json({ ok: true, nonce, connected: connectedPayload });
    }
    if (url.pathname === "/debug/status") {
      const auth = request.headers.get("x-shop-to-stock-admin-secret") || url.searchParams.get("secret") || "";
      if (!env.SHOP_TO_STOCK_ADMIN_SECRET || auth !== env.SHOP_TO_STOCK_ADMIN_SECRET) return json({ ok: false, error: "forbidden" }, 403);
      const [connectedRaw, debugRaw, pendingList, summaryList] = await Promise.all([
        env.SHOP_TO_STOCK_KV.get("status:connected"),
        env.SHOP_TO_STOCK_KV.get("debug:last-connect-attempt"),
        env.SHOP_TO_STOCK_KV.list({ prefix: "pending-token:", limit: 10 }),
        env.SHOP_TO_STOCK_KV.list({ prefix: "summary:", limit: 10 })
      ]);
      return json({
        ok: true,
        connected: connectedRaw ? JSON.parse(connectedRaw) : null,
        lastConnectAttempt: debugRaw ? JSON.parse(debugRaw) : null,
        pendingTokens: (pendingList.keys || []).map(k => k.name.replace(/^pending-token:/, "")),
        summaryDates: (summaryList.keys || []).map(k => k.name.replace(/^summary:/, "")).sort().reverse()
      });
    }
    const pending = url.pathname.match(/^\/pending-token\/(.+)$/);
    if (pending) {
      const auth = request.headers.get("x-shop-to-stock-admin-secret") || url.searchParams.get("secret") || "";
      if (!env.SHOP_TO_STOCK_ADMIN_SECRET || auth !== env.SHOP_TO_STOCK_ADMIN_SECRET) return json({ ok: false, error: "forbidden" }, 403);
      const raw = await env.SHOP_TO_STOCK_KV.get(`pending-token:${pending[1]}`);
      if (!raw) return json({ ok: false, error: "not found" }, 404);
      return new Response(raw, { headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
    }
    if (url.pathname === "/dates") return json(await loadHomeData(env));
    if (url.pathname.startsWith('/static/')) {
      if (env.ASSETS && env.ASSETS.fetch) return env.ASSETS.fetch(request);
      return new Response('Not found', { status: 404 });
    }

    const match = url.pathname.match(/^\/d\/(\d{4}-\d{2}-\d{2})$/);
    if (!match) return new Response("Not found", { status: 404 });
    const raw = await env.SHOP_TO_STOCK_KV.get(`summary:${match[1]}`);
    if (!raw) return new Response("Summary not found", { status: 404 });
    return new Response(renderPage(JSON.parse(raw), env), { headers: htmlHeaders() });
  }
};

function htmlHeaders() { return { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300" }; }
function json(obj, status = 200) { return new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } }); }
async function loadHomeData(env) {
  const list = await env.SHOP_TO_STOCK_KV.list({ prefix: "summary:" });
  const dates = (list.keys || []).map(k => k.name.replace(/^summary:/, "")).sort().reverse();
  const connectedRaw = await env.SHOP_TO_STOCK_KV.get("status:connected");
  const connected = connectedRaw ? JSON.parse(connectedRaw) : { connected: false };
  const insightRaw = await env.SHOP_TO_STOCK_KV.get("status:data-insight");
  const dataInsight = insightRaw ? JSON.parse(insightRaw) : null;
  let latestSummary = null;
  if (dates[0]) {
    const raw = await env.SHOP_TO_STOCK_KV.get(`summary:${dates[0]}`);
    latestSummary = raw ? JSON.parse(raw) : null;
  }
  return { dates, connected, latestSummary, dataInsight };
}
function esc(value) { return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;"); }
function money(n) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(n || 0)); }
function compactNumber(n, digits = 6) { if (n === null || n === undefined || Number.isNaN(Number(n))) return "—"; return Number(n).toFixed(digits).replace(/0+$/, '').replace(/\.$/, ''); }
function shell() {
  return `<style>
    :root { --text:#ffffff; --muted:rgba(236,242,252,.82); --line:rgba(255,255,255,.10); --panel:rgba(10,14,22,.58); --panel-strong:rgba(14,18,28,.72); --accent:#9dd6ff; --good:#92e0b3; --bad:#ff8f8f; --warn:#ffd98b; --gray:#c0c7d3; --outer-radius:28px; --panel-pad:22px; --inner-radius:6px; }
    *{box-sizing:border-box} body{margin:0;color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,sans-serif;letter-spacing:-.01em;background:#06070b}
    .bg-image{position:fixed;inset:0;z-index:-3;background:#06070b url('/background.png') center center / cover no-repeat}.bg-scrim{position:fixed;inset:0;z-index:-2;background:rgba(6,10,18,.28)}.bg-frost{display:none}
    .wrap{max-width:1160px;margin:0 auto;padding:28px 18px 48px}.hero,.card{border:1px solid var(--line);background:linear-gradient(180deg,var(--panel-strong),var(--panel));border-radius:var(--outer-radius);backdrop-filter:blur(24px) saturate(135%);box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 16px 50px rgba(0,0,0,.24)} .hero,.card{padding:var(--panel-pad)}
    .top,.stats,.home-grid,.holdings{display:grid;gap:16px}.top{grid-template-columns:1fr;align-items:start}.stats{grid-template-columns:repeat(3,minmax(0,1fr));margin-top:16px}.home-grid{grid-template-columns:1fr 1fr;margin-top:18px}.holdings{margin-top:18px}
    .table{margin-top:18px}.thead,.trow{display:grid;grid-template-columns:1.3fr 1.1fr .8fr .7fr;gap:18px;align-items:center}.thead{padding:0 0 10px;border-bottom:1px solid rgba(255,255,255,.08)}.thead div{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700}
    .trow{padding:14px 8px;border-bottom:1px solid rgba(255,255,255,.06)}.trow:nth-child(odd){background:rgba(255,255,255,.018)}.trow:nth-child(even){background:transparent}.trow:last-child{border-bottom:0}
    .cell-label{display:none}
    .holding{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.06)} .holding:last-child{border-bottom:0}
    .eyebrow{color:var(--accent);text-transform:uppercase;letter-spacing:.18em;font-size:10px;font-weight:700} h1{margin:8px 0 8px;font-size:clamp(28px,3.8vw,42px);line-height:1.0;font-weight:760} h2,h3,p{margin:0} h3{font-size:14px;font-weight:650;line-height:1.25}
    .sub,.mini,li{color:var(--muted)} .sub{font-size:13px;line-height:1.45}.mini{font-size:11px;line-height:1.35}.value,.money,.big{font-size:20px;font-weight:760;letter-spacing:-.03em}.big{font-size:22px}
    .pill{display:inline-flex;align-items:center;gap:7px;padding:6px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.08);font-size:11px;background:rgba(255,255,255,.05)} .pill.good{color:var(--good)} .pill.warn{color:var(--warn)} .pill.bad{color:var(--bad)} .pill.gray{color:var(--gray)}
    .dot{width:7px;height:7px;border-radius:999px;display:inline-block}.dot.good{background:var(--good);box-shadow:0 0 10px rgba(146,224,179,.9)} .dot.warn{background:var(--warn);box-shadow:0 0 10px rgba(255,217,139,.9)} .dot.bad{background:var(--bad);box-shadow:0 0 10px rgba(255,143,143,.9)} .dot.gray{background:var(--gray);box-shadow:0 0 10px rgba(169,176,188,.55)}
    .merchant-title{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.buy-block{display:flex;align-items:center;gap:10px;min-width:0}.logo{width:32px;height:32px;border-radius:10px;background:white;object-fit:contain;padding:4px;flex:0 0 auto;box-shadow:0 3px 14px rgba(0,0,0,.16)}
    .cta,button,select{border:0;border-radius:14px;padding:12px 15px;font:inherit}.cta,button{display:inline-flex;align-items:center;justify-content:center;width:auto;max-width:max-content;background:linear-gradient(180deg,#f7f9fd,#dbe7f7);color:#11151c;text-decoration:none;font-weight:760;box-shadow:0 6px 20px rgba(255,255,255,.08)} button{cursor:pointer} select{background:rgba(255,255,255,.05);color:var(--text);border:1px solid var(--line);width:100%;border-radius:var(--inner-radius)}
    .right{text-align:right}.dense{display:grid;gap:10px}.list{display:grid;gap:12px;margin-top:12px}.kv{display:grid;gap:8px}.kv-row{display:flex;justify-content:space-between;gap:16px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)} .kv-row:last-child{border-bottom:0}
    .section-head{display:grid;gap:8px}.section-sub{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px}.section-sub .mini{font-size:12px}.bank-actions{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}.bank-actions .cta{margin-left:auto}.empty-copy{color:var(--muted);font-size:14px;line-height:1.45}
    .mobile-stats{display:none}
    @media (max-width:900px){.top,.home-grid,.thead,.trow{grid-template-columns:1fr}.thead{display:none}.trow{padding:16px 0;gap:12px}.right{text-align:left}.bank-actions{align-items:flex-start}.bank-actions .cta{margin-left:0}.stats{display:none}.mobile-stats{display:grid;gap:10px;margin-top:16px;padding:14px 16px;border:1px solid rgba(255,255,255,.08);border-radius:18px;background:rgba(255,255,255,.025)}.mobile-stats-row{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center}.mobile-stats-row + .mobile-stats-row{padding-top:10px;border-top:1px solid rgba(255,255,255,.06)}.mobile-stats .eyebrow{font-size:9px}.mobile-stats .value{font-size:18px}.trow > div{display:grid;gap:8px}.cell-label{display:block;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:2px}.buy-block{align-items:flex-start}.logo{width:28px;height:28px;border-radius:8px}.table{margin-top:14px}}
  </style>`;
}
function pageBg() { return `<div class="bg-image"></div><div class="bg-scrim"></div><div class="bg-frost"></div>`; }
function renderLogo(symbol, env) { return env.LOGO_DEV_TOKEN && symbol ? `<img class="logo" src="https://img.logo.dev/ticker/${encodeURIComponent(symbol)}?token=${encodeURIComponent(env.LOGO_DEV_TOKEN)}" alt="${esc(symbol)} logo" />` : ''; }
function renderStatus(status) {
  const s = String(status || 'unknown').toLowerCase();
  const kind = s.includes('filled') ? 'good' : s.includes('placed') ? 'good' : s.includes('approval') ? 'warn' : s.includes('failed') ? 'bad' : s.includes('eligible') || s.includes('no buy') ? 'gray' : 'gray';
  const label = s === 'not eligible' ? 'No buy' : status || 'Unknown';
  return `<span class="pill ${kind}"><span class="dot ${kind}"></span>${esc(label)}</span>`;
}

function renderHome(data, env) {
  const options = (data.dates || []).map(d => `<option value="/d/${esc(d)}">${esc(d)}</option>`).join('');
  const connected = data.connected?.connected;
  const institution = data.connected?.institution;
  const savedAt = data.connected?.savedAt;
  const dataInsight = data.dataInsight || {};
  const latestTxDate = dataInsight.latestTransactionDate;
  const accountCount = dataInsight.accountCount;
  const accountSummary = Array.isArray(dataInsight.accounts) ? dataInsight.accounts.map(a => `${a.institution || 'Bank'} ${a.type || 'account'} ••••${a.last_four || '—'}`).join(' · ') : '';
  const portfolio = data.latestSummary?.portfolio || { positions: [], buyingPower: null };
  const publicAccount = data.latestSummary?.portfolio?.accountNumber || env.PUBLIC_COM_ACCOUNT_ID || '—';
  const holdings = (portfolio.positions || []).map(pos => `<div class="holding"><div class="buy-block">${renderLogo(pos.symbol, env)}<div><div><strong>${esc(pos.symbol)}</strong> · ${esc(pos.name || '')}</div><div class="mini">${compactNumber(pos.quantity, 4)} shares · ${money(pos.lastPrice)} · ${pos.percentOfPortfolio ? pos.percentOfPortfolio.toFixed(2) + '% of portfolio' : ''}</div></div></div><div class="right"><div><strong>${money(pos.currentValue)}</strong></div></div></div>`).join('') || `<div class="empty-copy">You haven’t bought any stocks yet!</div>`;
  return `<!doctype html><html><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>Shop-to-Stock</title>${shell()}</head><body>${pageBg()}<div class="wrap"><section class="hero"><div class="top"><div><div class="eyebrow">Shop to Stock</div><h1>Turn spending into ownership.</h1><p class="sub">Connect a bank through Teller, review what’s linked, browse daily summaries, and keep an eye on what you already hold at Public.</p></div></div><div class="home-grid"><section class="card"><div class="eyebrow">Bank connection</div><div class="bank-actions"><span class="pill ${connected ? 'good' : 'warn'}"><span class="dot ${connected ? 'good' : 'warn'}"></span>${connected ? 'Bank connected' : 'No bank connected'}</span><a class="cta" href="/connect">${connected ? 'Reconnect bank' : 'Connect bank'}</a></div><div class="list kv"><div class="kv-row"><strong>Status</strong><span class="mini">${connected ? 'Connected through Teller' : 'Not connected yet'}</span></div><div class="kv-row"><strong>Institution</strong><span class="mini">${esc(institution || '—')}</span></div><div class="kv-row"><strong>Last linked</strong><span class="mini">${esc(savedAt || '—')}</span></div><div class="kv-row"><strong>Accounts linked</strong><span class="mini">${esc(accountCount ?? '—')}</span></div><div class="kv-row"><strong>Latest transaction</strong><span class="mini">${esc(latestTxDate || 'No posted transactions found yet')}</span></div></div>${accountSummary ? `<p class="mini" style="margin-top:10px">${esc(accountSummary)}</p>` : ''}</section><section class="card"><div class="eyebrow">Investment Diary</div><p class="sub">Pick a date to see your purchases and corresponding investments for that day.</p><div class="list"><select id="dateSelect"><option value="">Choose a date…</option>${options}</select><button id="goBtn">Open Diary</button></div></section></div><section class="card" style="margin-top:18px"><div class="section-head"><div class="eyebrow">Holdings</div><div class="section-sub"><p class="sub">Public ${esc(publicAccount)} • Buying Power: ${portfolio.buyingPower !== null ? money(portfolio.buyingPower) : '—'}</p></div></div><div class="holdings">${holdings}</div></section></section></div><script>document.getElementById('goBtn').addEventListener('click',function(){const v=document.getElementById('dateSelect').value;if(v)location.href=v;});document.getElementById('dateSelect').addEventListener('change',function(){if(this.value)location.href=this.value;});</script></body></html>`;
}

function renderConnect(env) {
  const applicationId = esc(env.TELLER_APPLICATION_ID || '');
  return `<!doctype html><html><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>Connect your bank</title>${shell()}<script src="https://cdn.teller.io/connect/connect.js"></script></head><body>${pageBg()}<div class="wrap"><section class="hero"><div class="eyebrow">Teller Connect</div><h1>Connect your bank</h1><p class="sub">Finish the Teller flow. If save succeeds, this page will show a retrieval nonce and the homepage should update immediately.</p><div class="home-grid"><section class="card"><div class="eyebrow">Application</div><p><code>${applicationId || 'missing'}</code></p></section><section class="card"><div class="eyebrow">Action</div><button class="cta" id="launch">Launch Teller Connect</button><p id="status" class="sub" style="margin-top:12px"></p></section></div></section></div><script>const statusEl=document.getElementById('status');const appId=${JSON.stringify(env.TELLER_APPLICATION_ID || '')};document.getElementById('launch').addEventListener('click',function(){if(!appId){statusEl.textContent='Missing Teller application ID in worker config.';return;}statusEl.textContent='Launching Teller Connect...';const nonce=crypto.randomUUID();const teller=TellerConnect.setup({applicationId:appId,environment:'development',products:['transactions','balance','identity'],selectAccount:'multiple',nonce,onSuccess:async function(enrollment){statusEl.textContent='Enrollment succeeded. Saving token...';try{const payload={accessToken:enrollment?.accessToken||null,enrollment};const res=await fetch('/save-token',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});const text=await res.text();let data={};try{data=JSON.parse(text);}catch(_){data={ok:false,error:'non-json response',raw:text};}if(data.ok){statusEl.innerHTML='Connected. Retrieval nonce: <code>'+data.nonce+'</code><br><span class="mini">You can now go back home and refresh if needed.</span>';}else{statusEl.textContent='Token save failed: '+(data.error||'unknown error')+(data.details?' '+JSON.stringify(data.details):'');}}catch(err){statusEl.textContent='Token save failed: '+err;}},onExit:function(){if(!statusEl.textContent||statusEl.textContent==='Launching Teller Connect...')statusEl.textContent='Connect closed before completion.';}});teller.open();});</script></body></html>`;
}

function renderRow(entry, env) {
  const buy = entry.buy;
  const isFallback = !!entry.isFallback;
  const transactionCell = isFallback
    ? `<div><div class="cell-label">Transaction</div><div class="merchant-title"><h3>S&amp;P 500</h3></div><div class="mini">Automatic fallback investment for today.</div></div>`
    : `<div><div class="cell-label">Transaction</div><div class="merchant-title"><h3>${esc(entry.merchantName)}</h3></div><div class="mini">${esc(entry.date)} · transaction ${esc(entry.transactionId || 'unknown')}</div><div class="mini">${money(entry.totalSpent)}</div></div>`;
  const stockCell = buy && entry.public
      ? `<div><div class="cell-label">Stock match</div><div class="buy-block">${renderLogo(buy.ticker, env)}<div><div><strong>${esc(buy.ticker)}</strong> · ${esc(buy.parentCompany)}</div><div class="mini">${buy.currentPrice ? money(buy.currentPrice) : '—'}</div></div></div></div>`
      : `<div><div class="cell-label">Stock match</div><div class="mini">No stock purchase</div></div>`;
  const quantityCell = buy
    ? `<div><div class="cell-label">Quantity</div><div><strong>${money(buy.orderDollars || 1)}</strong> ≈ ${compactNumber(buy.estimatedShares)} shares</div></div>`
    : `<div><div class="cell-label">Quantity</div><div class="mini">—</div></div>`;
  const statusCell = `<div><div class="cell-label">Status</div>${renderStatus(entry.orderStatus || (buy ? buy.orderStatus : 'not eligible'))}</div>`;
  return `<div class="trow"><div>${transactionCell}</div><div>${stockCell}</div><div>${quantityCell}</div><div>${statusCell}</div></div>`;
}

function renderPage(data, env) {
  const rows = (data.entries || []).map(entry => renderRow(entry, env)).join('');
  return `<!doctype html><html><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>Shop-to-Stock for ${esc(data.date)}</title>${shell()}</head><body>${pageBg()}<div class="wrap"><section class="hero"><div class="top"><div><div class="eyebrow">Shop to Stock</div><h1>${esc(data.displayDate || data.date)}</h1><p class="sub">${esc(data.topExplanation || 'Below are your purchases for the past day. Any publicly traded companies you bought from have been identified so we can invest in them. If there were no purchases or none of the vendors you shopped at are public, we’ll toss today’s investment into the trusty S&P 500.')}</p></div><div class="dense right"><a class="cta" href="/">Browse dates</a></div></div><div class="stats"><div class="card"><div class="eyebrow">Merchant spend</div><div class="value">${money(data.totals?.merchantSpend)}</div></div><div class="card"><div class="eyebrow">Planned invest</div><div class="value">${money(data.totals?.plannedInvest)}</div></div><div class="card"><div class="eyebrow">Executed invest</div><div class="value">${money(data.totals?.executedInvest)}</div></div></div><div class="mobile-stats"><div class="mobile-stats-row"><div><div class="eyebrow">Merchant spend</div></div><div class="value">${money(data.totals?.merchantSpend)}</div></div><div class="mobile-stats-row"><div><div class="eyebrow">Planned invest</div></div><div class="value">${money(data.totals?.plannedInvest)}</div></div><div class="mobile-stats-row"><div><div class="eyebrow">Executed invest</div></div><div class="value">${money(data.totals?.executedInvest)}</div></div></div><div class="table"><div class="thead"><div>Transaction</div><div>Stock Match</div><div>Quantity</div><div>Status</div></div>${rows || '<div class="mini" style="padding:16px 0">No entries available.</div>'}</div></section></div></body></html>`;
}
