from django.db import transaction
from django.utils import timezone

from apps.tasks.models import Task, TaskActivity

@transaction.atomic
def change_task_status(*, task, new_status, user):
    old_status = task.status

    if old_status == new_status:
        return task

    task.status = new_status
    task.completed = (
        new_status == Task.Status.DONE
    )

    task.save(
        update_fields=[
            "status",
            "completed",
            "updated_at",
        ]
    )

    TaskActivity.objects.create(
        task=task,
        user=user,
        action=(
            TaskActivity.Action.STATUS_CHANGED
        ),
        field="status",
        old_value=old_status,
        new_value=new_status,
    )

    return task

@transaction.atomic
def change_task_priority(
    *,
    task,
    new_priority,
    user,
):
    old_priority = task.priority

    if old_priority == new_priority:
        return task

    task.priority = new_priority

    task.save(
        update_fields=[
            "priority",
            "updated_at",
        ]
    )

    TaskActivity.objects.create(
        task=task,
        user=user,
        action=(
            TaskActivity.Action
            .PRIORITY_CHANGED
        ),
        field="priority",
        old_value=old_priority,
        new_value=new_priority,
    )

    return task

@transaction.atomic
def change_task_due_date(
    *,
    task,
    new_due_date,
    user,
):
    old_due_date = task.due_date

    if old_due_date == new_due_date:
        return task

    task.due_date = new_due_date

    task.save(
        update_fields=[
            "due_date",
            "updated_at",
        ]
    )

    TaskActivity.objects.create(
        task=task,
        user=user,
        action=(
            TaskActivity.Action
            .DUE_DATE_CHANGED
        ),
        field="due_date",
        old_value=(
            old_due_date.isoformat()
            if old_due_date
            else None
        ),
        new_value=(
            new_due_date.isoformat()
            if new_due_date
            else None
        ),
    )

    return task

@transaction.atomic
def soft_delete_task(*, task, user):
    task.is_deleted = True
    task.deleted_at = timezone.now()
    task.deleted_by = user

    task.save(
        update_fields=[
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "updated_at",
        ]
    )

    TaskActivity.objects.create(
        task=task,
        user=user,
        action=TaskActivity.Action.DELETED,
        field="is_deleted",
        old_value=False,
        new_value=True,
    )

    return task

@transaction.atomic
def restore_task(*, task, user):
    task.is_deleted = False
    task.deleted_at = None
    task.deleted_by = None

    task.save(
        update_fields=[
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "updated_at",
        ]
    )

    TaskActivity.objects.create(
        task=task,
        user=user,
        action=TaskActivity.Action.RESTORED,
        field="is_deleted",
        old_value=True,
        new_value=False,
    )

    return task