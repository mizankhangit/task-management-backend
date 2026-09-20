from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_project_invitation_email(
    invitation,
):
    invitation_url = (
        f"{settings.FRONTEND_URL}"
        f"/invitations/accept"
        f"?token={invitation.token}"
    )

    context = {
        "project": invitation.project,
        "invited_by": invitation.invited_by.username,
        "role": invitation.role,
        "invitation_url": invitation_url,
        "expires_at": invitation.expires_at,
    }

    html_content = render_to_string(
        "emails/project_invitation.html",
        context,
    )

    subject = (
        f"You're invited to join "
        f"{invitation.project.name}"
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=(
            f"You've been invited to join "
            f"{invitation.project.name}.\n\n"
            f"Accept here: {invitation_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invitation.email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send()