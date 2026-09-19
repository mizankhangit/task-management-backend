from rest_framework.permissions import BasePermission
from apps.projects.models import Project
from apps.projects.permissions import (
    ProjectPermission,
    user_has_permission,
)


class HasTaskPermission(BasePermission):
    """
    Base permission for tasks that resolves the task's project
    and checks if the requesting user has the required permission.
    """
    permission = None

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if isinstance(obj, Project):
            project = obj
        elif hasattr(obj, "project"):
            project = obj.project
        elif hasattr(obj, "task") and hasattr(obj.task, "project"):
            project = obj.task.project
        else:
            return False

        return user_has_permission(project, request.user, self.permission)


class CanViewTask(HasTaskPermission):
    permission = ProjectPermission.VIEW


class CanCreateTask(HasTaskPermission):
    permission = ProjectPermission.CREATE_TASK


class CanEditTask(HasTaskPermission):
    permission = ProjectPermission.EDIT_TASK


class CanDeleteTask(HasTaskPermission):
    permission = ProjectPermission.DELETE_TASK


class CanAssignTask(HasTaskPermission):
    permission = ProjectPermission.ASSIGN_TASK


class CanRestoreTask(HasTaskPermission):
    permission = ProjectPermission.CREATE_TASK
