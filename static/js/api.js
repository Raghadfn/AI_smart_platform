/**
 * أدوات API - طلبات fetch مع JWT
 * API utilities - fetch wrapper with JWT support
 */

const API = {
    baseUrl: '/api/v1',

    /**
     * الحصول على CSRF token من ملفات تعريف الارتباط
     */
    getCsrfToken() {
        const name = 'csrftoken=';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name)) {
                return decodeURIComponent(cookie.substring(name.length));
            }
        }
        return '';
    },

    /**
     * طلب API عام
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken(),
            ...options.headers,
        };

        const config = {
            credentials: 'same-origin',
            ...options,
            headers,
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        const response = await fetch(url, config);
        const data = await response.json().catch(() => ({}));

        if (response.status === 401 && !endpoint.includes('/auth/refresh')) {
            const refreshed = await this.refreshToken();
            if (refreshed) {
                return this.request(endpoint, options);
            }
        }

        return { response, data, ok: response.ok };
    },

    /**
     * تجديد رمز الوصول
     */
    async refreshToken() {
        const { ok } = await fetch(`${this.baseUrl}/auth/refresh/`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify({}),
        });
        return ok;
    },

    /**
     * تسجيل الدخول
     */
    async login(username, password) {
        return this.request('/auth/login/', {
            method: 'POST',
            body: { username, password },
        });
    },

    /**
     * تسجيل الخروج
     */
    async logout() {
        return this.request('/auth/logout/', { method: 'POST' });
    },

    /**
     * بيانات المستخدم الحالي
     */
    async me() {
        return this.request('/auth/me/');
    },
};
