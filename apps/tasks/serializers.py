from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):

    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

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
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "project_name",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "Task title must contain at least 3 characters."
            )

        return value

    def validate(self, attrs):
        completed = attrs.get(
            "completed",
            getattr(self.instance, "completed", False)
        )

        status = attrs.get(
            "status",
            getattr(
                self.instance,
                "status",
                Task.Status.TODO
            )
        )

        if completed and status != Task.Status.DONE:
            raise serializers.ValidationError({
                "completed": (
                    "A completed task must have status 'done'."
                )
            })

        return attrs