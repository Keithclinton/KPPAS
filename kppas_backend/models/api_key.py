import secrets

from django.db import models


def _generate_key():
    return secrets.token_urlsafe(32)


class ApiKey(models.Model):
    """Issued by hand, one per licensee, after a request comes in through
    data_access_view's contact email -- there's no self-serve signup, the
    same manual-approval posture as every other gated workflow in this app
    (Gazette/Hansard entry, quarterly verification)."""
    label = models.CharField(max_length=200, help_text="Who this key is for, e.g. 'Nation Media Group research'")
    key = models.CharField(max_length=64, unique=True, default=_generate_key, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.label
