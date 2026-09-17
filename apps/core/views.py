from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import HealthCheck


# Create your views here.
@api_view(["GET"])
def health_check(request):
    health_check_record = HealthCheck.objects.create(
        message="API is connected to PostgreSQL"
    )

    return Response({
        "status": "success",
        "message": health_check_record.message,
        "id": health_check_record.id,
        "created_at": health_check_record.created_at,
    })
    