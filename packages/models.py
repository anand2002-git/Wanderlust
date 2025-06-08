# packages/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, FileExtensionValidator

class User(AbstractUser):
    is_vendor = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=True)
    phone = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    company_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    company_location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    specializations = models.CharField(max_length=200, blank=True)
    languages_spoken = models.CharField(max_length=200, blank=True)

    @property
    def profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/default_profile.png'

class Destination(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='destinations/')
    popular = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class TourPackage(models.Model):
    CATEGORY_CHOICES = [
        ('AD', 'Adventure'),
        ('CR', 'Cruise'),
        ('CU', 'Cultural'),
        ('BE', 'Beach'),
        ('HI', 'Hiking'),
    ]

    vendor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_vendor': True})
    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duration_days = models.PositiveIntegerField()
    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES)
    featured_image = models.ImageField(upload_to='packages/')
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    max_persons = models.PositiveIntegerField(default=1)
    inclusions = models.TextField(blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.vendor.is_superuser:
            self.is_approved = True
        if self.expiry_date < timezone.now().date():
            self.is_active = False
        super().save(*args, **kwargs)

    @property
    def can_be_booked(self):
        return self.is_active and (self.is_approved or self.vendor.is_superuser) and self.expiry_date >= timezone.now().date()

class PackageImage(models.Model):
    package = models.ForeignKey(TourPackage, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='package_images/')
    caption = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Image for {self.package.title}"

class Booking(models.Model):
    PENDING = 'PE'
    CONFIRMED = 'CF'
    CANCELLED = 'CA'
    COMPLETED = 'CO'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (CANCELLED, 'Cancelled'),
        (COMPLETED, 'Completed'),
    ]
    
    PAYMENT_PENDING = 'PP'
    PAYMENT_COMPLETED = 'PC'
    PAYMENT_FAILED = 'PF'
    PAYMENT_REFUNDED = 'PR'
    
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Payment Pending'),
        (PAYMENT_COMPLETED, 'Payment Completed'),
        (PAYMENT_FAILED, 'Payment Failed'),
        (PAYMENT_REFUNDED, 'Payment Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    package = models.ForeignKey(TourPackage, on_delete=models.PROTECT, related_name='bookings')
    booking_date = models.DateTimeField(auto_now_add=True)
    travel_date = models.DateField()
    persons = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default=PENDING)
    payment_status = models.CharField(max_length=2, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)
    special_requests = models.TextField(blank=True)
    is_vendor_booking = models.BooleanField(default=False)
    cancellation_date = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-booking_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['travel_date']),
        ]

    def __str__(self):
        return f"Booking #{self.id} - {self.package.title}"

    def save(self, *args, **kwargs):
        if not self.total_price or self.pk is None:
            self.total_price = self.package.price * self.persons
        
        if self.pk and self.status == self.CANCELLED:
            original = Booking.objects.get(pk=self.pk)
            if original.status != self.CANCELLED:
                self.cancellation_date = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status in [self.PENDING, self.CONFIRMED]

    @property
    def can_be_cancelled(self):
        return self.status == self.PENDING and self.payment_status != self.PAYMENT_REFUNDED