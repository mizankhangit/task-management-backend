from django.db.models import Count, Q
from rest_framework import status as http_status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied
from apps.core.pagination import StandardResultsSetPagination
from apps.tasks.serializers import TaskSerializer

from .models import Project, ProjectMembership
from .serializers import ProjectSerializer, ProjectMembershipSerializer
from .permissions import (
    CanViewProject,
    CanCreateTask,
    CanManageMembers,
    CanChangeRoles,
    CanDeleteProject,
    user_has_permission,
    ProjectPermission,
)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in [
            "list",
            "retrieve",
            "task_statistics",
            "activities",
        ]:
            permission_classes = [
                CanViewProject
            ]

        elif self.action == "members":
            permission_classes = [
                CanManageMembers
            ]

        elif self.action in [
            "destroy",
            "transfer_ownership",
        ]:
            permission_classes = [
                CanDeleteProject
            ]

        elif self.action == "leave":
            permission_classes = [
                CanViewProject
            ]

        elif self.action in [
            "update",
            "partial_update",
        ]:
            permission_classes = [
                CanChangeRoles
            ]

        elif self.action == "tasks":
            if self.request.method == "POST":
                permission_classes = [
                    CanCreateTask
                ]
            else:
                permission_classes = [
                    CanViewProject
                ]

        else:
            permission_classes = [
                CanViewProject
            ]

        return [
            permission()
            for permission
            in permission_classes
        ]

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Project.objects
            .filter(
                Q(owner=user)
                | Q(memberships__user=user)
            )
            .distinct()
            .annotate(
                tasks_count=Count(
                    "tasks",
                    filter=Q(tasks__is_deleted=False),
                    distinct=True,
                ),
                completed_tasks_count=Count(
                    "tasks",
                    filter=Q(tasks__completed=True, tasks__is_deleted=False),
                    distinct=True,
                ),
            )
        )

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        ordering = self.request.query_params.get("ordering", "-created_at")
        allowed_orderings = {
            "created_at",
            "-created_at",
            "name",
            "-name",
            "tasks_count",
            "-tasks_count",
        }

        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        
        # Auto-add owner 
        ProjectMembership.objects.get_or_create(
            project=project,
            user=self.request.user,
            defaults={"role": ProjectMembership.Role.OWNER},
        )

    @action(detail=True, methods=["get", "post"], url_path="tasks")
    def tasks(self, request, pk=None):
        project = self.get_object()

        if request.method == "GET":
            tasks = project.tasks.filter(is_deleted=False)

            task_status = request.query_params.get("status")
            priority = request.query_params.get("priority")
            completed = request.query_params.get("completed")
            search = request.query_params.get("search")
            ordering = request.query_params.get("ordering")

            if task_status:
                tasks = tasks.filter(status=task_status)

            if priority:
                tasks = tasks.filter(priority=priority)

            if completed is not None:
                tasks = tasks.filter(completed=completed.lower() == "true")

            if search:
                tasks = tasks.filter(
                    Q(title__icontains=search) | Q(description__icontains=search)
                )

            allowed_ordering = {
                "created_at",
                "-created_at",
                "title",
                "-title",
            }

            if ordering in allowed_ordering:
                tasks = tasks.order_by(ordering)
            else:
                tasks = tasks.order_by("-created_at")

            page = self.paginate_queryset(tasks)
            if page is not None:
                serializer = TaskSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = TaskSerializer(tasks, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            payload = (
                request.data.copy()
                if hasattr(request.data, "copy")
                else dict(request.data)
            )
            payload["project"] = project.id

            serializer = TaskSerializer(data=payload)
            serializer.is_valid(raise_exception=True)
            serializer.save(project=project)
            return Response(
                serializer.data,
                status=http_status.HTTP_201_CREATED,
            )
    
    @action(
        detail=True,
        methods=["get"],
        url_path="task-statistics",
    )
    def task_statistics(self, request, pk=None):
        project = self.get_object()

        today = timezone.localdate()

        stats = project.tasks.filter(is_deleted=False).aggregate(
            total=Count("id"),

            todo=Count(
                "id",
                filter=Q(status="todo"),
            ),

            in_progress=Count(
                "id",
                filter=Q(status="in_progress"),
            ),

            done=Count(
                "id",
                filter=Q(status="done"),
            ),

            high_priority=Count(
                "id",
                filter=Q(priority="high"),
            ),

            overdue=Count(
                "id",
                filter=Q(
                    due_date__lt=today,
                    completed=False,
                ),
            ),
        )

        return Response(stats)

    @action(
        detail=True,
        methods=["get"],
        url_path="activities",
    )
    def activities(self, request, pk=None):
        project = self.get_object()
        from apps.tasks.models import TaskActivity
        from apps.tasks.serializers import TaskActivitySerializer

        activities = (
            TaskActivity.objects
            .filter(task__project=project)
            .select_related("user", "task")
            .order_by("-created_at")[:50]
        )

        serializer = TaskActivitySerializer(activities, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="members",
    )
    def members(self, request, pk=None):
        project = self.get_object()

        if request.method == "GET":
            memberships = (
                project.memberships
                .select_related("user")
                .all()
            )

            serializer = ProjectMembershipSerializer(
                memberships,
                many=True,
                context={"request": request},
            )

            return Response(serializer.data)

        elif request.method == "POST":
            payload = (
                request.data.copy()
                if hasattr(request.data, "copy")
                else dict(request.data)
            )
            payload["project"] = project.id

            serializer = ProjectMembershipSerializer(
                data=payload,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(project=project)

            return Response(
                serializer.data,
                status=http_status.HTTP_201_CREATED,
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="leave",
    )
    def leave(self, request, pk=None):
        project = self.get_object()
        user = request.user

        if project.owner_id == user.id or project.owner == user:
            return Response(
                {"detail": "Project owner cannot leave the project. Transfer ownership or delete the project."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        membership = project.memberships.filter(user=user).first()
        if not membership:
            return Response(
                {"detail": "You are not a member of this project."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        membership.delete()
        return Response(
            {"detail": "You have successfully left the project."},
            status=http_status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="transfer-ownership",
    )
    def transfer_ownership(self, request, pk=None):
        project = self.get_object()
        user = request.user

        if project.owner_id != user.id and project.owner != user:
            raise PermissionDenied("Only the project owner can transfer ownership.")

        new_owner_id = request.data.get("user_id") or request.data.get("new_owner_id")
        if not new_owner_id:
            return Response(
                {"detail": "user_id is required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        new_owner = User.objects.filter(id=new_owner_id).first()
        if not new_owner:
            return Response(
                {"detail": "User not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        if new_owner.id == user.id:
            return Response(
                {"detail": "You are already the owner of this project."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        # Update or create membership for new owner
        new_membership, _ = ProjectMembership.objects.get_or_create(
            project=project,
            user=new_owner,
            defaults={"role": ProjectMembership.Role.OWNER},
        )
        new_membership.role = ProjectMembership.Role.OWNER
        new_membership.save(update_fields=["role"])

        # Demote previous owner to ADMIN
        old_membership = ProjectMembership.objects.filter(
            project=project,
            user=user,
        ).first()
        if old_membership:
            old_membership.role = ProjectMembership.Role.ADMIN
            old_membership.save(update_fields=["role"])

        project.owner = new_owner
        project.save(update_fields=["owner", "updated_at"])

        return Response(
            {"detail": f"Ownership successfully transferred to {new_owner.username}."},
            status=http_status.HTTP_200_OK,
        )


class ProjectMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMembershipSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [CanViewProject]
        elif self.action == "create":
            permission_classes = [CanManageMembers]
        elif self.action == "destroy":
            permission_classes = [CanViewProject]
        elif self.action in ["update", "partial_update"]:
            permission_classes = [CanChangeRoles]
        else:
            permission_classes = [CanViewProject]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        queryset = (
            ProjectMembership.objects
            .filter(
                Q(project__owner=user)
                | Q(project__memberships__user=user)
            )
            .distinct()
            .select_related(
                "project",
                "user",
            )
        )

        project_id = self.request.query_params.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return queryset

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        user = self.request.user

        if not user_has_permission(project, user, ProjectPermission.MANAGE_MEMBERS):
            raise PermissionDenied("You do not have permission to add members to this project.")

        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        project = instance.project
        user = self.request.user

        if not user_has_permission(project, user, ProjectPermission.CHANGE_ROLES):
            raise PermissionDenied("You do not have permission to change roles in this project.")

        if instance.role == ProjectMembership.Role.OWNER or instance.user == project.owner:
            raise PermissionDenied("Project owner's role cannot be changed.")

        new_role = serializer.validated_data.get("role")
        if new_role == ProjectMembership.Role.OWNER:
            raise PermissionDenied("Owner role cannot be assigned to members.")

        if instance.role == ProjectMembership.Role.ADMIN and project.owner != user:
            raise PermissionDenied("Only the project owner can change an admin's role.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        project = instance.project

        # Project owner membership cannot be removed
        if instance.role == ProjectMembership.Role.OWNER or instance.user == project.owner:
            raise PermissionDenied("Project owner membership cannot be removed.")

        # Self-removal (leaving the project) is allowed for any non-owner member
        if instance.user == user:
            instance.delete()
            return

        # Otherwise, user must have MANAGE_MEMBERS
        if not user_has_permission(project, user, ProjectPermission.MANAGE_MEMBERS):
            raise PermissionDenied("You do not have permission to remove members from this project.")

        if instance.role == ProjectMembership.Role.ADMIN and project.owner != user:
            raise PermissionDenied("Only the project owner can remove admin members.")

        instance.delete()