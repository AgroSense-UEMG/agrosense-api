from django.db import models
from django.contrib.auth.models import AbstractUser

class InstitutionalDomain(models.Model):
    
    domain = models.CharField(max_length=255, unique=True) # Domain of the institution example: @uemg.br
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.domain

from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    # Add custom fields here if needed in the future
    
    def save(self, *args, **kwargs):
        if self.email:
            domain = self.email.split('@')[-1]
            if not InstitutionalDomain.objects.filter(domain=domain).exists():
                # Allow superusers to bypass this check (optional, but good for safety)
                if not self.is_superuser:
                    raise ValidationError(f"The domain @{domain} is not allowed.")
        super().save(*args, **kwargs)