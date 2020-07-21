from datetime import datetime

from django.db import models
from ipware import get_client_ip


class Log(models.Model):
    src_user = models.IntegerField()
    src_addr = models.CharField(max_length=15)
    src_time = models.DateTimeField()
    category = models.CharField(max_length=4)
    behavior = models.CharField(max_length=8)
    detailed = models.TextField()

    @staticmethod
    def new_log(request, category, behavior='', detailed=''):
        ip, _ = get_client_ip(request)
        Log.objects.create(
            src_user=request.user.id if request.user.is_authenticated else 0,
            src_addr=ip,
            src_time=datetime.now(),
            category=category,
            behavior=behavior,
            detailed=detailed
        ).save()
