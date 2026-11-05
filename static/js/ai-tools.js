/**
 * أدوات الذكاء الاصطناعي للمحاضرات
 * AI tools - async Fetch API, history, interactive exams
 */

const AITools = {
    panel: null,
    yearSlug: '',
    subjectSlug: '',
    lectureSlug: '',
    lectureId: '',
    activeTool: null,
    currentExam: null,
    currentSavedId: null,
    currentAction: null,
    _mermaidSeq: 0,
    _mermaidSources: {},

    TYPE_LABELS: {
        translation: 'ترجمة',
        summary: 'تلخيص',
        qa: 'سؤال وجواب',
        exam: 'امتحان',
        illustration: 'شرح بصري',
    },

    TYPE_ICONS: {
        translation: '🌐',
        summary: '📝',
        qa: '❓',
        exam: '📋',
        illustration: '🖼️',
    },

    init() {
        this.panel = document.getElementById('ai-panel');
        if (!this.panel) return;

        this.yearSlug = this.panel.dataset.yearSlug;
        this.subjectSlug = this.panel.dataset.subjectSlug;
        this.lectureSlug = this.panel.dataset.lectureSlug;
        this.lectureId = this.panel.dataset.lectureId;
        this.hasContent = this.panel.dataset.hasContent === 'true';

        document.querySelectorAll('.ai-tool-btn').forEach(btn => {
            btn.addEventListener('click', () => this.selectTool(btn.dataset.tool));
        });

        document.getElementById('ai-tab-tools')?.addEventListener('click', () => this.showTab('tools'));
        document.getElementById('ai-tab-history')?.addEventListener('click', () => this.showTab('history'));
        document.getElementById('ai-close-output')?.addEventListener('click', () => this.closeOutput());
        document.getElementById('ai-copy-btn')?.addEventListener('click', () => this.copyOutput());

        this.showTab('tools');
    },

    showTab(tab) {
        const toolsSection = document.getElementById('ai-tools-section');
        const historySection = document.getElementById('ai-history-section');
        const tabTools = document.getElementById('ai-tab-tools');
        const tabHistory = document.getElementById('ai-tab-history');

        if (tab === 'history') {
            toolsSection?.classList.add('hidden');
            historySection?.classList.remove('hidden');
            tabTools?.classList.remove('bg-white', 'shadow-sm', 'text-primary-700');
            tabTools?.classList.add('text-slate-600');
            tabHistory?.classList.add('bg-white', 'shadow-sm', 'text-primary-700');
            tabHistory?.classList.remove('text-slate-600');
            this.loadHistory();
        } else {
            toolsSection?.classList.remove('hidden');
            historySection?.classList.add('hidden');
            tabHistory?.classList.remove('bg-white', 'shadow-sm', 'text-primary-700');
            tabHistory?.classList.add('text-slate-600');
            tabTools?.classList.add('bg-white', 'shadow-sm', 'text-primary-700');
            tabTools?.classList.remove('text-slate-600');
        }
    },

    basePath() {
        return `/years/${this.yearSlug}/subjects/${this.subjectSlug}/lectures/${this.lectureSlug}`;
    },

    shouldSave() {
        return document.getElementById('ai-save-toggle')?.checked !== false;
    },

    selectTool(tool) {
        this.activeTool = tool;
        const optionsEl = document.getElementById('ai-tool-options');
        optionsEl.classList.remove('hidden');

        document.querySelectorAll('.ai-tool-btn').forEach(btn => {
            btn.classList.toggle('ring-2', btn.dataset.tool === tool);
            btn.classList.toggle('ring-primary-500', btn.dataset.tool === tool);
        });

        const options = {
            translate: `
                <p class="text-sm text-slate-600 mb-3">اختر لغة الترجمة:</p>
                <div class="flex flex-wrap gap-2" id="ai-translate-lang-buttons">
                    <button type="button" class="ai-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50 transition" data-action="translate" data-lang="ar">العربية</button>
                    <button type="button" class="ai-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50 transition" data-action="translate" data-lang="en">English</button>
                </div>`,
            summarize: `
                <p class="text-sm text-slate-600 mb-3">اختر طول الملخص:</p>
                <div class="flex flex-wrap gap-2">
                    <button type="button" class="ai-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50 transition" data-action="summarize" data-length="short">قصير</button>
                    <button type="button" class="ai-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50 transition" data-action="summarize" data-length="medium">متوسط</button>
                    <button type="button" class="ai-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50 transition" data-action="summarize" data-length="detailed">مفصل</button>
                </div>`,
            ask: `
                <p class="text-sm text-slate-600 mb-3">اكتب سؤالك عن المحاضرة (يمكنك طلب رسماً توضيحياً):</p>
                <textarea id="ai-question-input" rows="3" placeholder="مثال: ارسم مخططاً يوضح دورة حياة البرمجيات"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-200 outline-none resize-none"></textarea>
                <label class="flex items-center gap-2 text-xs text-slate-500 mt-2 cursor-pointer">
                    <input type="checkbox" id="ai-force-visual" class="rounded text-teal-600">
                    أرفق مخططاً انسيابياً مع الإجابة
                </label>
                <button type="button" class="ai-action-btn mt-2 w-full py-2 bg-primary-700 text-white rounded-lg text-sm hover:bg-primary-800 transition" data-action="ask">إرسال السؤال</button>`,
            illustrate: `
                <p class="text-xs text-slate-500 mb-2">مخطط انسيابي تفصيلي — كل خطوة مع شرح من المحاضرة</p>
                <textarea id="ai-illustrate-input" rows="2" placeholder="مثال: خوارزمية البحث الثنائي"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-200 outline-none resize-none"></textarea>
                <button type="button" class="ai-action-btn mt-2 w-full py-2 bg-teal-700 text-white rounded-lg text-sm hover:bg-teal-800 transition" data-action="illustrate">عرض المخطط</button>`,
            exam: `
                <p class="text-sm text-slate-600 mb-2">أسئلة اختيار من متعدد عالية الجودة من محتوى المحاضرة</p>
                <label class="block text-sm text-slate-600 mb-1">عدد الأسئلة</label>
                <input type="number" id="ai-exam-count" value="5" min="1" max="20" class="w-full mt-1 px-3 py-2 border border-slate-200 rounded-lg text-sm">
                <button type="button" class="ai-action-btn mt-3 w-full py-2 bg-teal-700 text-white rounded-2xl text-sm font-bold hover:bg-teal-800 transition" data-action="exam">إنشاء الامتحان التفاعلي</button>`,
        };

        optionsEl.innerHTML = options[tool] || '';
        optionsEl.querySelectorAll('.ai-action-btn').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleAction(btn);
            });
        });
    },

    async handleAction(btn) {
        const action = btn.dataset.action;
        this.currentAction = action;
        this.showLoading(action);
        this.hideError();

        try {
            let endpoint, body, title;

            switch (action) {
                case 'translate': {
                    const targetLang = (btn.getAttribute('data-lang') || btn.dataset.lang || '').trim().toLowerCase();
                    if (targetLang !== 'ar' && targetLang !== 'en') {
                        throw new Error('لغة الترجمة غير مدعومة. المتاح: العربية والإنجليزية.');
                    }
                    endpoint = `${this.basePath()}/translate/`;
                    body = {
                        target_lang: targetLang,
                        save: this.shouldSave(),
                        lecture_id: this.lectureId,
                    };
                    title = targetLang === 'ar' ? 'ترجمة إلى العربية' : 'ترجمة إلى الإنجليزية';
                    console.debug('[AI translate] payload', body);
                    break;
                }
                case 'summarize':
                    endpoint = `${this.basePath()}/summarize/`;
                    body = { length: btn.dataset.length, save: this.shouldSave(), lecture_id: this.lectureId };
                    title = `ملخص ${btn.textContent}`;
                    break;
                case 'ask':
                    const question = document.getElementById('ai-question-input')?.value?.trim();
                    if (!question) throw new Error('يرجى كتابة سؤال.');
                    endpoint = `${this.basePath()}/ask/`;
                    body = {
                        question,
                        save: this.shouldSave(),
                        lecture_id: this.lectureId,
                        force_visual: document.getElementById('ai-force-visual')?.checked === true,
                    };
                    title = 'سؤال وجواب';
                    break;
                case 'illustrate':
                    const concept = document.getElementById('ai-illustrate-input')?.value?.trim();
                    if (!concept) throw new Error('يرجى وصف المفهوم المراد رسمه.');
                    endpoint = `${this.basePath()}/illustrate/`;
                    body = { concept, save: this.shouldSave(), lecture_id: this.lectureId };
                    title = 'شرح بصري';
                    break;
                case 'exam':
                    const count = Math.max(
                        1,
                        Math.min(parseInt(document.getElementById('ai-exam-count')?.value || '5', 10) || 5, 20)
                    );
                    endpoint = `${this.basePath()}/generate-exam/`;
                    body = { types: ['mcq'], count, save: this.shouldSave(), lecture_id: this.lectureId };
                    title = 'امتحان تفاعلي';
                    break;
                default:
                    return;
            }

            if (!this.hasContent && !this.lectureId) {
                throw new Error('لا يوجد سياق محاضرة متاح للمساعد.');
            }

            const { data, ok } = await API.request(endpoint, { method: 'POST', body });

            if (!ok || !data.success) {
                throw new Error(data.detail || data.error || 'فشلت العملية.');
            }

            this.currentSavedId = data.saved_result_id || null;
            if (this.currentSavedId) this.showSavedToast();

            if (action === 'exam') {
                const examPayload = data.data || {};
                if (!Array.isArray(examPayload.questions) || !examPayload.questions.length) {
                    throw new Error('لم يتم إنشاء أسئلة. حاول مرة أخرى.');
                }
                this.renderInteractiveExam(examPayload, title, data.tokens_used);
            } else if (action === 'translate') {
                const payload = data.data || {};
                if (!payload.translated_text) {
                    throw new Error('لم يُرجع الخادم نصاً مترجماً. حاول مرة أخرى.');
                }
                this.showOutput(
                    title,
                    this.renderContent('translate', payload),
                    data.tokens_used || payload.tokens_used,
                    'translate'
                );
            } else {
                this.showOutput(title, this.renderContent(action, data.data), data.tokens_used, action);
            }

        } catch (err) {
            this.showError(err.message || 'حدث خطأ غير متوقع.');
        } finally {
            this.hideLoading();
        }
    },

    renderContent(action, data) {
        switch (action) {
            case 'translate': {
                const langCode = (data.target_lang || data.target_language || '').toLowerCase();
                const langLabel = langCode === 'ar'
                    ? 'العربية'
                    : langCode === 'en'
                        ? 'الإنجليزية'
                        : (data.target_language_name || langCode || '');
                return `<div class="p-4 bg-blue-50 rounded-xl border border-blue-100">
                    <p class="text-sm text-blue-600 mb-2">اللغة: ${this.escapeHtml(langLabel)}</p>
                    <p class="whitespace-pre-wrap">${this.escapeHtml(data.translated_text || '')}</p>
                </div>`;
            }
            case 'summarize':
                return `<div class="p-4 bg-green-50 rounded-xl border border-green-100">
                    <p class="text-sm text-green-600 mb-2">${data.length_label || 'ملخص'}</p>
                    <p class="whitespace-pre-wrap">${this.escapeHtml(data.summary || '')}</p>
                </div>`;
            case 'ask':
                return this.renderAskOrIllustration(data);
            case 'illustrate':
                return this.renderVisualSummary(data);
            default:
                return `<pre class="text-sm">${this.escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
        }
    },

    renderVisualSummary(data) {
        if (data.illustration_error) {
            return `<p class="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl p-3">تعذّر توليد المخطط: ${this.escapeHtml(data.illustration_error)}</p>`;
        }
        const illustration = data.illustration || data;
        return this.renderIllustration(illustration) || '';
    },

    renderAskOrIllustration(data) {
        let html = `<div class="space-y-4">`;
        if (data.question) {
            html += `<div class="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <p class="text-xs text-slate-500 mb-1">السؤال</p>
                <p class="font-medium">${this.escapeHtml(data.question || '')}</p>
            </div>`;
        }
        if (data.answer) {
            html += `<div class="p-4 bg-accent-50 rounded-xl border border-accent-100">
                <p class="text-xs text-accent-600 mb-1">الإجابة</p>
                <p class="whitespace-pre-wrap">${this.escapeHtml(data.answer || '')}</p>
            </div>`;
        }
        const diagram = this.renderIllustration(data.illustration);
        if (diagram) html += diagram;
        if (data.illustration_error) {
            html += `<p class="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl p-3">تعذّر توليد المخطط: ${this.escapeHtml(data.illustration_error)}</p>`;
        }
        html += `</div>`;
        return html;
    },

    renderIllustration(illustration) {
        let source = illustration?.mermaid;
        if (!source && Array.isArray(illustration?.nodes) && illustration.nodes.length) {
            source = this.buildMermaidFromNodes(
                illustration.nodes,
                illustration.connections,
                illustration.direction || 'TD'
            );
        }
        // توافق مع نتائج HTML القديمة (steps)
        if (!source && Array.isArray(illustration?.steps) && illustration.steps.length) {
            const nodes = illustration.steps.map((s, i) => ({
                id: `n${s.step || i + 1}`,
                label: s.title || s.label || '',
                explanation: s.explanation || s.description || '',
                step: s.step || i + 1,
            }));
            source = this.buildMermaidFromNodes(nodes, null, 'TD');
        }
        if (!source) return '';

        const ref = `mm${++this._mermaidSeq}`;
        this._mermaidSources[ref] = source;
        return `<div class="ai-flowchart-view" data-mermaid-ref="${ref}"></div>`;
    },

    sanitizeMermaidText(text) {
        return String(text || '')
            .replace(/[\r\n]+/g, ' ')
            .replace(/"/g, "'")
            .replace(/`/g, "'")
            .replace(/[<>\[\]{}|]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    },

    normVisualPhrase(text) {
        return String(text || '')
            .replace(/[\s:：.\-–—،؛,]+/g, ' ')
            .trim()
            .toLowerCase();
    },

    stripRepeatedSentence(text) {
        let t = String(text || '').trim();
        if (!t) return '';
        const m = t.match(/^(.+?)[\s:：.\-–—،؛]+\1[\s.]*$/s);
        if (m) return m[1].trim();
        const parts = t.split(/[.۔]\s*/).map((p) => p.trim()).filter(Boolean);
        if (parts.length >= 2 && this.normVisualPhrase(parts[0]) === this.normVisualPhrase(parts[1])) {
            return parts[0].replace(/[.:：،؛]+$/, '') + '.';
        }
        return t;
    },

    dedupeLabelExplanation(label, explanation) {
        let title = this.stripRepeatedSentence(String(label || '').trim());
        let detail = this.stripRepeatedSentence(String(explanation || '').trim());
        if (title && detail) {
            const nTitle = this.normVisualPhrase(title);
            for (let i = 0; i < 4; i++) {
                const nDetail = this.normVisualPhrase(detail);
                if (!nDetail || nDetail === nTitle) {
                    detail = '';
                    break;
                }
                if (!nDetail.startsWith(nTitle)) break;
                const esc = title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                let stripped = detail.replace(new RegExp('^' + esc + '[\\s:：.\\-–—،؛]*', 'i'), '').trim();
                if (!stripped || this.normVisualPhrase(stripped) === nDetail) {
                    const wordsL = nTitle.split(/\s+/).filter(Boolean);
                    const origWords = detail.split(/\s+/).filter(Boolean);
                    stripped = origWords.length > wordsL.length
                        ? origWords.slice(wordsL.length).join(' ').replace(/^[:：.\-–—،؛\s]+/, '').trim()
                        : '';
                }
                if (!stripped || this.normVisualPhrase(stripped) === nTitle) {
                    detail = '';
                    break;
                }
                detail = stripped;
            }
            detail = this.stripRepeatedSentence(detail);
        }
        if (title && detail && this.normVisualPhrase(title) === this.normVisualPhrase(detail)) {
            detail = '';
        }
        return { title, detail };
    },

    formatMermaidNodeText(label, explanation) {
        const { title, detail } = this.dedupeLabelExplanation(label, explanation);
        const safeTitle = this.sanitizeMermaidText(title);
        const safeDetail = this.sanitizeMermaidText(detail);
        if (safeTitle && safeDetail) return `${safeTitle}<br/>${safeDetail}`;
        return safeTitle || safeDetail;
    },

    buildMermaidFromNodes(nodes, connections, direction = 'TD') {
        const sorted = [...nodes].sort((a, b) => (a.step || 0) - (b.step || 0));
        const dir = (direction === 'LR') ? 'LR' : 'TD';
        const lines = [
            "%%{init: {'flowchart': {'htmlLabels': true, 'curve': 'basis', 'padding': 22, 'nodeSpacing': 48, 'rankSpacing': 56, 'useMaxWidth': false, 'wrappingWidth': 9999}, 'useMaxWidth': false}}%%",
            `flowchart ${dir}`,
        ];
        const idMap = {};

        sorted.forEach((node, i) => {
            const safeId = (node.id || `n${i + 1}`).replace(/[^a-zA-Z0-9_]/g, '') || `n${i + 1}`;
            idMap[node.id || safeId] = safeId;
            const text = this.formatMermaidNodeText(
                node.label || node.title || '',
                node.explanation || node.description || ''
            );
            lines.push(`    ${safeId}["${text}"]`);
        });

        if (Array.isArray(connections) && connections.length) {
            connections.forEach((c) => {
                const src = idMap[c.from];
                const dst = idMap[c.to];
                if (!src || !dst) return;
                const edge = this.sanitizeMermaidText(c.label || '');
                lines.push(edge ? `    ${src} -->|"${edge}"| ${dst}` : `    ${src} --> ${dst}`);
            });
        } else {
            for (let i = 0; i < sorted.length - 1; i++) {
                const src = idMap[sorted[i].id || `n${i + 1}`];
                const dst = idMap[sorted[i + 1].id || `n${i + 2}`];
                if (src && dst) lines.push(`    ${src} --> ${dst}`);
            }
        }

        lines.push('    classDef default fill:#f8fafc,stroke:#0f766e,stroke-width:1.5px,color:#0f172a');
        return lines.join('\n');
    },

    async hydrateMermaidDiagrams(root) {
        if (!root || typeof mermaid === 'undefined') return;

        const placeholders = root.querySelectorAll('[data-mermaid-ref]');
        const nodes = [];

        placeholders.forEach((el) => {
            const ref = el.getAttribute('data-mermaid-ref');
            const source = this._mermaidSources[ref];
            if (!source) return;

            const pre = document.createElement('pre');
            pre.className = 'mermaid';
            pre.textContent = source;
            el.appendChild(pre);
            nodes.push(pre);
            el.removeAttribute('data-mermaid-ref');
        });

        if (!nodes.length) return;

        try {
            await mermaid.run({ nodes });
        } catch (err) {
            console.error('Mermaid render failed:', err);
            placeholders.forEach((el) => {
                if (!el.querySelector('svg')) {
                    el.innerHTML = '<p class="ai-flowchart-view__error">تعذّر عرض المخطط. حاول مرة أخرى.</p>';
                }
            });
        }
    },
    renderInteractiveExam(examData, title, tokens) {
        const questions = examData.questions || [];
        this.currentExam = { data: examData, savedId: this.currentSavedId };

        let html = `<form id="exam-form" class="space-y-6">`;
        html += `<p class="text-sm text-teal-600 font-medium">${this.escapeHtml(examData.exam_title || title)} — ${questions.length} سؤال</p>`;

        questions.forEach((q, i) => {
            html += `<div class="p-4 bg-slate-50 rounded-xl border border-slate-200" data-qid="${q.id}">`;
            html += `<p class="font-medium text-slate-800 mb-3"><span class="text-teal-600">${i + 1}.</span> ${this.escapeHtml(q.question)}</p>`;
            html += `<span class="text-xs px-2 py-0.5 bg-white rounded border border-slate-200 text-slate-500">${this.getQuestionTypeLabel(q.type)}</span>`;

            if (q.type === 'mcq' && q.options) {
                html += `<div class="mt-3 space-y-2">`;
                q.options.forEach((opt, j) => {
                    html += `<label class="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-teal-300 transition">
                        <input type="radio" name="q_${q.id}" value="${this.escapeAttr(opt)}" class="text-teal-600">
                        <span class="text-sm">${this.escapeHtml(opt)}</span>
                    </label>`;
                });
                html += `</div>`;
            } else if (q.type === 'true_false') {
                html += `<div class="mt-3 flex gap-3">
                    <label class="flex-1 flex items-center justify-center gap-2 p-3 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-green-300 transition">
                        <input type="radio" name="q_${q.id}" value="صح" class="text-green-600"> صح
                    </label>
                    <label class="flex-1 flex items-center justify-center gap-2 p-3 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-red-300 transition">
                        <input type="radio" name="q_${q.id}" value="خطأ" class="text-red-600"> خطأ
                    </label>
                </div>`;
            } else {
                html += `<textarea name="q_${q.id}" rows="3" placeholder="اكتب إجابتك..."
                    class="w-full mt-3 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-200 outline-none resize-none"></textarea>`;
            }
            html += `</div>`;
        });

        html += `<button type="submit" class="w-full py-3 bg-teal-700 text-white rounded-2xl font-bold hover:bg-teal-800 transition flex items-center justify-center gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            تسليم الإجابات والتصحيح
        </button></form>`;

        this.showOutput(title, html, tokens, 'exam');

        document.getElementById('exam-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitExam(questions);
        });
    },

    async submitExam(questions) {
        if (!this.currentSavedId) {
            this.showError('يجب حفظ الامتحان أولاً لتسليم الإجابات. فعّل خيار الحفظ.');
            return;
        }

        const answers = {};
        questions.forEach(q => {
            const radio = document.querySelector(`input[name="q_${q.id}"]:checked`);
            const textarea = document.querySelector(`textarea[name="q_${q.id}"]`);
            answers[String(q.id)] = radio ? radio.value : (textarea?.value || '');
        });

        this.showLoading('grading');
        this.hideError();

        try {
            const { data, ok } = await API.request(`/saved-results/${this.currentSavedId}/submit/`, {
                method: 'POST',
                body: { answers },
            });

            if (!ok || !data.success) {
                throw new Error(data.detail || 'فشل التصحيح.');
            }

            this.showExamResults(data);
        } catch (err) {
            this.showError(err.message);
        } finally {
            this.hideLoading();
        }
    },

    showExamResults(data) {
        const pct = data.score_percent;
        const scoreBg = pct >= 70 ? 'bg-green-50 border-green-200' : pct >= 50 ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200';
        const scoreText = pct >= 70 ? 'text-green-700' : pct >= 50 ? 'text-amber-700' : 'text-red-700';
        const scoreSub = pct >= 70 ? 'text-green-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600';

        let html = `<div class="text-center mb-6 p-6 rounded-2xl border ${scoreBg}">
            <p class="text-4xl font-bold ${scoreText}">${pct}%</p>
            <p class="text-sm ${scoreSub} mt-1">${data.correct_count} من ${data.total_gradable} إجابة صحيحة</p>
        </div>`;

        html += `<div class="space-y-4">`;
        (data.grading_details || []).forEach((d, i) => {
            const status = d.graded === false
                ? '<span class="text-slate-500">يحتاج مراجعة يدوية</span>'
                : d.is_correct
                    ? '<span class="text-green-600 font-medium">✓ صحيح</span>'
                    : '<span class="text-red-600 font-medium">✗ خطأ</span>';

            html += `<div class="p-4 rounded-xl border ${d.is_correct === true ? 'bg-green-50 border-green-200' : d.is_correct === false ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200'}">
                <p class="font-medium mb-2">${i + 1}. ${this.escapeHtml(d.question)}</p>
                <p class="text-sm text-slate-600">إجابتك: ${this.escapeHtml(d.user_answer || '—')}</p>
                ${d.graded ? `<p class="text-sm text-slate-600">الإجابة الصحيحة: ${this.escapeHtml(d.correct_answer)}</p>` : ''}
                <p class="text-sm mt-1">${status}</p>
                ${d.explanation ? `<p class="text-xs text-slate-500 mt-2 p-2 bg-white rounded">${this.escapeHtml(d.explanation)}</p>` : ''}
            </div>`;
        });
        html += `</div>`;

        this.showOutput('نتيجة الامتحان', html, null, 'exam-result');
    },

    showOutput(title, html, tokens, type) {
        const panel = document.getElementById('ai-output-panel');
        const titleEl = document.getElementById('ai-output-title');
        const metaEl = document.getElementById('ai-output-meta');
        const contentEl = document.getElementById('ai-output-content');
        const copyBtn = document.getElementById('ai-copy-btn');

        if (!panel) return;

        this.currentAction = type || null;
        const isDiagramOnly = type === 'illustrate';

        panel.classList.toggle('ai-output-panel--diagram', isDiagramOnly);

        if (isDiagramOnly) {
            titleEl.textContent = 'شرح بصري';
            metaEl.textContent = '';
            copyBtn?.classList.add('hidden');
        } else {
            titleEl.textContent = title;
            const parts = [];
            if (tokens) parts.push(`استُخدم ${tokens} رمز`);
            if (this.currentSavedId) parts.push('محفوظ في سجلك');
            metaEl.textContent = parts.join(' · ');
            copyBtn?.classList.remove('hidden');
        }

        contentEl.innerHTML = html;
        this.hydrateMermaidDiagrams(contentEl);
        panel.classList.remove('hidden');
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    closeOutput() {
        document.getElementById('ai-output-panel')?.classList.add('hidden');
        document.getElementById('ai-output-panel')?.classList.remove('ai-output-panel--diagram');
        this.currentExam = null;
        this.currentAction = null;
    },

    async copyOutput() {
        const content = document.getElementById('ai-output-content');
        if (!content) return;
        try {
            await navigator.clipboard.writeText(content.innerText);
            const btn = document.getElementById('ai-copy-btn');
            btn?.classList.add('text-green-600');
            setTimeout(() => btn?.classList.remove('text-green-600'), 1500);
        } catch {
            this.showError('تعذّر النسخ.');
        }
    },

    async loadHistory() {
        const loading = document.getElementById('ai-history-loading');
        const empty = document.getElementById('ai-history-empty');
        const list = document.getElementById('ai-history-list');

        loading?.classList.remove('hidden');
        empty?.classList.add('hidden');
        list.innerHTML = '';

        try {
            const { data, ok } = await API.request(`/saved-results/?lecture=${this.lectureId}`);
            loading?.classList.add('hidden');

            const results = Array.isArray(data) ? data : (data.results || []);
            if (!ok || !results.length) {
                empty?.classList.remove('hidden');
                return;
            }

            results.forEach(item => {
                const el = document.createElement('button');
                el.type = 'button';
                el.className = 'w-full text-right p-3 bg-slate-50 hover:bg-primary-50 rounded-xl border border-slate-200 hover:border-primary-200 transition group';
                el.innerHTML = `
                    <div class="flex items-start justify-between gap-2">
                        <span class="text-lg">${this.TYPE_ICONS[item.result_type] || '📄'}</span>
                        <div class="flex-grow min-w-0">
                            <p class="text-sm font-medium text-slate-800 truncate">${this.escapeHtml(item.title)}</p>
                            <p class="text-xs text-slate-400">${this.TYPE_LABELS[item.result_type] || item.result_type} · ${this.formatDate(item.created_at)}</p>
                        </div>
                        <button type="button" class="delete-history opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 p-1" data-id="${item.id}" title="حذف">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        </button>
                    </div>`;

                el.addEventListener('click', (e) => {
                    if (e.target.closest('.delete-history')) return;
                    this.loadSavedResult(item);
                });

                el.querySelector('.delete-history')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.deleteHistoryItem(item.id);
                });

                list.appendChild(el);
            });
        } catch {
            loading?.classList.add('hidden');
            empty?.classList.remove('hidden');
            empty.textContent = 'تعذّر تحميل السجل';
        }
    },

    async loadSavedResult(item) {
        try {
            const { data, ok } = await API.request(`/saved-results/${item.id}/`);
            if (!ok) throw new Error('تعذّر تحميل النتيجة');

            this.currentSavedId = item.id;
            const resultData = data.result_data || item.result_data;

            if (item.result_type === 'exam') {
                this.renderInteractiveExam(resultData, item.title, resultData.tokens_used);
            } else {
                const actionMap = {
                    translation: 'translate',
                    summary: 'summarize',
                    qa: 'ask',
                    illustration: 'illustrate',
                };
                const action = actionMap[item.result_type] || item.result_type;
                this.showOutput(item.title, this.renderContent(action, resultData), resultData.tokens_used, action);
            }
            this.showTab('tools');
        } catch (err) {
            this.showError(err.message);
        }
    },

    async deleteHistoryItem(id) {
        if (!confirm('حذف هذه النتيجة من السجل؟')) return;
        try {
            await API.request(`/saved-results/${id}/`, { method: 'DELETE' });
            this.loadHistory();
        } catch {
            this.showError('تعذّر الحذف.');
        }
    },

    getQuestionTypeLabel(type) {
        return { mcq: 'اختيار من متعدد', true_false: 'صح وخطأ', essay: 'مقالي' }[type] || type;
    },

    formatDate(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleDateString('ar', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch {
            return iso;
        }
    },

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    escapeAttr(str) {
        return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },

    showLoading(action) {
        const el = document.getElementById('ai-loading');
        const text = document.getElementById('ai-loading-text');
        if (el) el.classList.remove('hidden');
        if (text) {
            const messages = {
                grading: 'جاري التصحيح...',
                illustrate: 'جاري إنشاء التلخيص البصري...',
                ask: 'جاري تحليل السؤال والإجابة...',
                translate: 'جاري الترجمة... قد يستغرق ذلك دقيقة إذا كان النموذج مشغولاً.',
            };
            text.textContent = messages[action] || 'جاري المعالجة بالذكاء الاصطناعي...';
        }
    },

    hideLoading() {
        document.getElementById('ai-loading')?.classList.add('hidden');
    },

    showError(message) {
        const el = document.getElementById('ai-error');
        if (el) {
            el.textContent = message;
            el.classList.remove('hidden');
        }
    },

    hideError() {
        document.getElementById('ai-error')?.classList.add('hidden');
    },

    showSavedToast() {
        const toast = document.getElementById('ai-saved-toast');
        if (!toast) return;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 3000);
    },
};

document.addEventListener('DOMContentLoaded', () => AITools.init());
