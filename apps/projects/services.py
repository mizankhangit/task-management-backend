from datetime import timedelta
import secrets
from django.db import transaction
from django.utils import timezone

from .models import (
    ProjectInvitation,
    ProjectMembership,
)

def generate_invitation_token():
    return secrets.token_urlsafe(48)

def create_project_invitation(
    *,
    project,
    email,
    role,
    invited_by,
):
    token = generate_invitation_token()

    expires_at = (
        timezone.now()
        + timedelta(days=7)
    )

    invitation = (
        ProjectInvitation.objects.create(
            project=project,
            email=email.lower().strip(),
            role=role,
            token=token,
            invited_by=invited_by,
            expires_at=expires_at,
        )
    )

    return invitation


@transaction.atomic
def accept_project_invitation(*,token, user):
    invitation = (
        ProjectInvitation.objects
        .select_for_update()
        .select_related("project")
        .filter(
            token=token,
        )
        .first()
    )

    if invitation is None:
        raise ValueError(
            "Invalid invitation."
        )

    if invitation.status != (
        ProjectInvitation.Status.PENDING
    ):
        raise ValueError(
            "This invitation is no longer active."
        )

    if invitation.expires_at <= timezone.now():
        raise ValueError(
            "This invitation has expired."
        )

    if user.email.lower() != (
        invitation.email.lower()
    ):
        raise ValueError(
            "This invitation was sent "
            "to a different email address."
        )

    membership, created = (
        ProjectMembership.objects.get_or_create(
            project=invitation.project,
            user=user,
            defaults={
                "role": invitation.role,
            },
        )
    )

    if not created:
        raise ValueError(
            "You are already a member "
            "of this project."
        )

    invitation.status = (
        ProjectInvitation.Status.ACCEPTED
    )

    invitation.accepted_at = timezone.now()

    invitation.save(
        update_fields=[
            "status",
            "accepted_at",
        ]
    )

    return membership