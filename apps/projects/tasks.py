from celery import shared_task
from django.db import transaction

from .email_service import (
    send_project_invitation_email,
)
from .models import ProjectInvitation

from django.utils import timezone


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={
        "max_retries": 5,
    },
)
def send_project_invitation_email_task(
    self,
    invitation_id,
):
    invitation = (
        ProjectInvitation.objects
        .select_related(
            "project",
            "invited_by",
        )
        .get(
            id=invitation_id,
        )
    )

    if invitation.email_sent_at:
        return

    invitation.email_send_attempts += 1

    invitation.save(
        update_fields=[
            "email_send_attempts",
        ]
    )

    try:
        send_project_invitation_email(
            invitation
        )

    except Exception as exc:
        invitation.email_last_error = str(exc)

        invitation.save(
            update_fields=[
                "email_last_error",
            ]
        )

        raise

    invitation.email_sent_at = timezone.now()
    invitation.email_last_error = ""

    invitation.save(
        update_fields=[
            "email_sent_at",
            "email_last_error",
        ]
    )

@shared_task
def cleanup_expired_invitations():
    now = timezone.now()

    updated = (
        ProjectInvitation.objects
        .filter(
            status=ProjectInvitation.Status.PENDING,
            expires_at__lte=now,
        )
        .update(
            status=ProjectInvitation.Status.REVOKED,
        )
    )

    return updated