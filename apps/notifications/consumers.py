from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(
    AsyncJsonWebsocketConsumer
):

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

        self.user = user

        self.group_name = (
            f"user_{user.id}"
        )

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        await self.send_json({
            "type": "connection_established",
            "message": (
                "WebSocket connection established."
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

    async def notification_message(
        self,
        event,
    ):

        await self.send_json(
            event["data"]
        )