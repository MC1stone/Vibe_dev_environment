// S6: contextual chatbot panel (MO 10) — shared by analysis results and
// project report pages. Reads window.nirChatbotContext set by the embedding
// page and posts to /api/chatbot/message/ (existing endpoint, unchanged).
(function () {
    const state = { history: [] };

    function esc(text) {
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    function render(role, content) {
        const box = document.getElementById('chatbotPanelMessages');
        if (!box) return;
        const wrapper = document.createElement('div');
        const isUser = role === 'user';
        wrapper.className = 'd-flex mb-2 ' + (isUser ? 'justify-content-end' : 'justify-content-start');
        const bubble = document.createElement('div');
        bubble.className = isUser ? 'bg-primary text-white rounded p-2' : 'bg-light rounded p-2';
        bubble.style.maxWidth = '85%';
        bubble.innerHTML = isUser ? esc(content) : content;
        wrapper.appendChild(bubble);
        box.appendChild(wrapper);
        box.scrollTop = box.scrollHeight;
    }

    window.nirChatbotPanelSend = function () {
        const input = document.getElementById('chatbotPanelInput');
        const typing = document.getElementById('chatbotPanelTyping');
        const sources = document.getElementById('chatbotPanelSources');
        const question = (input.value || '').trim();
        if (!question) return;
        input.value = '';
        render('user', question);
        typing.hidden = false;

        const ctx = window.nirChatbotContext || {};
        // OP66: Fusionsergebnisse (Kalibrationsvergleich, Signifikanz-Test,
        // Fazit) als Dokument in die KI-Diskussion einspeisen - die
        // Nutzer-KI-Diskussion bezieht sich damit auf die tatsaechlich
        // gerechnete kombinierte Analyse.
        const documents = (ctx.documents || []).slice();
        if (ctx.fusion_discussion) {
            documents.push({
                source: 'fusion_calibration',
                text: String(ctx.fusion_discussion)
            });
        }
        const payload = {
            question: question,
            analysis_results: ctx.analysis_results || [],
            documents: documents,
            history: state.history.slice(-6),
            // OP79 Stufe 2: eigene Projektliste als Kontext - der
            // Server erkennt Fusions-Wuensche strukturiert (kein LLM).
            context_projects: ctx.context_projects || []
        };

        fetch('/api/chatbot/message/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': (function () {
                    const el = document.querySelector('[name=csrfmiddlewaretoken]');
                    return el ? el.value : '';
                })(),
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        })
            .then(r => r.json().catch(() => ({})))
            .then(data => {
                typing.hidden = true;
                if (data.degraded) {
                    render('assistant', '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> ' +
                        esc(data.error || 'Chatbot nicht verfügbar (Ollama nicht erreichbar).') + '</span>');
                    return;
                }
                if (data.answer) {
                    render('assistant', esc(data.answer).replace(/\n/g, '<br>'));
                    state.history.push({ role: 'user', content: question });
                    state.history.push({ role: 'assistant', content: data.answer });
                    // OP79 Stufe 2: Fusion-Wunsch erkannt -> strukturierte
                    // Bestaetigungskarte mit Button (nie automatisch).
                    const fi = data.fusion_intent;
                    if (fi && fi.ready && (fi.project_ids || []).length >= 2) {
                        const btn = document.createElement('button');
                        btn.className = 'btn btn-sm btn-success mt-1';
                        btn.innerHTML = '<i class="bi bi-boxes me-1"></i>' +
                            'Zusammenführen: ' + esc((fi.projects || [])
                                .map(p => p.name).join(' + '));
                        btn.onclick = function () {
                            btn.disabled = true;
                            window.nirFusionPreviewResult =
                                document.getElementById('fusionProjectsResult')
                                || document.getElementById('fusionPreviewResult');
                            window.nirFusionPreview(fi.project_ids);
                        };
                        const last = document.getElementById('chatbotPanelMessages');
                        if (last) {
                            const w = document.createElement('div');
                            w.className = 'd-flex justify-content-start mb-2';
                            w.appendChild(btn);
                            last.appendChild(w);
                            last.scrollTop = last.scrollHeight;
                        }
                    }
                    const rag = data.rag_sources || [];
                    sources.textContent = rag.length
                        ? 'RAG: ' + rag.join(', ')
                        : '';
                } else {
                    render('assistant', '<span class="text-danger">Unerwartete Antwort: ' +
                        esc(JSON.stringify(data)) + '</span>');
                }
            })
            .catch(err => {
                typing.hidden = true;
                render('assistant', '<span class="text-danger">Anfrage fehlgeschlagen: ' +
                    esc(err.message) + '</span>');
            });
    };
})();
