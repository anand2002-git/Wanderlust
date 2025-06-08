from django.contrib import admin
from .models import *

class PackageImageInline(admin.TabularInline):
    model = PackageImage
    extra = 1

class TourPackageAdmin(admin.ModelAdmin):
    list_display = ('title', 'vendor', 'destination', 'price', 'is_approved', 'is_active')
    list_filter = ('is_approved', 'is_active', 'category', 'destination')
    search_fields = ('title', 'description', 'destination__name')
    inlines = [PackageImageInline]
    actions = ['approve_packages']

    def approve_packages(self, request, queryset):
        queryset.update(is_approved=True)
    approve_packages.short_description = "Approve selected packages"

admin.site.register(User)
admin.site.register(Destination)
admin.site.register(TourPackage, TourPackageAdmin)
admin.site.register(Booking)