/**
 * أدوات الذكاء الاصطناعي لوضع الزائر
 * Guest mode AI tools - summarize & Q&A only
 */

const GuestTools = {
    panel: null,
    uploadId: '',

    init() {
        this.panel = document.getElementById('guest-ai-panel');
        if (!this.panel) return;

        this.uploadId = this.panel.dataset.uploadId;

        document.querySelectorAll('.guest-tool-btn').forEach(btn => {
            btn.addEventListener('click', () => this.selectTool(btn.dataset.tool));
        });

        document.getElementById('guest-clear-result')?.addEventListener('click', () => this.clearResult());
    },

    basePath() {
        return `/guest/upload/${this.uploadId}`;
    },

    selectTool(tool) {
        const optionsEl = document.getElementById('guest-tool-options');
        optionsEl.classList.remove('hidden');

        document.querySelectorAll('.guest-tool-btn').forEach(btn => {
            btn.classList.toggle('ring-2', btn.dataset.tool === tool);
            btn.classList.toggle('ring-primary-500', btn.dataset.tool === tool);
        });

        const options = {
            summarize: `
                <p class="text-sm text-slate-600 mb-3">اختر طول الملخص:</p>
                <div class="flex flex-wrap gap-2">
                    <button type="button" class="guest-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50" data-action="summarize" data-length="short">قصير</button>
                    <button type="button" class="guest-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50" data-action="summarize" data-length="medium">متوسط</button>
                    <button type="button" class="guest-action-btn px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-primary-50" data-action="summarize" data-length="detailed">مفصل</button>
                </div>`,
            ask: `
                <p class="text-sm text-slate-600 mb-3">اكتب سؤالك عن الملف:</p>
                <textarea id="guest-question-input" rows="3" placeholder="مثال: ما هي النقاط الرئيسية في هذا المستند؟"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-200 outline-none resize-none"></textarea>
                <button type="button" class="guest-action-btn mt-2 w-full py-2 bg-primary-700 text-white rounded-lg text-sm hover:bg-primary-800" data-action="ask">إرسال السؤال</button>`,
        };

        optionsEl.innerHTML = options[tool] || '';
        optionsEl.querySelectorAll('.guest-action-btn').forEach(btn => {
            btn.addEventListener('click', () => this.handleAction(btn));
        });
    },

    async handleAction(btn) {
        const action = btn.dataset.action;
        this.showLoading();
        this.hideError();

        try {
            let endpoint, body, title;

            switch (action) {
                case 'summarize':
                    endpoint = `${this.basePath()}/summarize/`;
                    body = { length: btn.dataset.length };
                    title = `ملخص ${btn.textContent}`;
                    break;
                case 'ask':
                    const question = document.getElementById('guest-question-input')?.value?.trim();
                    if (!question) throw new Error('يرجى كتابة سؤال.');
                    endpoint = `${this.basePath()}/ask/`;
                    body = { question };
                    title = 'سؤال وجواب';
                    break;
                default:
                    return;
            }

            const { data, ok } = await API.request(endpoint, { method: 'POST', body });

            if (!ok || !data.success) {
                throw new Error(data.detail || 'فشلت العملية.');
            }

            this.showResult(title, this.formatResult(action, data.data), data.tokens_used);

        } catch (err) {
            this.showError(err.message || 'حدث خطأ غير متوقع.');
        } finally {
            this.hideLoading();
        }
    },

    formatResult(action, data) {
        switch (action) {
            case 'summarize':
                return data.summary || '';
            case 'ask':
                return `السؤال: ${data.question}\n\nالإجابة:\n${data.answer}`;
            default:
                return JSON.stringify(data, null, 2);
        }
    },

    showLoading() {
        document.getElementById('guest-loading')?.classList.remove('hidden');
    },

    hideLoading() {
        document.getElementById('guest-loading')?.classList.add('hidden');
    },

    showResult(title, content, tokens) {
        document.getElementById('guest-result-empty')?.classList.add('hidden');
        document.getElementById('guest-result-title').textContent = title;
        document.getElementById('guest-result-content').textContent = content;
        document.getElementById('guest-result-meta').textContent = tokens ? `استُخدم ${tokens} رمز` : '';
        document.getElementById('guest-result-area')?.classList.remove('hidden');
        document.getElementById('guest-error')?.classList.add('hidden');
    },

    showError(message) {
        const el = document.getElementById('guest-error');
        if (el) {
            el.textContent = message;
            el.classList.remove('hidden');
        }
    },

    hideError() {
        document.getElementById('guest-error')?.classList.add('hidden');
    },

    clearResult() {
        document.getElementById('guest-result-area')?.classList.add('hidden');
        document.getElementById('guest-result-empty')?.classList.remove('hidden');
        document.getElementById('guest-result-content').textContent = '';
    },
};

document.addEventListener('DOMContentLoaded', () => GuestTools.init());
