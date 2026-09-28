from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User

from .models import Notification


def create_notification(
    *,
    recipient,
    notification_type,
    title,
    message,
    task=None,
    project=None,
):
    if not recipient:
        return None

    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        task=task,
        project=project,
    )

    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(
                channel_layer.group_send
            )(
                f"user_{recipient.id}",
                {
                    "type": "notification_message",
                    "data": {
                        "id": notification.id,
                        "notification_type": (
                            notification.notification_type
                        ),
                        "title": notification.title,
                        "message": notification.message,
                        "task": notification.task_id,
                        "project": (
                            notification.project_id
                        ),
                        "is_read": notification.is_read,
                        "created_at": (
                            notification.created_at.isoformat()
                        ),
                    },
                },
            )
    except Exception:
        # Gracefully handle channel layer issues without failing DB write
        pass

    return notification


def notify_task_assigned(*, task, actor=None):
    """
    Notify the assignee when they are assigned to a task.
    Do not notify if the assignee is the actor making the assignment.
    """
    if not task.assignee:
        return None

    if actor and task.assignee_id == actor.id:
        return None

    actor_name = actor.username if actor else "A team member"
    project_name = task.project.name if task.project else "your project"

    return create_notification(
        recipient=task.assignee,
        notification_type=Notification.NotificationType.TASK_ASSIGNED,
        title=f"Task assigned: {task.title}",
        message=f"{actor_name} assigned you to '{task.title}' in {project_name}.",
        task=task,
        project=task.project,
    )


def notify_task_status_changed(*, task, new_status, actor=None):
    """
    Notify the task assignee and/or project owner when status changes.
    """
    actor_name = actor.username if actor else "A team member"
    status_label = dict(task.Status.choices).get(new_status, new_status)

    recipients = set()
    if task.assignee and (not actor or task.assignee_id != actor.id):
        recipients.add(task.assignee)

    if task.project and task.project.owner:
        owner = task.project.owner
        if (not actor or owner.id != actor.id) and (not task.assignee or owner.id != task.assignee_id):
            recipients.add(owner)

    notifications = []
    for recipient in recipients:
        notifications.append(
            create_notification(
                recipient=recipient,
                notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
                title=f"Task status updated: {task.title}",
                message=f"{actor_name} moved task '{task.title}' to {status_label}.",
                task=task,
                project=task.project,
            )
        )
    return notifications


def notify_project_invitation(*, project, email, role, invited_by):
    """
    If the invited email belongs to a registered user, send an in-app notification.
    """
    target_user = User.objects.filter(email__iexact=email).first()
    if not target_user or (invited_by and target_user.id == invited_by.id):
        return None

    role_label = role.capitalize() if role else "Member"
    actor_name = invited_by.username if invited_by else "Someone"

    return create_notification(
        recipient=target_user,
        notification_type=Notification.NotificationType.PROJECT_INVITATION,
        title=f"Invitation to join {project.name}",
        message=f"{actor_name} invited you to join '{project.name}' as {role_label}.",
        project=project,
    )


def notify_member_added(*, project, user, actor=None, role=None):
    """
    Notify the user when they are added to a project, or notify the project owner when an invited user joins.
    """
    if not user:
        return None

    role_label = role.capitalize() if role else "Member"
    actor_name = actor.username if actor else "An admin"

    if actor and user.id != actor.id:
        return create_notification(
            recipient=user,
            notification_type=Notification.NotificationType.MEMBER_ADDED,
            title=f"Added to project: {project.name}",
            message=f"{actor_name} added you to '{project.name}' as {role_label}.",
            project=project,
        )

    if project.owner and project.owner_id != user.id:
        return create_notification(
            recipient=project.owner,
            notification_type=Notification.NotificationType.MEMBER_ADDED,
            title=f"New member in {project.name}",
            message=f"{user.username} joined '{project.name}' as {role_label}.",
            project=project,
        )

    return None


def notify_task_commented(*, task, actor, comment_text=""):
    """
    Notify the task assignee and project owner when a comment is added to a task.
    """
    actor_name = actor.username if actor else "Someone"
    recipients = set()

    if task.assignee and (not actor or task.assignee_id != actor.id):
        recipients.add(task.assignee)

    if task.project and task.project.owner:
        owner = task.project.owner
        if (not actor or owner.id != actor.id) and (not task.assignee or owner.id != task.assignee_id):
            recipients.add(owner)

    notifications = []
    snippet = f": \"{comment_text[:50]}...\"" if comment_text else "."
    for recipient in recipients:
        notifications.append(
            create_notification(
                recipient=recipient,
                notification_type=Notification.NotificationType.TASK_COMMENTED,
                title=f"New comment on {task.title}",
                message=f"{actor_name} commented on '{task.title}'{snippet}",
                task=task,
                project=task.project,
            )
        )
    return notifications