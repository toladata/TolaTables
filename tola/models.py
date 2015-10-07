from django.db import models
from django.contrib import admin
from django.conf import settings
from datetime import datetime

# collect feedback from users
class Feedback(models.Model):
    submitter = models.ForeignKey(settings.AUTH_USER_MODEL)
    note = models.TextField()
    page = models.CharField(max_length=135)
    severity = models.CharField(max_length=135)
    create_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('create_date',)

    def save(self):
        if self.create_date is None:
            self.create_date = datetime.now()
        super(Feedback, self).save()

    def __unicode__(self):
        return unicode(self.submitter)


class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('submitter', 'note', 'page', 'severity', 'create_date',)
    display = 'Feedback'