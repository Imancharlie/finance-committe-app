from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class Member(models.Model):
    name = models.CharField(max_length=200)

    pledge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('70000.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    paid_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    course = models.CharField(max_length=100, blank=True, null=True)
    year = models.CharField(max_length=20, blank=True, null=True)

    is_active = models.BooleanField(default=True)  # <-- Newly added field

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def remaining(self):
        return self.pledge - self.paid_total

    @property
    def is_complete(self):
        return self.paid_total >= self.pledge

    @property
    def is_incomplete(self):
        return 0 < self.paid_total < self.pledge

    @property
    def not_started(self):
        return self.paid_total == 0

    @property
    def has_exceeded(self):
        return self.paid_total > self.pledge

    @property
    def status_display(self):
        if self.has_exceeded:
            return "Exceeded"
        elif self.is_complete:
            return "Complete"
        elif self.is_incomplete:
            return "Incomplete"
        else:
            return "Not Started"

    def update_paid_total(self):
        total = self.transaction_set.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.paid_total = total
        self.save(update_fields=['paid_total', 'updated_at'])


class Transaction(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date = models.DateField()
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.member.name} - {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        """Override save to update member's paid_total"""
        super().save(*args, **kwargs)
        self.member.update_paid_total()

    def delete(self, *args, **kwargs):
        """Override delete to update member's paid_total"""
        super().delete(*args, **kwargs)
        self.member.update_paid_total()
