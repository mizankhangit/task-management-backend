from channels.db import database_sync_to_async
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
)

from apps.projects.models import (
    ProjectMembership,
)


class ProjectConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):

        user = self.scope.get("user")

        if (
            not user
            or user.is_anonymous
        ):
            await self.close(
                code=4001
            )
            return

        project_id = (
            self.scope["url_route"]
            ["kwargs"]
            ["project_id"]
        )

        has_access = (
            await self.user_can_access_project(
                user.id,
                project_id,
            )
        )

        if not has_access:
            await self.close(
                code=4003
            )
            return

        self.project_id = project_id

        self.group_name = (
            f"project_{project_id}"
        )

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        await self.send_json({
            "type": "connection_established",
            "project_id": int(
                project_id
            ),
        })

    async def disconnect(
        self,
        close_code,
    ):

        if hasattr(
            self,
            "group_name",
        ):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def task_event(
        self,
        event,
    ):
        await self.send_json(
            event["data"]
        )

    @database_sync_to_async
    def user_can_access_project(
        self,
        user_id,
        project_id,
    ):
        from apps.projects.models import Project, ProjectMembership
        return (
            ProjectMembership.objects
            .filter(
                project_id=project_id,
                user_id=user_id,
            )
            .exists()
            or Project.objects.filter(
                id=project_id,
                owner_id=user_id,
            ).exists()
        )