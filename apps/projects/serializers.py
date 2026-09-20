from rest_framework import serializers

from .models import (
    Project,
    ProjectMembership,
    ProjectInvitation,
)

from django.utils import timezone

class ProjectMembershipSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )
    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = ProjectMembership
        fields = [
            "id",
            "project",
            "project_name",
            "user",
            "username",
            "email",
            "role",
            "joined_at",
        ]

        read_only_fields = [
            "id",
            "project_name",
            "username",
            "email",
            "joined_at",
        ]

    def validate_role(self, value):
        if value == ProjectMembership.Role.OWNER:
            raise serializers.ValidationError("Owner role cannot be assigned to members.")
        return value

    def validate(self, attrs):
        project = attrs.get("project") or (self.instance.project if self.instance else None)
        user = attrs.get("user") or (self.instance.user if self.instance else None)

        if project and user and project.owner_id == user.id:
            raise serializers.ValidationError({
                "user": "Project owner already has full owner access to this project."
            })

        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(
        source="owner.username"
    )
    current_user_role = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()

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
            "current_user_role",
            "user_permissions",
            "tasks_count",
            "completed_tasks_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "owner",
            "current_user_role",
            "user_permissions",
            "tasks_count",
            "completed_tasks_count",
            "created_at",
            "updated_at",
        ]

    def get_current_user_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None
        if obj.owner_id == request.user.id:
            return ProjectMembership.Role.OWNER
        membership = ProjectMembership.objects.filter(project=obj, user=request.user).first()
        return membership.role if membership else None

    def get_user_permissions(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None
        from .permissions import user_has_permission, ProjectPermission
        user = request.user
        return {
            "can_view": user_has_permission(obj, user, ProjectPermission.VIEW),
            "can_create_task": user_has_permission(obj, user, ProjectPermission.CREATE_TASK),
            "can_edit_task": user_has_permission(obj, user, ProjectPermission.EDIT_TASK),
            "can_delete_task": user_has_permission(obj, user, ProjectPermission.DELETE_TASK),
            "can_assign_task": user_has_permission(obj, user, ProjectPermission.ASSIGN_TASK),
            "can_manage_members": user_has_permission(obj, user, ProjectPermission.MANAGE_MEMBERS),
            "can_change_roles": user_has_permission(obj, user, ProjectPermission.CHANGE_ROLES),
            "can_delete_project": user_has_permission(obj, user, ProjectPermission.DELETE_PROJECT),
        }

class ProjectInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectInvitation
        fields = [
            "id",
            "email",
            "role",
            "status",
            "expires_at",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "expires_at",
            "created_at",
        ]

class CreateProjectInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    role = serializers.ChoiceField(
        choices=[
            ProjectMembership.Role.ADMIN,
            ProjectMembership.Role.MEMBER,
            ProjectMembership.Role.VIEWER,
        ]
    )

    def validate(self, attrs):
        project = self.context["project"]

        email = (
            attrs["email"]
            .strip()
            .lower()
        )

        already_member = (
            ProjectMembership.objects
            .filter(
                project=project,
                user__email__iexact=email,
            )
            .exists()
        )

        if already_member:
            raise serializers.ValidationError({
                "email": (
                    "This user is already "
                    "a project member."
                )
            })

        pending_invitation = (
            ProjectInvitation.objects
            .filter(
                project=project,
                email__iexact=email,
                status=(
                    ProjectInvitation.Status.PENDING
                ),
                expires_at__gt=timezone.now(),
            )
            .exists()
        )

        if pending_invitation:
            raise serializers.ValidationError({
                "email": (
                    "An invitation to this user "
                    "is already pending."
                )
            })

        return attrs
        
class AcceptInvitationSerializer(
    serializers.Serializer
):
    token = serializers.CharField(
        min_length=20,
        max_length=128,
    )
        