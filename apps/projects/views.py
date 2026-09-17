from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsOwner
from apps.core.pagination import StandardResultsSetPagination

from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = (
            Project.objects
            .filter(owner=self.request.user)
            .annotate(
                tasks_count=Count("tasks", distinct=True),
                completed_tasks_count=Count(
                    "tasks",
                    filter=Q(tasks__completed=True),
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
        serializer.save(owner=self.request.user)