from apps.tasks.serializers import TaskActivitySerializer
from django.db.models import Count, Q
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from apps.projects.permissions import (
    user_has_permission,
    ProjectPermission,
)
from .permissions import (
    CanViewTask,
    CanCreateTask,
    CanEditTask,
    CanDeleteTask,
    CanAssignTask,
    CanRestoreTask,
)
from .models import Task, TaskActivity
from .serializers import TaskSerializer
from .filters import TaskFilter
from .services import soft_delete_task, restore_task

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_permissions(self):
        if self.action in [
            "list",
            "retrieve",
            "statistics",
            "activities",
            "trash",
        ]:
            permission_classes = [
                CanViewTask
            ]

        elif self.action == "create":
            permission_classes = [
                CanCreateTask
            ]

        elif self.action in [
            "update",
            "partial_update",
        ]:
            permission_classes = [
                CanEditTask
            ]

        elif self.action in [
            "destroy",
            "permanent_delete",
        ]:
            permission_classes = [
                CanDeleteTask
            ]

        elif self.action == "restore":
            permission_classes = [
                CanRestoreTask
            ]

        else:
            permission_classes = [
                CanViewTask
            ]

        return [
            permission()
            for permission
            in permission_classes
        ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = TaskFilter

    search_fields = [
        "title",
        "description",
    ]

    ordering_fields = [
        "created_at",
        "updated_at",
        "due_date",
        "title",
        "priority",
        "status",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        user = self.request.user

        return (
            Task.objects
            .filter(
                Q(project__owner=user)
                | Q(
                    project__memberships__user=user
                ),
                is_deleted=False,
            )
            .select_related(
                "project",
                "assignee",
            )
            .distinct()
        )

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]

        if not user_has_permission(project, self.request.user, ProjectPermission.CREATE_TASK):
            raise PermissionDenied(
                "You do not have permission to create tasks in this project."
            )

        serializer.save()

    def perform_update(self, serializer):
        task = serializer.instance
        user = self.request.user

        if not user_has_permission(task.project, user, ProjectPermission.EDIT_TASK):
            raise PermissionDenied(
                "You do not have permission to edit tasks in this project."
            )

        if "assignee" in serializer.validated_data:
            new_assignee = serializer.validated_data["assignee"]
            if new_assignee != task.assignee and not user_has_permission(
                task.project, user, ProjectPermission.ASSIGN_TASK
            ):
                raise PermissionDenied(
                    "You do not have permission to assign tasks in this project."
                )

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        soft_delete_task(task=task, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        url_path="statistics",
    )
    def statistics(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        stats = queryset.aggregate(
            total=Count("id"),
            todo=Count(
                "id",
                filter=Q(status=Task.Status.TODO),
            ),
            in_progress=Count(
                "id",
                filter=Q(status=Task.Status.IN_PROGRESS),
            ),
            done=Count(
                "id",
                filter=Q(status=Task.Status.DONE),
            ),
        )

        return Response(stats)

    @action(
        detail=True,
        methods=["get"],
        url_path="activities",
    )
    def activities(self, request, pk=None):
        task = self.get_object()

        queryset = (
            task.activities
            .select_related("user")
            .all()
        )

        serializer = TaskActivitySerializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        task = (
            Task.objects
            .filter(
                Q(project__owner=request.user)
                | Q(project__memberships__user=request.user),
                is_deleted=True,
            )
            .select_related("project")
            .filter(pk=pk)
            .first()
        )

        if task is None:
            return Response(
                {
                    "detail": (
                        "Deleted task not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_has_permission(task.project, request.user, ProjectPermission.CREATE_TASK):
            raise PermissionDenied("You do not have permission to restore tasks in this project.")

        task = restore_task(task=task, user=request.user)

        return Response(
            TaskSerializer(task).data
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="trash",
    )
    def trash(self, request):
        queryset = (
            Task.objects
            .filter(
                Q(project__owner=request.user)
                | Q(project__memberships__user=request.user),
                is_deleted=True,
            )
            .distinct()
            .select_related("project", "deleted_by")
            .order_by("-deleted_at")
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
            )

            return self.get_paginated_response(
                serializer.data
            )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path="permanent",
    )
    def permanent_delete(
        self,
        request,
        pk=None,
    ):
        task = (
            Task.objects
            .filter(
                Q(project__owner=request.user)
                | Q(project__memberships__user=request.user),
                is_deleted=True,
            )
            .select_related("project")
            .filter(pk=pk)
            .first()
        )

        if task is None:
            return Response(
                {
                    "detail": (
                        "Deleted task not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_has_permission(task.project, request.user, ProjectPermission.DELETE_TASK):
            raise PermissionDenied("You do not have permission to permanently delete tasks in this project.")

        task.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )