from django.contrib.auth.models import User
from django.db import models


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        TASK_ASSIGNED = (
            "task_assigned",
            "Task Assigned",
        )
        TASK_STATUS_CHANGED = (
            "task_status_changed",
            "Task Status Changed",
        )
        TASK_COMMENTED = (
            "task_commented",
            "Task Commented",
        )
        PROJECT_INVITATION = (
            "project_invitation",
            "Project Invitation",
        )
        MEMBER_ADDED = (
            "member_added",
            "Member Added",
        )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]