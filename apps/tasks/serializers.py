from apps.tasks.models import TaskActivity
from apps.projects.models import ProjectMembership
from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )
    deleted_by = serializers.SerializerMethodField()

    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
    )

    assignee_name = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    ALLOWED_TRANSITIONS = {
        Task.Status.TODO: {
            Task.Status.TODO,
            Task.Status.IN_PROGRESS,
        },
        Task.Status.IN_PROGRESS: {
            Task.Status.TODO,
            Task.Status.IN_PROGRESS,
            Task.Status.DONE,
        },
        Task.Status.DONE: {
            Task.Status.DONE,
            Task.Status.IN_PROGRESS,
        },
    }

    class Meta:
        model = Task

        fields = [
            "id",
            "project",
            "project_name",
            "title",
            "description",
            "status",
            "priority",
            "completed",
            "due_date",
            "assignee",
            "assignee_name",
            "can_edit",
            "can_delete",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "project_name",
            "assignee_name",
            "can_edit",
            "can_delete",
            "completed",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "created_at",
            "updated_at",
        ]

    def get_assignee_name(self, obj):
        if not obj.assignee:
            return None
        return obj.assignee.get_full_name() or obj.assignee.username.capitalize()

    def get_can_edit(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        from apps.projects.permissions import user_has_permission, ProjectPermission
        return user_has_permission(obj.project, request.user, ProjectPermission.EDIT_TASK)

    def get_can_delete(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        from apps.projects.permissions import user_has_permission, ProjectPermission
        return user_has_permission(obj.project, request.user, ProjectPermission.DELETE_TASK)

    def get_deleted_by(self, obj):
        if not obj.deleted_by:
            return None
        return obj.deleted_by.get_full_name() or obj.deleted_by.username.capitalize()

    def validate_title(self, value):
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "Task title must contain at least 3 characters."
            )

        return value

    def validate(self, attrs):
        if self.instance and "status" in attrs:
            current_status = self.instance.status
            new_status = attrs["status"]
            allowed_statuses = self.ALLOWED_TRANSITIONS.get(
                current_status,
                set(),
            )

            if new_status not in allowed_statuses:
                raise serializers.ValidationError({
                    "status": (
                        f"Cannot change status from '{current_status}' to '{new_status}'."
                    )
                })

        project = (
            attrs.get("project")
            or (self.instance.project if self.instance else None)
        )
        assignee = attrs.get("assignee")

        if assignee is not None and project is not None:
            is_member = (
                ProjectMembership.objects
                .filter(
                    project=project,
                    user=assignee,
                )
                .exists()
            )

            if not is_member:
                raise serializers.ValidationError({
                    "assignee": (
                        "Assignee must be a member of the project."
                    )
                })

        status = attrs.get(
            "status",
            getattr(
                self.instance,
                "status",
                Task.Status.TODO,
            ),
        )

        attrs["completed"] = (status == Task.Status.DONE)

        return attrs

    def create(self, validated_data):
        status = validated_data.get(
            "status",
            Task.Status.TODO,
        )

        validated_data["completed"] = (
            status == Task.Status.DONE
        )

        task = super().create(validated_data)

        request = self.context.get("request")
        user = request.user if request and hasattr(request, "user") and request.user.is_authenticated else None

        TaskActivity.objects.create(
            task=task,
            user=user,
            action=TaskActivity.Action.CREATED,
            field="title",
            old_value=None,
            new_value=task.title,
        )

        return task

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = (
            request.user
            if request and hasattr(request, "user") and request.user.is_authenticated
            else None
        )

        from .services import (
            change_task_due_date,
            change_task_priority,
            change_task_status,
        )

        if "status" in validated_data:
            new_status = validated_data.pop("status")
            if new_status != instance.status:
                instance = change_task_status(
                    task=instance,
                    new_status=new_status,
                    user=user,
                )

        if "priority" in validated_data:
            new_priority = validated_data.pop("priority")
            if new_priority != instance.priority:
                instance = change_task_priority(
                    task=instance,
                    new_priority=new_priority,
                    user=user,
                )

        if "due_date" in validated_data:
            new_due_date = validated_data.pop("due_date")
            if new_due_date != instance.due_date:
                instance = change_task_due_date(
                    task=instance,
                    new_due_date=new_due_date,
                    user=user,
                )

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if validated_data:
            instance.save()

        return instance


class TaskActivitySerializer(
    serializers.ModelSerializer
):
    user = serializers.SerializerMethodField()
    task_title = serializers.CharField(
        source="task.title",
        read_only=True,
    )

    class Meta:
        model = TaskActivity

        fields = [
            "id",
            "task",
            "task_title",
            "user",
            "action",
            "field",
            "old_value",
            "new_value",
            "created_at",
        ]

        read_only_fields = fields

    def get_user(self, obj):
        if not obj.user:
            return None
        full_name = obj.user.get_full_name()
        if full_name:
            return full_name
        # Capitalize first letter of username for clean presentation (e.g. mizan -> Mizan)
        return obj.user.username.capitalize() if obj.user.username else None