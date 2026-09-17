from apps.core.permissions import IsTaskOwner
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsTaskOwner]

    def get_queryset(self):
        queryset = (
            Task.objects
            .filter(project__owner=self.request.user)
            .select_related("project")
        )

        status = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        completed = self.request.query_params.get("completed")
        project = self.request.query_params.get("project")
        search = self.request.query_params.get("search")
        ordering = self.request.query_params.get("ordering")

        if status:
            queryset = queryset.filter(status=status)

        if priority:
            queryset = queryset.filter(priority=priority)

        if completed is not None:
            queryset = queryset.filter(
                completed=completed.lower() == "true"
            )

        if project:
            queryset = queryset.filter(
                project_id=project
            )

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
            )

        allowed_ordering = {
            "created_at",
            "-created_at",
            "title",
            "-title",
        }

        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]

        if project.owner != self.request.user:
            raise PermissionDenied(
                "You do not have permission to use this project."
            )

        serializer.save() 