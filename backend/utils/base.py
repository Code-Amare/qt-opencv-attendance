from rest_framework.views import APIView

from .auth import IsTenantAdmin


class TenantAdminView(APIView):
    permission_classes = [IsTenantAdmin]

    @property
    def tenant(self):
        return self.request.user.tenant
