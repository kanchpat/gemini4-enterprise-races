/* Gemini for Real-Life Enterprise Use Cases — single-page app.
 * DATA (results/summary.json) is injected by scripts/build_site.py. */
const DATA = /*DATA*/null;

const REPO = 'https://github.com/kanchpat/gemini4-enterprise-races';
const BLOB = REPO + '/blob/main/';
const BLOG = 'https://blog.google/innovation-and-ai/models-and-research/gemini-models/';

// Display order and colors per setup.
const SETUPS = [
  {model: 'gemini-4-hydrogen', thinking: 'LOW', short: 'Hydrogen · low', color: '#2F7D5B'},
  {model: 'gemini-4-hydrogen', thinking: 'HIGH', short: 'Hydrogen · high', color: '#1E5C43'},
  {model: 'gemini-3.8-flash', thinking: 'HIGH', short: '3.8 Flash', color: '#D9822B'},
  {model: 'gemini-4-neon', thinking: 'HIGH', short: 'Neon · high', color: '#4A235A'},
];

const USE_CASES = [
  {
    id: 'analyst', tag: 'green', name: 'Financial reporting analysis',
    task: 'Read a full quarterly filing (about 38,000 words) and answer 25 questions: reported figures, derived KPIs (margins, growth, mix) and a trap question whose answer is not in the document.',
    owner: 'Office of the CFO, FP&A, credit and equity research',
    elsewhere: 'Supplier financial health checks, competitor tracking, loan covenant monitoring',
    data: 'Alphabet Form 10-Q, Q3 2026, graded against the SEC XBRL facts',
    verdict: '<b>Solved task: pick on speed and cost.</b> Every setup scored 100% on every run. Hydrogen at low thinking was fastest; 3.8 Flash was cheapest at its promotional price.',
  },
  {
    id: 'intake', tag: 'blue', name: 'Meeting and call intelligence',
    task: 'Watch a 34-minute earnings-call video (no transcript provided) and answer 20 questions on figures, guidance and who said what.',
    owner: 'Investor relations, strategy, sales leadership',
    elsewhere: 'Board meetings, customer QBRs, contact-center QA, all-hands',
    data: 'Alphabet Q3 2026 earnings call (YouTube), keyed to timestamps',
    verdict: '<b>The previous generation wins here, and we say so.</b> All setups scored 100%. 3.8 Flash was fastest and cheapest, so it stays a good choice for high-volume call intake.',
  },
  {
    id: 'audit', tag: 'coral', name: 'Review and controls',
    task: 'Review the same filing with 6 planted errors (a wrong segment figure, a broken total, a part larger than its whole and more). Report each error with proof. False flags count against you.',
    owner: 'Controllership, internal audit, compliance',
    elsewhere: 'Regulatory filings, contracts and invoices, insurance claims, RFP responses',
    data: '10-Q text with 6 author-planted errors; list published in the repo',
    verdict: '<b>This is where Gemini 4 earns its keep.</b> Hydrogen (high thinking) and Neon caught all 6 errors on all 5 runs with zero false flags. 3.8 Flash caught 77% and missed the part-larger-than-whole error every time.',
  },
];

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const usd = (v, d = 2) => '$' + v.toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});

function cfg(test, s) {
  const t = DATA.tests[test];
  return t && t.configs.find(c => c.model === s.model && c.thinking === s.thinking);
}

function accLabel(test, c) {
  if (test === 'part2') return `${c.fully_verified}/${c.answers_total} verified`;
  return test === 'audit' ? `${c.errors_found}/${c.errors_planted} errors` : `${Math.round(c.accuracy_median_pct)}%`;
}

function accFrac(test, c) {
  if (test === 'part2') return c.fully_verified / c.answers_total;
  return test === 'audit' ? c.errors_found / c.errors_planted : c.accuracy_median_pct / 100;
}

function bars(test) {
  const rows = SETUPS.map(s => ({s, c: cfg(test, s)})).filter(r => r.c);
  const maxT = Math.max(...rows.map(r => r.c.seconds_median));
  const maxC = Math.max(...rows.map(r => r.c.cost_usd_median));
  const bestT = Math.min(...rows.map(r => r.c.seconds_median));
  const bestC = Math.min(...rows.map(r => r.c.cost_usd_median));
  const bestA = Math.max(...rows.map(r => accFrac(test, r.c)));
  const bar = (frac, label, color, best) =>
    `<div class="bar${best ? ' best' : ''}"><i style="width:${Math.max(frac * 100, 3)}%;background:${color}33"></i><span>${label}</span></div>`;
  return `<div class="rows">
    <div class="row head"><div>Setup (median of ${rows[0].c.runs} runs)</div><div>Accuracy</div><div>Time per task</div><div>Cost per task</div></div>
    ${rows.map(({s, c}) => `<div class="row">
      <div class="who"><span class="sw" style="background:${s.color}"></span>${s.short}</div>
      ${bar(accFrac(test, c), accLabel(test, c), s.color, accFrac(test, c) === bestA)}
      ${bar(c.seconds_median / maxT, Math.round(c.seconds_median) + ' s', s.color, c.seconds_median === bestT)}
      ${bar(c.cost_usd_median / maxC, usd(c.cost_usd_median, 3), s.color, c.cost_usd_median === bestC)}
    </div>`).join('')}
  </div>`;
}

function useCase(u, i) {
  return `<article class="card uc" id="uc-${u.id}">
    <div class="uc-h">
      <div>
        <span class="tag ${u.tag}">Enterprise use case ${i + 1}</span>
        <h3>${u.name}</h3>
        <p><b>The test:</b> ${u.task}</p>
      </div>
      <dl class="meta">
        <dt>Who owns it</dt><dd>${u.owner}</dd>
        <dt>Where else this applies</dt><dd>${u.elsewhere}</dd>
        <dt>Stand-in data</dt><dd>${u.data}</dd>
      </dl>
    </div>
    <div class="uc-b">${bars(u.id)}<p class="verdict">${u.verdict}</p></div>
  </article>`;
}

function scaleCalc() {
  return `<div class="card">
    <div class="ctrl"><label for="vol">Documents per month</label>
      <input id="vol" type="range" min="1000" max="100000" step="1000" value="10000">
      <output id="volv">10,000</output></div>
    <div id="scale"></div>
    <p class="lede" style="margin:12px 0 0;font-size:13px">Median list-price cost per task from our runs × volume. Excludes caching, batch discounts and retries. 3.8 Flash uses its promotional price, which ends 2026-12-31.</p>
  </div>`;
}

function renderScale() {
  const v = +$('#vol').value;
  $('#volv').textContent = v.toLocaleString('en-US');
  const line = (job, test, pick) => {
    const cells = SETUPS.map(s => {
      const c = cfg(test, s);
      return `<td class="num">${usd(c.cost_usd_median * v, 0)}</td>`;
    }).join('');
    return `<tr><td><b>${job}</b><br><small>Recommended: ${pick}</small></td>${cells}</tr>`;
  };
  $('#scale').innerHTML = `<table><thead><tr><th>Workflow</th>${SETUPS.map(s => `<th>${s.short}</th>`).join('')}</tr></thead><tbody>
    ${line('Financial reporting analysis', 'analyst', 'Hydrogen · low')}
    ${line('Meeting and call intelligence', 'intake', '3.8 Flash or Hydrogen · low')}
    ${line('Review and controls', 'audit', 'Hydrogen · high')}
  </tbody></table>`;
}

function part1() {
  return `
  <div class="hero">
    <div class="eyebrow">Gemini for Real-Life Enterprise Use Cases · Part 1</div>
    <h1>Right model, <em>right job</em></h1>
    <p>Enterprises don't run benchmarks. They run workflows. We tested Gemini 4 Hydrogen, Gemini 4 Neon and Gemini 3.8 Flash on three of them, graded every answer by script, and measured time and cost per task.</p>
    <div class="pills">
      <a class="pill" href="#/part1/analyst">Financial reporting analysis</a>
      <a class="pill" href="#/part1/intake">Meeting and call intelligence</a>
      <a class="pill" href="#/part1/audit">Review and controls</a>
      <a class="pill on" href="#/part1/route">Routing guide</a>
    </div>
  </div>

  <section>
    <div class="video-wrap"><iframe src="https://www.youtube-nocookie.com/embed/rWk_GcL1MH4" title="Gemini for Real-Life Enterprise Use Cases, Part 1: Right Model, Right Job" loading="lazy" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>
    <p class="video-cap">Watch Part 1 (4.5 min): the paradigm shift, the Neon model card, three use cases and the verification rerun. <a href="https://youtu.be/rWk_GcL1MH4" target="_blank" rel="noopener">Open on YouTube</a></p>
  </section>

  <section>
    <div class="grid g3">
      <div class="card take"><span class="n">1</span><div><h3>Extraction is solved</h3><p>All four setups scored 100% on filing analysis and call intake. Choose on speed and cost, not intelligence.</p></div></div>
      <div class="card take"><span class="n">2</span><div><h3>Review needs Gemini 4</h3><p>On a planted-error audit, Hydrogen (high) and Neon caught 30 of 30 errors. 3.8 Flash caught 23 of 30.</p></div></div>
      <div class="card take"><span class="n">3</span><div><h3>Hydrogen is the default worker</h3><p>It matched Neon on document work at about a third of the cost. Save Neon for agent and coding work.</p></div></div>
    </div>
  </section>

  <section style="margin-top:-6px">
    <div class="card" style="display:flex;gap:18px;align-items:center;border-left:5px solid var(--success)">
      <span class="tag green">Verified</span>
      <p style="margin:0;font-size:14px"><b>Rerun by the author, on camera.</b> A fresh run of all three tests (2026-11-20, 22:12 UTC) matched every published accuracy result, including the same missed audit error. Every call's API receipt is saved. <a href="${REPO}/tree/main/results/verification">See the receipts →</a></p>
    </div>
  </section>

  <section>
    <div class="eyebrow">Three enterprise workflows</div>
    <h2>What we tested, and what won</h2>
    <p class="lede">Alphabet's public Q3 2026 filings stand in for your documents, so anyone can check the answers. Bars outlined in coral are the best in each column.</p>
    <div class="grid">${USE_CASES.map(useCase).join('')}</div>
  </section>

  <section id="route">
    <div class="eyebrow">Routing guide</div>
    <h2>Which model for which job</h2>
    <p class="lede">A starting point for an architecture review. Validate on your own documents with the <a href="#/run">bring-your-own-docs steps</a>.</p>
    <div class="grid g3">
      <div class="card route"><span class="tag green">High volume</span><h3>Gemini 4 Hydrogen · low</h3>
        <p>Default for document workflows where answers are in the text.</p>
        <ul><li>Financial reporting analysis</li><li>Extraction into systems of record</li><li>First-pass triage</li></ul></div>
      <div class="card route r2"><span class="tag amber">Accuracy-critical</span><h3>Gemini 4 Hydrogen · high</h3>
        <p>Turn thinking up when a miss is expensive. Same model, one setting.</p>
        <ul><li>Review and controls</li><li>Pre-publication checks</li><li>Verifier subagent behind a faster worker</li></ul></div>
      <div class="card route r3"><span class="tag plum">Long-running agents</span><h3>Gemini 4 Neon</h3>
        <p>Google reports Neon at #1 on the Artificial Analysis Coding Agent Index and Zapier AutomationBench, and 90.5% on SEC-bench Pro (<a href="${BLOG}introducing-gemini-4-neon/">source</a>).</p>
        <ul><li>Multi-step agents and orchestration</li><li>Code modernization</li><li>Multi-source research (Part 2)</li></ul></div>
    </div>
    <p class="callout" style="margin-top:16px"><b>Not tested:</b> Gemini 4 Carbon, which is limited to the Fairwind program for now, and Neon at extra-high thinking, which used its whole output budget on our audit. <a href="${BLOB}docs/approach.md">Why</a>.</p>
  </section>

  <section id="scale-s">
    <div class="eyebrow">Enterprise scale</div>
    <h2>What it costs at volume</h2>
    ${scaleCalc()}
  </section>`;
}

const SRC = {
  '10q': {label: '10-Q · Q3', cls: 'blue'},
  '10q_prior': {label: '10-Q · Q2', cls: 'blue'},
  release: {label: 'Release', cls: 'amber'},
  call: {label: 'Call', cls: 'plum'},
};

function node(x, y, w, h, title, sub, cls = '') {
  return `<g class="n ${cls}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14"/>
    <text class="t" x="${x + w / 2}" y="${y + h / 2 - (sub ? 6 : -5)}">${title}</text>
    ${sub ? `<text class="s" x="${x + w / 2}" y="${y + h / 2 + 15}">${sub}</text>` : ''}</g>`;
}

function flowDiagram() {
  const srcs = [
    ['10-Q · Q3 2026', 'filing · text', ''],
    ['10-Q · Q2 2026', 'prior quarter · text', ''],
    ['Earnings release', '2 planted conflicts', 'hot'],
    ['Earnings call', '34-min video · no transcript', 'vid'],
  ];
  const ys = [24, 112, 200, 288];
  const feeds = ys.map(y => `M212 ${y + 31} C256 ${y + 31} 256 200 300 200`);
  return `<div class="card flow"><svg viewBox="0 0 1200 380" role="img" aria-label="Four sources feed one Gemini call; a verifier script checks every citation; verified answers go to the system of record and conflicts go to an analyst">
    ${feeds.map((d, i) => `<path class="ant" d="${d}"/><circle class="pkt" r="4.5"><animateMotion dur="2.2s" begin="${i * 0.4}s" repeatCount="indefinite" path="${d}"/></circle>`).join('')}
    <path class="ant" d="M512 200 L578 200"/><path class="ant" d="M772 200 L838 200"/>
    <path class="ant ok" d="M1032 186 C1052 186 1050 120 1070 120"/>
    <path class="ant bad" d="M1032 214 C1052 214 1050 280 1070 280"/>
    <circle class="pkt" r="4.5"><animateMotion dur="1.4s" repeatCount="indefinite" path="M512 200 L838 200"/></circle>
    ${srcs.map(([t, sub, c], i) => node(20, ys[i], 192, 62, t, sub, c)).join('')}
    ${node(300, 130, 212, 140, 'One Gemini call', '~280K tokens + video', 'core')}
    <text class="s" x="406" y="250">14 questions, one pass</text>
    ${node(578, 152, 194, 96, 'Answer + citations', 'quote or timestamp per source')}
    ${node(838, 152, 194, 96, 'Verifier script', 'verbatim? ±30 s? agree?', 'ver')}
    ${node(1070, 82, 122, 76, 'Verified', 'system of record', 'good')}
    ${node(1070, 242, 122, 76, 'Conflict', 'analyst review', 'warn')}
  </svg>
  <div class="grid g3 gets">
    <div><b>No chunking, no vector store.</b> At this size, all four sources fit in one call.</div>
    <div><b>Every claim is checked by code</b> before anyone uses it. No model grades another.</div>
    <div><b>Disagreements go to a person,</b> not into the board memo.</div>
  </div></div>`;
}

let xQ = 1, xS = 'gemini-4-neon|HIGH';
const fmtVal = v => v === null || v === undefined ? 'not stated'
  : (typeof v === 'number' ? v.toLocaleString('en-US', {maximumFractionDigits: 3}) : esc(v));
const mmss = t => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, '0')}`;

function explorer() {
  const X = DATA.explorer;
  if (!X) return '';
  return `<div class="card xp">
    <div class="xq">${X.questions.map((q, i) => `<button class="qb" data-q="${i}"><b>${q.id.toUpperCase()}</b><span>${esc(q.kind)}</span></button>`).join('')}</div>
    <div id="xd"></div></div>`;
}

function renderX() {
  const X = DATA.explorer, q = X.questions[xQ];
  document.querySelectorAll('.qb').forEach(b => b.classList.toggle('on', +b.dataset.q === xQ));
  const why = (q.planted && `<b>Planted:</b> ${esc(q.planted.note)}`) || (q.lookalike && `<b>Look-alike:</b> ${esc(q.lookalike)}`) || (q.note && esc(q.note)) || '';
  const rows = SETUPS.map(s => {
    const k = `${s.model}|${s.thinking}`, d = q.setups[k];
    if (!d) return '';
    const n = d.runs.filter(Boolean).length;
    return `<button class="xs${k === xS ? ' on' : ''}" data-s="${k}">
      <span class="who"><span class="sw" style="background:${s.color}"></span>${s.short}</span>
      <span class="dots">${d.runs.map(ok => `<i class="${ok ? 'ok' : 'no'}"></i>`).join('')}</span>
      <span class="num">${n}/5</span><span class="val">${fmtVal(d.values[0])}</span></button>`;
  }).join('');
  const d = q.setups[xS];
  const cites = d.cites.length ? d.cites.map(c => {
    const src = SRC[c.source] || {label: c.source, cls: ''};
    const body = c.source === 'call'
      ? `<a href="${X.video}&t=${Math.round(c.timestamp_s || 0)}s" target="_blank" rel="noopener">▶ ${mmss(c.timestamp_s || 0)}</a> “${esc(c.quote || '')}”`
      : `“${esc(c.quote)}”`;
    return `<li class="${c.ok ? 'ok' : 'no'}"><span class="tag ${src.cls}">${src.label}</span><span class="q">${body}</span>
      <em>${c.ok ? '✓ verified' : '✗ ' + esc(c.why)}</em></li>`;
  }).join('') : '<li class="ok"><span class="q">No citations: the correct answer is “not stated”.</span></li>';
  $('#xd').innerHTML = `
    <h3>${esc(q.q)}</h3>
    <p class="xa">Correct answer: <b>${fmtVal(q.answer)}</b>${why ? ' · ' + why : ''}</p>
    <div class="xrows"><div class="xs head"><span>Setup</span><span>5 runs</span><span>Verified</span><span>Answer (run 1)</span></div>${rows}</div>
    <p class="eyebrow" style="margin:18px 0 8px">Citations · ${esc((SETUPS.find(s => `${s.model}|${s.thinking}` === xS) || {}).short || '')} · run 1</p>
    <ul class="cites">${cites}</ul>`;
  document.querySelectorAll('.xs[data-s]').forEach(b => b.onclick = () => { xS = b.dataset.s; renderX(); });
}

function part2() {
  const c = s => cfg('part2', s);
  const neon = c(SETUPS[3]), hh = c(SETUPS[1]);
  const perQ = x => usd(x.cost_usd_median / x.questions, 3);
  return `
  <div class="hero">
    <div class="eyebrow">Gemini for Real-Life Enterprise Use Cases · Part 2</div>
    <h1>Ask once, <em>verify everywhere</em></h1>
    <p>Due diligence means reconciling filings, press releases and calls. We asked each model 14 questions across all four at once, and a script checked every quote and timestamp it cited.</p>
    <div class="pills">
      <a class="pill" href="#/part2/flow">The architecture</a>
      <a class="pill" href="#/part2/results">Results</a>
      <a class="pill on" href="#/part2/explorer">Check every answer</a>
      <a class="pill" href="#/part2/route">Route by risk</a>
    </div>
  </div>

  <section>
    <div class="grid g3">
      <div class="card take"><span class="n">1</span><div><h3>Neon never slipped</h3><p><b>${neon.fully_verified}/${neon.answers_total}</b> answers fully verified, including the one conflict only the call could expose.</p></div></div>
      <div class="card take"><span class="n">2</span><div><h3>Hydrogen (high) is the value pick</h3><p><b>${hh.fully_verified}/${hh.answers_total}</b> at about half Neon's cost: ${perQ(hh)} vs ${perQ(neon)} per question.</p></div></div>
      <div class="card take"><span class="n">3</span><div><h3>Trust comes from the verifier</h3><p>No made-up quotes from Gemini 4 and zero false conflict alarms. Every citation was checked by code.</p></div></div>
    </div>
  </section>

  <section id="flow">
    <div class="eyebrow">Enterprise use case · research and due diligence</div>
    <h2>The pattern you can deploy</h2>
    <p class="lede">Corporate development, risk, legal and IR teams reconcile sources by hand. One stale figure can reach a board memo. This is the pattern we tested.</p>
    ${flowDiagram()}
  </section>

  <section id="results">
    <div class="eyebrow">Results · 5 runs per setup</div>
    <h2>Who verified every answer</h2>
    <p class="lede">An answer is <b>fully verified</b> only if the value is right, every quote appears word for word in its source, every call timestamp is within 30 seconds, and conflicts are flagged correctly.</p>
    <div class="card">${bars('part2')}
      <p class="verdict"><b>The decider: a figure the filings don't contain.</b> We changed trailing-twelve-month free cash flow in the release to 17,947 (it is 19,747). Neither 10-Q reports free cash flow, so only the call exposes it. Neon caught it 5 of 5 times, Hydrogen (high) 4 of 5, 3.8 Flash 2 of 5, Hydrogen (low) 0 of 5.</p>
    </div>
  </section>

  <section id="explorer">
    <div class="eyebrow">Explorer</div>
    <h2>Check every answer yourself</h2>
    <p class="lede">Pick a question, then a setup, to see the quotes and timestamps it cited and what the verifier found. Call timestamps open the video at that moment.</p>
    ${explorer()}
  </section>

  <section id="route">
    <div class="eyebrow">Routing guide</div>
    <h2>Route by the cost of an unchecked number</h2>
    <div class="grid g3">
      <div class="card route r3"><span class="tag plum">Decision-grade</span><h3>Gemini 4 Neon · high</h3><p>The answer goes straight into a decision.</p>
        <ul><li>Diligence and board memos</li><li>Regulator responses</li><li>Orchestrator over Hydrogen workers</li></ul></div>
      <div class="card route r2"><span class="tag amber">Reviewed output</span><h3>Gemini 4 Hydrogen · high</h3><p>A person signs off anyway. Near-Neon accuracy at half the cost.</p>
        <ul><li>Analyst briefings</li><li>Vendor and credit reviews</li><li>Research drafts</li></ul></div>
      <div class="card route"><span class="tag green">First pass</span><h3>Gemini 4 Hydrogen · low</h3><p>Fast and cheap, but it trusted the release when only the call disagreed.</p>
        <ul><li>Triage and summaries</li><li>Single-source extraction</li><li>Not for conflict detection</li></ul></div>
    </div>
    <p class="callout" style="margin-top:16px"><b>Read with care:</b> 5 runs per setup, and the gap rests mostly on one question. Conflicts were planted by the author. 3.8 Flash ran out of output budget at 32K on 3 of 5 runs, so its runs used 64K. One grading change after the pilot accepts a filing's own rounded wording (e.g. “$125.1 billion” for 125,102). An easier first version, where every setup scored 12/12, is published too. <a href="${BLOB}docs/approach.md#part-2-ask-once-verify-everywhere">Full method →</a></p>
  </section>`;
}

function method() {
  const rows = [
    ['Grading', 'By script against answer keys built from SEC XBRL facts and call timestamps. No human or model judging.'],
    ['Repeats', '5 runs per setup; we report the median and publish every run.'],
    ['Settings', 'Same prompt, temperature and output cap for every model. Only the thinking level changes.'],
    ['Cost', 'Token counts from the API × public list prices. 3.8 Flash at its promotional price.'],
    ['Time', 'Wall-clock seconds per task on the Vertex AI global endpoint, all setups running in parallel.'],
    ['Traps', 'Questions whose answer is not in the source. The right answer is "not stated".'],
    ['Citations (Part 2)', 'Quotes must appear word for word in the cited source. Call timestamps must fall within 30 s of where the figure is spoken (reference transcripts from three models agree within 10 s).'],
    ['Honesty', 'Ties and losses are published, including Part 2\'s easier first version. One grading change per part, made after each pilot, is disclosed.'],
  ];
  return `
  <section style="margin-top:0">
    <div class="eyebrow">Method</div>
    <h2>How we tested, and why</h2>
    <p class="lede">Published benchmarks rank models on intelligence. Architects ask a narrower question: <b>for a given job, which model gives the right answer at a speed and cost I can run thousands of times a day?</b></p>
    <div class="card"><table><tbody>${rows.map(r => `<tr><th style="width:160px">${r[0]}</th><td>${r[1]}</td></tr>`).join('')}</tbody></table></div>
  </section>
  <section>
    <h2>Limitations</h2>
    <div class="grid g2">
      <div class="card"><ul style="margin:0;padding-left:18px">
        <li>One company's filings; your documents may be harder or easier.</li>
        <li>Planted errors were written by the author. Real errors may be subtler.</li>
        <li>Latency varies by region, time and load. Compare within a run.</li></ul></div>
      <div class="card"><ul style="margin:0;padding-left:18px">
        <li>The filing and call are public, so a model may have seen them. Trap questions check for outside knowledge.</li>
        <li>Results apply to these tasks, dates and prices only.</li>
        <li>Neon's agent strengths are not covered by Part 1.</li></ul></div>
    </div>
    <p style="margin-top:16px"><a href="${BLOB}docs/approach.md">Read the full approach and reasoning →</a></p>
  </section>`;
}

function run() {
  return `
  <section style="margin-top:0">
    <div class="eyebrow">Run it yourself</div>
    <h2>Rerun every test on your own project</h2>
    <p class="lede">Python 3.10+ and the standard library only. A full 5-run pass costs about $25 at list price.</p>
    <div class="grid g2">
      <div class="card"><h3 style="margin-top:0">1 · Set up</h3>
<pre>git clone ${REPO}.git
cd gemini4-enterprise-races

# Gemini API
export GEMINI_API_KEY="your-key"
# or Vertex AI (takes precedence)
export GOOGLE_CLOUD_PROJECT="your-project-id"</pre></div>
      <div class="card"><h3 style="margin-top:0">2 · Run and summarize</h3>
<pre>python3 races/race1_analyst.py --runs 5
python3 races/race2_intake.py  --runs 5
python3 races/race_hard.py --task audit --runs 5
python3 races/part2_verify.py --runs 5
python3 scripts/summarize.py --print</pre></div>
    </div>
  </section>
  <section>
    <h2>Bring your own documents</h2>
    <ol class="steps">
      <li>Replace the text in <code>data/race1/</code> with your document, and write an answer key with the source of each value.</li>
      <li>Keep a few trap questions whose answer is not in the document.</li>
      <li>Run with <code>--out results/mine.jsonl</code> so your runs stay separate.</li>
      <li>Compare accuracy first, then time and cost.</li>
    </ol>
    <p><a href="${REPO}">Open the repository on GitHub →</a></p>
  </section>`;
}

const ROUTES = {part1, part2, method, run};

function render() {
  const [, tab = 'part1', anchor] = location.hash.split('/');
  const fn = ROUTES[tab] || part1;
  $('#view').innerHTML = fn();
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.tab === (ROUTES[tab] ? tab : 'part1')));
  if ($('#vol')) { $('#vol').addEventListener('input', renderScale); renderScale(); }
  if ($('#xd')) {
    document.querySelectorAll('.qb').forEach(b => b.onclick = () => { xQ = +b.dataset.q; renderX(); });
    renderX();
  }
  const target = anchor && (document.getElementById('uc-' + anchor) || document.getElementById(anchor));
  if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
  else window.scrollTo(0, 0);
}

function initTheme() {
  const root = document.documentElement;
  if (localStorage.getItem('g4-theme') === 'dark') root.classList.add('dark');
  $('#theme').addEventListener('click', () => {
    root.classList.toggle('dark');
    localStorage.setItem('g4-theme', root.classList.contains('dark') ? 'dark' : 'light');
  });
}

window.addEventListener('hashchange', render);
initTheme();
render();
