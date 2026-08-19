from rest_framework.permissions import BasePermission
from .services import track_api_request

class TrackAPIUsage(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            track_api_request(request.user)
        return True