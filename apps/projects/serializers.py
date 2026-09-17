from rest_framework import serializers

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(
        source="owner.username"
    )

    tasks_count = serializers.IntegerField(
        read_only=True,
        default=0,
    )
    completed_tasks_count = serializers.IntegerField(
        read_only=True,
        default=0,
    )

    class Meta:
        model = Project

        fields = [
            "id",
            "owner",
            "name",
            "description",
            "tasks_count",
            "completed_tasks_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "owner",
            "tasks_count",
            "completed_tasks_count",
            "created_at",
            "updated_at",
        ]