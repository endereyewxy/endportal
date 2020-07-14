from django.db import models


class Blog(models.Model):
    publish_date = models.DateField()
    publish_desc = models.CharField(max_length=64)
    content_name = models.CharField(max_length=64)
    content_type = models.CharField(max_length=16)
    content_imgs = models.TextField()
    content_tags = models.TextField()
    content_desc = models.TextField()
    content_text = models.TextField()
