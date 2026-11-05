"""
نماذج تسجيل الدخول للقوالب
Login forms for HTML templates
"""
from django import forms


class LoginForm(forms.Form):
    """نموذج تسجيل الدخول"""

    username = forms.CharField(
        label="اسم المستخدم",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white/90 shadow-sm focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition",
                "placeholder": "أدخل اسم المستخدم",
                "autocomplete": "username",
                "dir": "ltr",
            }
        ),
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white/90 shadow-sm focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition",
                "placeholder": "أدخل كلمة المرور",
                "autocomplete": "current-password",
                "dir": "ltr",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label="تذكرني",
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "w-4 h-4 text-teal-700 border-slate-300 rounded focus:ring-teal-500",
            }
        ),
    )
