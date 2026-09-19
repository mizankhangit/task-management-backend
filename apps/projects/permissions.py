from rest_framework.permissions import BasePermission
from .models import ProjectMembership

class ProjectPermission:
    VIEW = "view"
    CREATE_TASK = "create_task"
    EDIT_TASK = "edit_task"
    DELETE_TASK = "delete_task"
    ASSIGN_TASK = "assign_task"
    MANAGE_MEMBERS = "manage_members"
    CHANGE_ROLES = "change_roles"
    DELETE_PROJECT = "delete_project"

ROLE_HIERARCHY = {
    ProjectMembership.Role.VIEWER: 10,
    ProjectMembership.Role.MEMBER: 20,
    ProjectMembership.Role.ADMIN: 30,
    ProjectMembership.Role.OWNER: 40,
}

ROLE_PERMISSIONS = {
    ProjectMembership.Role.OWNER: {
        ProjectPermission.VIEW,
        ProjectPermission.CREATE_TASK,
        ProjectPermission.EDIT_TASK,
        ProjectPermission.DELETE_TASK,
        ProjectPermission.ASSIGN_TASK,
        ProjectPermission.MANAGE_MEMBERS,
        ProjectPermission.CHANGE_ROLES,
        ProjectPermission.DELETE_PROJECT,
    },

    ProjectMembership.Role.ADMIN: {
        ProjectPermission.VIEW,
        ProjectPermission.CREATE_TASK,
        ProjectPermission.EDIT_TASK,
        ProjectPermission.DELETE_TASK,
        ProjectPermission.ASSIGN_TASK,
        ProjectPermission.MANAGE_MEMBERS,
        ProjectPermission.CHANGE_ROLES,
    },

    ProjectMembership.Role.MEMBER: {
        ProjectPermission.VIEW,
        ProjectPermission.CREATE_TASK,
        ProjectPermission.EDIT_TASK,
        ProjectPermission.ASSIGN_TASK,
    },

    ProjectMembership.Role.VIEWER: {
        ProjectPermission.VIEW,
    },
}

def get_membership(
    project,
    user,
):
    return (
        ProjectMembership.objects
        .filter(
            project=project,
            user=user,
        )
        .first()
    )

def user_has_permission(
    project,
    user,
    permission,
):
    if not user or not user.is_authenticated:
        return False

    # Safety: project creator/owner always has all permissions
    if getattr(project, "owner_id", None) == user.id or getattr(project, "owner", None) == user:
        return True

    membership = get_membership(
        project,
        user,
    )

    if membership is None:
        return False

    return permission in ROLE_PERMISSIONS.get(
        membership.role,
        set(),
    )

def user_has_role(
    project,
    user,
    minimum_role,
):
    if not user or not user.is_authenticated:
        return False

    if getattr(project, "owner_id", None) == user.id or getattr(project, "owner", None) == user:
        return True

    membership = get_membership(
        project,
        user,
    )

    if membership is None:
        return False

    user_level = ROLE_HIERARCHY.get(
        membership.role, 0
    )

    required_level = ROLE_HIERARCHY.get(
        minimum_role, 0
    )

    return user_level >= required_level

def get_project_membership(project, user):
    return (
        ProjectMembership.objects
        .filter(project=project, user=user)
        .first()
    )

def has_project_role(project, user, allowed_roles):
    if not user or not user.is_authenticated:
        return False
    if getattr(project, "owner_id", None) == user.id or getattr(project, "owner", None) == user:
        return True
    membership = get_project_membership(project, user)
    if not membership:
        return False
    return membership.role in allowed_roles


class HasProjectPermission(BasePermission):
    """
    Base permission that resolves project from either a Project or related object (e.g. Task, ProjectMembership)
    and checks if the requesting user has the required ProjectPermission.
    """
    permission = None

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        from .models import Project
        if isinstance(obj, Project):
            project = obj
        elif hasattr(obj, "project"):
            project = obj.project
        elif hasattr(obj, "memberships") or hasattr(obj, "owner"):
            project = obj
        else:
            return False

        return user_has_permission(project, request.user, self.permission)


class CanViewProject(HasProjectPermission):
    permission = ProjectPermission.VIEW


class CanCreateTask(HasProjectPermission):
    permission = ProjectPermission.CREATE_TASK


class CanEditTask(HasProjectPermission):
    permission = ProjectPermission.EDIT_TASK


class CanDeleteTask(HasProjectPermission):
    permission = ProjectPermission.DELETE_TASK


class CanAssignTask(HasProjectPermission):
    permission = ProjectPermission.ASSIGN_TASK


class CanManageMembers(HasProjectPermission):
    permission = ProjectPermission.MANAGE_MEMBERS


class CanChangeRoles(HasProjectPermission):
    permission = ProjectPermission.CHANGE_ROLES


class CanDeleteProject(HasProjectPermission):
    permission = ProjectPermission.DELETE_PROJECT