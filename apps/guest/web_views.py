"""
صفحات ويب لوضع الزائر
Guest mode web views
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from apps.guest.utils.session import get_guest_session_info, verify_guest_upload_access


class GuestWorkspaceView(View):
    """
    مساحة عمل الزائر - تلخيص وأسئلة
    GET /guest/<upload_id>/
    """

    template_name = "guest/workspace.html"

    def get(self, request, upload_id):
        if not verify_guest_upload_access(request, upload_id):
            messages.error(request, "انتهت صلاحية الجلسة أو الملف غير موجود.")
            return redirect("guest_web:upload")

        session_info = get_guest_session_info(request)
        if not session_info:
            return redirect("guest_web:upload")

        return render(request, self.template_name, {
            "upload_id": upload_id,
            "session_info": session_info,
        })
