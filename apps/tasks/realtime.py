from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import TaskSerializer


def publish_task_event(
    *,
    task,
    event_type,
):
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        data = {
            "type": event_type,
            "project_id": task.project_id,
            "task": TaskSerializer(
                task
            ).data,
        }

        async_to_sync(
            channel_layer.group_send
        )(
            f"project_{task.project_id}",
            {
                "type": "task_event",
                "data": data,
            },
        )
    except Exception:
        pass