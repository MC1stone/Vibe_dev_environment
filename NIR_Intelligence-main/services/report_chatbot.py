# NIR Intelligence Platform - embedded report chatbot widget (OP24)
# Renders the chatbot knowledge base (built by agents/chatbot_agent.py at
# release time) into a self-contained, fully offline chat widget inside
# the final HTML report. The matching runs client-side in vanilla JS:
#   - exact keyword hits (normalized, umlaut-folded) count per entry
#   - question-text similarity adds to the score
#   - the best entry is shown with its category, answer and - when set -
#     a jump link to the referenced figure
# No server, no network, no external libraries. Fallback answer when
# nothing matches. The widget degrades to nothing when the knowledge
# base is empty.

import json
from typing import Any, Dict, List


def build_chatbot_widget(knowledge_base: List[Dict[str, Any]]) -> str:
    """Return the HTML for the chat widget ('' when the base is empty)."""
    if not knowledge_base:
        return ""
    payload = json.dumps(knowledge_base, ensure_ascii=False)
    payload = payload.replace("</", "<\\/")
    return _WIDGET_TEMPLATE.replace("__KB__", payload)


_WIDGET_TEMPLATE = """
<section id="chatbot-section">
<h2>Fragen zur Analyse (Chatbot)</h2>
<div class="card" id="chatbot-card">
  <p class="muted">Stellen Sie Fragen zur Analyse - der Chatbot antwortet
  aus den Ergebnissen dieses Berichts (funktioniert offline, ohne Server).</p>
  <div id="chatbot-log" style="max-height:320px;overflow-y:auto;"></div>
  <form id="chatbot-form" style="display:flex;gap:8px;margin-top:8px;">
    <input id="chatbot-input" type="text" autocomplete="off"
           placeholder="z. B. Wie gut ist die Kalibration?"
           style="flex:1;padding:8px;border:1px solid #ced4da;border-radius:6px;">
    <button type="submit" style="padding:8px 16px;border:0;border-radius:6px;
            background:#0d6efd;color:#fff;cursor:pointer;">Fragen</button>
  </form>
  <div id="chatbot-chips" style="margin-top:8px;"></div>
</div>
<script>
(function () {
  var KB = __KB__;
  var log = document.getElementById('chatbot-log');
  var form = document.getElementById('chatbot-form');
  var input = document.getElementById('chatbot-input');
  var chips = document.getElementById('chatbot-chips');

  function fold(s) {
    return (s || '').toLowerCase()
      .replace(/\\u00e4/g, 'a').replace(/\\u00f6/g, 'o').replace(/\\u00fc/g, 'u')
      .replace(/\\u00df/g, 'ss').replace(/\\u00e9|\\u00e8/g, 'e');
  }

  function scoreEntry(entry, q) {
    var qf = fold(q);
    var score = 0;
    var words = qf.split(/[^a-z0-9]+/).filter(function (w) { return w.length > 2; });
    for (var i = 0; i < entry.keywords.length; i++) {
      var kw = fold(entry.keywords[i]);
      if (qf.indexOf(kw) !== -1) { score += 3; }
      for (var j = 0; j < words.length; j++) {
        if (kw.indexOf(words[j]) !== -1 && words[j].length > 3) { score += 1; }
      }
    }
    var qWords = fold(entry.question).split(/[^a-z0-9]+/);
    for (var k = 0; k < words.length; k++) {
      if (qWords.indexOf(words[k]) !== -1) { score += 2; }
    }
    return score;
  }

  function bestEntry(q) {
    var best = null, bestScore = 0;
    for (var i = 0; i < KB.length; i++) {
      var s = scoreEntry(KB[i], q);
      if (s > bestScore) { best = KB[i]; bestScore = s; }
    }
    return bestScore >= 2 ? best : null;
  }

  function addMessage(role, html) {
    var div = document.createElement('div');
    div.style.margin = '6px 0';
    div.innerHTML = '<b>' + (role === 'user' ? 'Sie' : 'Chatbot') + ':</b> ' + html;
    div.style.textAlign = role === 'user' ? 'right' : 'left';
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  function answer(q) {
    var entry = bestEntry(q);
    if (!entry) {
      addMessage('bot', 'Dazu habe ich in den Analyseergebnissen nichts ' +
        'gefunden. Versuchen Sie Begriffe wie <i>Kalibration</i>, ' +
        '<i>Wellenl\u00e4nge</i>, <i>Sensor</i>, <i>PCA</i>, <i>RMSE</i> oder ' +
        '<i>Optimierung</i> - oder schauen Sie in die Diskussion des ' +
        'Berichts.');
      return;
    }
    var fig = '';
    if (entry.figure) {
      fig = ' <a href="#chatbot-section" onclick="jumpToFigure(' +
        entry.figure + ');return false;">Zur Abbildung ' + entry.figure +
        '</a>';
    }
    addMessage('bot', '<span class="muted">[' + entry.category + ']</span> ' +
      entry.answer + fig);
  }

  window.jumpToFigure = function (n) {
    var imgs = document.querySelectorAll('.chart, img');
    var count = 0;
    for (var i = 0; i < imgs.length; i++) {
      if ((imgs[i].tagName === 'IMG' &&
           imgs[i].getAttribute('src') || '').indexOf('data:image') === 0) {
        count++;
        if (count === n) {
          imgs[i].scrollIntoView({behavior: 'smooth', block: 'center'});
          imgs[i].style.outline = '3px solid #0d6efd';
          setTimeout(function (el) {
            return function () { el.style.outline = ''; };
          }(imgs[i]), 2500);
          return;
        }
      }
    }
    var h2 = document.createElement('div');
    h2.textContent = 'Abbildung ' + n + ' ist in dieser Version nicht ' +
      'enthalten (z. B. ohne TensorFlow wurde der Plot nicht erzeugt).';
    log.appendChild(h2);
  };

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var q = (input.value || '').trim();
    if (!q) { return; }
    addMessage('user', q.replace(/</g, '&lt;'));
    input.value = '';
    try { answer(q); } catch (e) {
      addMessage('bot', 'Interner Fehler bei der Antwortfindung.');
    }
  });

  var seen = {};
  var suggestions = 0;
  for (var i = 0; i < KB.length && suggestions < 4; i++) {
    var cat = KB[i].category;
    if (seen[cat]) { continue; }
    seen[cat] = true;
    suggestions++;
    (function (question) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.textContent = question;
      chip.style.cssText = 'display:inline-block;margin:2px 4px;padding:4px ' +
        '10px;border:1px solid #ced4da;border-radius:14px;background:#f8f9fa;' +
        'cursor:pointer;font-size:0.85em;';
      chip.addEventListener('click', function () {
        input.value = question;
        form.dispatchEvent(new Event('submit'));
      });
      chips.appendChild(chip);
    })(KB[i].question);
  }

  addMessage('bot', 'Hallo! Ich beantworte Fragen zu den Ergebnissen ' +
    'dieses Berichts - zum Beispiel zur Kalibration, zu den Spektren, zum ' +
    'Sensor oder zu den Methoden (PLS, PCA, RMSE).');
})();
</script>
</section>
"""


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
        return {"widget": build_chatbot_widget(base)}
    except Exception:
        import logging

        logging.getLogger("Service.ReportChatbot").exception(
            "Chatbot widget rendering failed (non-fatal)")
        return {"widget": ""}
