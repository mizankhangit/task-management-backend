from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    message = "You do not have permission to access this resource."

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return obj.owner == request.user

class IsTaskOwner(BasePermission):
    message = "You do not have permission to access this task."

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return obj.project.owner == request.user