from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(
    viewsets.ReadOnlyModelViewSet
):
    serializer_class = NotificationSerializer
    permission_classes = [
        IsAuthenticated
    ]

    def get_queryset(self):
        return (
            Notification.objects
            .filter(
                recipient=self.request.user
            )
            .select_related(
                "task",
                "project",
            )
            .order_by("-created_at")
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="read",
    )
    def mark_as_read(
        self,
        request,
        pk=None,
    ):
        notification = self.get_object()

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()

            notification.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

        return Response(
            NotificationSerializer(
                notification
            ).data
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="read-all",
    )
    def mark_all_as_read(
        self,
        request,
    ):
        updated = (
            self.get_queryset()
            .filter(is_read=False)
            .update(
                is_read=True,
                read_at=timezone.now(),
            )
        )

        return Response({
            "updated": updated,
        })

    @action(
        detail=False,
        methods=["get"],
        url_path="unread-count",
    )
    def unread_count(
        self,
        request,
    ):
        count = (
            self.get_queryset()
            .filter(is_read=False)
            .count()
        )

        return Response({
            "count": count,
        })