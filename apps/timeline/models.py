from django.db import models


class TimelineEvent(models.Model):
    date = models.DateField()
    event = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    supporting_docs = models.JSONField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.date}: {self.event}"