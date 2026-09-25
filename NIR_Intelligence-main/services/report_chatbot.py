# NIR Intelligence Platform - embedded report chatbot widget (OP24, OP37)
# KI-first chat widget inside the final HTML report: every question is
# first sent to the local Ollama/Mistral chatbot (/api/chatbot/message/,
# services/chatbot_service.py) together with a compact report context and
# the conversation history. Only when the local KI is unreachable (report
# opened as a plain file, server down) does the widget fall back to the
# client-side keyword knowledge base - then honestly labelled as offline.
# The knowledge base itself is still built by agents/chatbot_agent.py at
# release time and also feeds the suggestion chips.
import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger('Service.ReportChatbot')

_MAX_CONTEXT_CHARS = 4000


def build_chatbot_widget(knowledge_base: List[Dict[str, Any]],
                         context_documents: List[Dict[str, str]] = None) -> str:
    """Return the HTML for the chat widget ('' when the base is empty)."""
    if not knowledge_base:
        return ''
    payload = json.dumps(knowledge_base, ensure_ascii=False)
    payload = payload.replace('</', '<\\/')
    docs = json.dumps((context_documents or [])[:24], ensure_ascii=False)
    docs = docs.replace('</', '<\\/')
    return _WIDGET_TEMPLATE.replace('__KB__', payload).replace('__CTX__', docs)


def _compact_report_context(per_agent: List[Dict[str, Any]],
                            crew_results: Dict[str, Any],
                            datasets: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Compact, bounded text documents describing the report results - the
    RAG context for the KI chat (anti-hallucination: facts only, straight
    from the analysis results, nothing invented)."""
    documents: List[Dict[str, str]] = []

    def add(source: str, text: str):
        text = ' '.join(str(text).split())
        if text:
            documents.append({'source': source, 'text': text[:_MAX_CONTEXT_CHARS]})

    score = crew_results.get('overall_quality_score')
    if score is not None:
        add('gesamt',
            f"Gesamtqualitaet der Analyse: {score} von 100 Punkten. "
            f"Empfehlungen: {'; '.join(str(r) for r in crew_results.get('recommendations', [])[:6])}")
    for dataset in datasets:
        meta = dataset.get('metadata') or {}
        facts = [f"Datei {dataset.get('file_name', '?')}"]
        for key in ('sample_description', 'operator_name', 'instrument_type',
                    'instrument_model', 'serial_number', 'temperature',
                    'humidity', 'integration_time', 'wavelength_range',
                    'resolution', 'scan_count', 'target_name'):
            if meta.get(key):
                facts.append(f"{key}={meta[key]}")
        add(str(dataset.get('file_name', 'datensatz')), ', '.join(facts))
    for section in per_agent:
        data = section.get('data') or {}
        parts = [f"{section.get('title', section.get('agent', 'Agent'))} "
                 f"(Status {section.get('status', '?')})"]
        for key in ('overall_quality_score', 'best_r2_score', 'best_method',
                    'mean_r2', 'r2_score', 'rmse', 'noise_detected',
                    'drift_detected', 'offset_detected', 'quality_grade',
                    'assessable', 'measurement_count', 'outlier_indices',
                    'threshold', 'analysis_summary', 'verdict'):
            if isinstance(data, dict) and data.get(key) is not None:
                parts.append(f"{key}: {data[key]}")
        for finding in (data.get('findings') or [])[:4] if isinstance(data, dict) else []:
            parts.append(f"Befund: {finding}")
        add(str(section.get('agent', 'section')), '; '.join(parts))
    return documents


_WIDGET_TEMPLATE = """<section id="chatbot-section"><h2>Fragen zur Analyse (Chatbot)</h2><div class="card" id="chatbot-card">  <p class="muted">Fragen Sie frei zu diesem Bericht - die lokale KI (Ollama/Mistral)  antwortet aus den Analyseergebnissen. Ohne Server greift der Chatbot auf  die eingebaute Wissensbasis zur\u00fcck (dann als 'Offline' gekennzeichnet).</p>  <div id="chatbot-log" style="max-height:320px;overflow-y:auto;"></div>  <form id="chatbot-form" style="display:flex;gap:8px;margin-top:8px;">    <input id="chatbot-input" type="text" autocomplete="off"           placeholder="z. B. Welche Messungen sind Ausreisser und warum?"           style="flex:1;padding:8px;border:1px solid #ced4da;border-radius:6px;">    <button id="chatbot-submit" type="submit" style="padding:8px 16px;border:0;border-radius:6px;            background:#0d6efd;color:#fff;cursor:pointer;">Fragen</button>  </form>  <div id="chatbot-chips" style="margin-top:8px;"></div></div><script>(function () {  var KB = __KB__;  var CTX = __CTX__;  var log = document.getElementById('chatbot-log');  var form = document.getElementById('chatbot-form');  var input = document.getElementById('chatbot-input');  var submitBtn = document.getElementById('chatbot-submit');  var history = [];  var offlineNoted = false;  var busy = false;  function fold(s) {    return (s || '').toLowerCase()      .replace(/\\u00e4/g, 'a').replace(/\\u00f6/g, 'o').replace(/\\u00fc/g, 'u')      .replace(/\\u00df/g, 'ss').replace(/\\u00e9|\\u00e8/g, 'e');  }  function scoreEntry(entry, q) {    var qf = fold(q);    var score = 0;    var words = qf.split(/[^a-z0-9]+/).filter(function (w) { return w.length > 2; });    for (var i = 0; i < entry.keywords.length; i++) {      var kw = fold(entry.keywords[i]);      if (qf.indexOf(kw) !== -1) { score += 3; }      for (var j = 0; j < words.length; j++) {        if (kw.indexOf(words[j]) !== -1 && words[j].length > 3) { score += 1; }      }    }    var qWords = fold(entry.question).split(/[^a-z0-9]+/);    for (var k = 0; k < words.length; k++) {      if (qWords.indexOf(words[k]) !== -1) { score += 2; }    }    return score;  }  function topEntries(q, max) {    var scored = [];    for (var i = 0; i < KB.length; i++) {      var s = scoreEntry(KB[i], q);      if (s >= 2) { scored.push({ entry: KB[i], score: s }); }    }    scored.sort(function (a, b) { return b.score - a.score; });    var out = [];    for (var j = 0; j < scored.length && out.length < max; j++) {      out.push(scored[j].entry);    }    return out;  }  function addMessage(role, html) {    var div = document.createElement('div');    div.style.margin = '6px 0';    div.innerHTML = '<b>' + (role === 'user' ? 'Sie' : 'Chatbot') + ':</b> ' + html;    div.style.textAlign = role === 'user' ? 'right' : 'left';    log.appendChild(div);    log.scrollTop = log.scrollHeight;  }  function esc(s) {    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')      .replace(/>/g, '&gt;');  }  function figLink(entry) {    if (!entry || !entry.figure) { return ''; }    return ' <a href="#chatbot-section" onclick="jumpToFigure(' +      entry.figure + ');return false;">Zur Abbildung ' + entry.figure +    '</a>';  }  function offlineFallback(q) {    if (!offlineNoted) {      addMessage('bot', '<span class="muted">[Offline]</span> Die lokale KI ' +        '(Ollama/Mistral) ist gerade nicht erreichbar - ich antworte aus ' +        'der eingebauten Wissensbasis dieses Berichts.');      offlineNoted = true;    }    var entries = topEntries(q, 2);    if (!entries.length) {      addMessage('bot', 'Dazu habe ich in den Analyseergebnissen nichts ' +        'gefunden. Versuchen Sie Begriffe wie <i>Kalibration</i>, ' +        '<i>Wellenl\\u00e4nge</i>, <i>Ausreisser</i>, <i>Sensor</i>, <i>PCA</i> ' +        'oder <i>RMSE</i> - oder schauen Sie in die Diskussion des ' +        'Berichts.');      return;    }    for (var i = 0; i < entries.length; i++) {      addMessage('bot', '<span class="muted">[Offline-Wissensbasis: ' +        esc(entries[i].category) + ']</span> ' + esc(entries[i].answer) +        figLink(entries[i]));    }  }  function askKI(q) {    busy = true;    submitBtn.disabled = true;    submitBtn.textContent = 'KI denkt \\u2026';    var ctrl = (typeof AbortController === 'function')      ? new AbortController() : null;    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, 90000) : null;    fetch('/api/chatbot/message/', {      method: 'POST',      headers: { 'Content-Type': 'application/json' },      body: JSON.stringify({        question: q,        documents: CTX,        history: history.slice(-6)      }),      signal: ctrl ? ctrl.signal : undefined    }).then(function (res) {      return res.json().then(function (body) { return { ok: res.ok, body: body }; });    }).then(function (result) {      if (timer) { clearTimeout(timer); }      var answer = result && result.body && result.body.answer;      if (answer) {        history.push({ role: 'user', content: q });        history.push({ role: 'assistant', content: answer });        addMessage('bot', '<span class="muted">[KI (' +          esc((result.body.model || 'Mistral').split(':')[0]) + ')]</span> ' +          esc(answer));      } else {        offlineFallback(q);      }    }).catch(function () {      if (timer) { clearTimeout(timer); }      offlineFallback(q);    }).then(function () {      busy = false;      submitBtn.disabled = false;      submitBtn.textContent = 'Fragen';    });  }  function answer(q) {    askKI(q);  }  window.jumpToFigure = function (n) {    var imgs = document.querySelectorAll('.chart, img');    var count = 0;    for (var i = 0; i < imgs.length; i++) {      if ((imgs[i].tagName === 'IMG' &&           imgs[i].getAttribute('src') || '').indexOf('data:image') === 0) {        count++;        if (count === n) {          imgs[i].scrollIntoView({behavior: 'smooth', block: 'center'});          imgs[i].style.outline = '3px solid #0d6efd';          setTimeout(function (el) {            return function () { el.style.outline = ''; };          }(imgs[i]), 2500);          return;        }      }    }    var h2 = document.createElement('div');    h2.textContent = 'Abbildung ' + n + ' ist in dieser Version nicht ' +      'enthalten (z. B. ohne TensorFlow wurde der Plot nicht erzeugt).';    log.appendChild(h2);  };  form.addEventListener('submit', function (ev) {    ev.preventDefault();    var q = (input.value || '').trim();    if (!q || busy) { return; }    addMessage('user', esc(q));    input.value = '';    try { answer(q); } catch (e) {      addMessage('bot', 'Interner Fehler bei der Antwortfindung.');    }  });  var seen = {};  var suggestions = 0;  for (var i = 0; i < KB.length && suggestions < 4; i++) {    var cat = KB[i].category;    if (seen[cat]) { continue; }    seen[cat] = true;    suggestions++;    (function (question) {      var chip = document.createElement('button');      chip.type = 'button';      chip.textContent = question;      chip.style.cssText = 'display:inline-block;margin:2px 4px;padding:4px ' +        '10px;border:1px solid #ced4da;border-radius:14px;background:#f8f9fa;' +        'cursor:pointer;font-size:0.85em;';      chip.addEventListener('click', function () {        input.value = question;        form.dispatchEvent(new Event('submit'));      });      chips.appendChild(chip);    })(KB[i].question);  }  addMessage('bot', 'Hallo! Ich beantworte Ihre Fragen zu den Ergebnissen ' +    'dieses Berichts mit der lokalen KI - zum Beispiel zur Kalibration, ' +    'zu Ausreissern, zu den Spektren, zum Sensor oder zu den Methoden ' +    '(PLS, PCA, RMSE).');})();</script></section>"""


def chatbot_html(per_agent: List[Dict[str, Any]],
                 crew_results: Dict[str, Any],
                 datasets: List[Dict[str, Any]],
                 overview_keys: List[str] = None) -> Dict[str, str]:
    """Run the ChatbotAgent and render the widget. Returns the widget HTML
    ('' when the agent fails or the base is empty). Never raises."""
    try:
        from agents.chatbot_agent import ChatbotAgent
        output = ChatbotAgent().execute({
            "per_agent_reports": per_agent,
            "crew_results": crew_results,
            "datasets": datasets,
            "overview_keys": overview_keys or [],
        })
        base = ((output.data or {}).get("knowledge_base")) or []
        context = _compact_report_context(per_agent, crew_results, datasets)
        return {"widget": build_chatbot_widget(base, context)}
    except Exception:
        logger.exception("Chatbot widget rendering failed (non-fatal)")
        return {"widget": ""}
