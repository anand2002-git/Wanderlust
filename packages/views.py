from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from .models import *
from .forms import *
from datetime import date
from django.contrib.auth import authenticate, login, logout
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import razorpay
import json
from django.core.paginator import Paginator

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def home(request):
    # All available packages (paginated)
    available_packages = TourPackage.objects.filter(
        is_approved=True,
        is_active=True,
        expiry_date__gte=timezone.now().date()
    ).order_by('-created_at')
    
    paginator = Paginator(available_packages, 6)  # Show 6 packages per page
    page_number = request.GET.get('page')
    available_packages = paginator.get_page(page_number)
    
    # Popular packages based on booking count
    popular_packages = TourPackage.objects.filter(
        is_approved=True,
        is_active=True,
        expiry_date__gte=timezone.now().date()
    ).annotate(
        booking_count=models.Count('bookings')
    ).order_by('-booking_count')[:6]
    
    context = {
        'available_packages': available_packages,
        'popular_packages': popular_packages,
    }
    return render(request, 'packages/home.html', context)

def about(request):
    context = {
        'company_name': 'WANDERLUST',
        'tagline': 'Roam Beyond Boundaries',
        'description': 'WANDERLUST is a premier travel company dedicated to crafting unforgettable adventures.',
        'mission': 'To inspire and empower travelers to explore the world with curiosity and respect.',
        'founded': '2025',
    }
    return render(request, 'packages/about.html', context)

def register(request):
    if request.user.is_authenticated:
        return redirect('packages:home')
        
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome {user.username}!')
            return redirect('packages:home')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def vendor_register(request):
    if request.user.is_authenticated:
        return redirect('packages:home')
        
    if request.method == 'POST':
        form = VendorRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_vendor = True
            user.is_customer = False
            user.save()
            login(request, user)
            messages.success(request, f'Vendor account created successfully! Welcome {user.username}!')
            return redirect('packages:vendor_dashboard')
    else:
        form = VendorRegisterForm()
    return render(request, 'accounts/vendor_register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('packages:home')
        
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                remember_me = form.cleaned_data.get('remember_me')
                
                if not remember_me:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(86400 * 30)  # 30 days
                
                messages.success(request, f"Welcome back, {username}!")
                return redirect('packages:home')
        messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('packages:home')

def package_list(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    destination_id = request.GET.get('destination')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    packages = TourPackage.objects.filter(
        Q(is_approved=True) | Q(vendor=request.user) if request.user.is_authenticated else Q(is_approved=True),
        is_active=True,
        expiry_date__gte=timezone.now().date()
    )
    
    if query:
        packages = packages.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(destination__icontains=query)
        )
    
    if category:
        packages = packages.filter(category=category)
    
    if destination_id:
        try:
            destination = Destination.objects.get(id=destination_id)
            packages = packages.filter(destination__icontains=destination.name)
        except Destination.DoesNotExist:
            pass
    
    if min_price:
        packages = packages.filter(price__gte=min_price)
    
    if max_price:
        packages = packages.filter(price__lte=max_price)
    
    destinations = Destination.objects.all()
    
    context = {
        'packages': packages,
        'destinations': destinations,
        'search_query': query or '',
        'selected_category': category or '',
        'selected_destination': destination_id or '',
    }
    return render(request, 'packages/package_list.html', context)

def package_detail(request, pk):
    try:
        package = get_object_or_404(TourPackage, pk=pk)
        
        if not package.can_be_booked and not (request.user.is_superuser or request.user == package.vendor):
            messages.error(request, "This package is not available for booking.")
            return redirect('packages:home')
            
        if request.method == 'POST':
            if not request.user.is_authenticated:
                messages.warning(request, 'Please login to book this package.')
                return redirect('packages:login')
            
            form = BookingForm(request.POST)
            if form.is_valid():
                booking = form.save(commit=False)
                booking.user = request.user
                booking.package = package
                booking.total_price = package.price * booking.persons
                booking.is_vendor_booking = request.user.is_vendor
                
                # For vendor bookings, mark as confirmed without payment
                if request.user.is_vendor and request.user == package.vendor:
                    booking.status = 'CF'  # Confirmed
                    booking.payment_status = 'PC'  # Payment Completed
                    booking.save()
                    messages.success(request, 'Vendor booking confirmed successfully!')
                    return redirect('packages:profile')
                
                # For regular users, proceed to payment
                booking.save()
                
                # Create Razorpay order
                currency = 'INR'
                amount = int(booking.total_price * 100)  # Razorpay expects amount in paise
                
                razorpay_order = client.order.create({
                    'amount': amount,
                    'currency': currency,
                    'payment_capture': '1'  # Auto-capture payment
                })
                
                booking.razorpay_order_id = razorpay_order['id']
                booking.save()
                
                context = {
                    'booking': booking,
                    'package': package,
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'razorpay_order_id': razorpay_order['id'],
                    'amount': amount,
                    'currency': currency,
                    'callback_url': request.build_absolute_uri('/payment/success/'),
                    'user': {
                        'name': request.user.get_full_name() or request.user.username,
                        'email': request.user.email,
                        'contact': request.user.phone or '9999999999'
                    }
                }
                
                return render(request, 'packages/payment.html', context)
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            form = BookingForm(initial={'travel_date': date.today()})
        
        similar_packages = TourPackage.objects.filter(
            destination=package.destination,
            is_active=True,
            expiry_date__gte=timezone.now().date()
        ).exclude(pk=pk)[:4]
        
        context = {
            'package': package,
            'form': form,
            'similar_packages': similar_packages,
            'can_book': package.can_be_booked,
            'today': date.today().strftime('%Y-%m-%d')
        }
        return render(request, 'packages/package_detail.html', context)
        
    except Http404:
        messages.error(request, "The requested package does not exist.")
        return redirect('packages:home')

@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        try:
            # Get the payment details from POST data
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            
            # Verify the payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            try:
                client.utility.verify_payment_signature(params_dict)
                
                # Signature verification successful
                booking = Booking.objects.get(razorpay_order_id=razorpay_order_id)
                booking.razorpay_payment_id = razorpay_payment_id
                booking.razorpay_signature = razorpay_signature
                booking.payment_status = 'PC'  # Payment Completed
                booking.status = 'CF'  # Confirmed
                booking.save()
                
                messages.success(request, 'Payment successful! Your booking is confirmed.')
                return redirect('packages:profile')
                
            except Exception as e:
                # Signature verification failed
                messages.error(request, 'Payment verification failed. Please contact support.')
                return redirect('packages:profile')
                
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('packages:profile')
    
    return redirect('packages:home')

# ... [previous code remains unchanged above]

@login_required
def add_package(request):
    if not request.user.is_vendor and not request.user.is_superuser:
        messages.error(request, "Only vendors can add packages.")
        return redirect('packages:home')
    
    if request.method == 'POST':
        form = PackageForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            package = form.save(commit=False)
            package.vendor = request.user
            package.is_approved = request.user.is_superuser
            package.save()
            
            # Handle additional images
            if 'additional_images' in request.FILES:
                for image in request.FILES.getlist('additional_images'):
                    PackageImage.objects.create(package=package, image=image)
            
            messages.success(request, 'Package created successfully!')
            return redirect('packages:package_detail', pk=package.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PackageForm(user=request.user)
    
    return render(request, 'packages/add_package.html', {
        'form': form,
        'today': timezone.now().strftime('%Y-%m-%d')
    })
@login_required
def edit_package(request, pk):
    package = get_object_or_404(TourPackage, pk=pk, vendor=request.user)
    
    if request.method == 'POST':
        form = PackageForm(request.POST, request.FILES, instance=package, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Package updated successfully!')
            return redirect('packages:package_detail', pk=package.id)
    else:
        form = PackageForm(instance=package, user=request.user)
    
    return render(request, 'packages/edit_package.html', {'form': form, 'package': package})

@login_required
def delete_package(request, pk):
    package = get_object_or_404(TourPackage, pk=pk, vendor=request.user)
    
    if request.method == 'POST':
        package.delete()
        messages.success(request, 'Package deleted successfully!')
        return redirect('packages:vendor_dashboard')
    
    return render(request, 'packages/confirm_delete.html', {'package': package})

@login_required
def vendor_dashboard(request):
    if not request.user.is_vendor:
        return redirect('packages:home')
    
    packages = TourPackage.objects.filter(vendor=request.user)
    approved_packages_count = packages.filter(is_approved=True).count()
    bookings = Booking.objects.filter(package__vendor=request.user).order_by('-booking_date')
    
    context = {
        'packages': packages,
        'approved_packages_count': approved_packages_count,
        'bookings': bookings,
    }
    return render(request, 'packages/vendor_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    packages_for_approval = TourPackage.objects.filter(is_approved=False)
    recent_bookings = Booking.objects.all().order_by('-booking_date')[:10]
    vendors = User.objects.filter(is_vendor=True)
    
    context = {
        'packages_for_approval': packages_for_approval,
        'recent_bookings': recent_bookings,
        'vendors': vendors,
    }
    return render(request, 'packages/admin_dashboard.html', context)

@login_required
def profile(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    return render(request, 'accounts/profile.html', {'bookings': bookings})

@login_required
def profile_update(request):
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('packages:profile')
    else:
        form = UserProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_update.html', {'form': form})
@login_required
@require_POST
def book_package(request, pk):
    package = get_object_or_404(TourPackage, pk=pk)
    
    if not package.can_be_booked:
        messages.error(request, "This package is no longer available for booking.")
        return redirect('packages:package_detail', pk=pk)
    
    if request.user.is_vendor and request.user == package.vendor:
        messages.error(request, "You cannot book your own package.")
        return redirect('packages:package_detail', pk=pk)
    
    try:
        travel_date = request.POST.get('travel_date')
        persons = int(request.POST.get('persons'))
        special_requests = request.POST.get('special_requests', '')
        
        if datetime.strptime(travel_date, '%Y-%m-%d').date() < timezone.now().date():
            messages.error(request, "Travel date must be in the future.")
            return redirect('packages:package_detail', pk=pk)
            
        if persons < 1:
            messages.error(request, "Number of persons must be at least 1.")
            return redirect('packages:package_detail', pk=pk)
            
        booking = Booking.objects.create(
            user=request.user,
            package=package,
            travel_date=travel_date,
            persons=persons,
            special_requests=special_requests,
            total_price=package.price * persons,
            is_vendor_booking=request.user.is_vendor
        )
        
        messages.success(request, "Booking successful!")
        return redirect('packages:profile')
        
    except Exception as e:
        messages.error(request, f"Error creating booking: {str(e)}")
        return redirect('packages:package_detail', pk=pk)

@login_required
@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status == 'PE':  # Only allow cancelling pending bookings
        booking.status = 'CA'  # CA for Cancelled
        booking.save()
        messages.success(request, 'Your booking has been cancelled successfully.')
    else:
        messages.error(request, 'Only pending bookings can be cancelled.')
    return redirect('packages:profile')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def approve_package(request, pk):
    package = get_object_or_404(TourPackage, pk=pk)
    package.is_approved = True
    package.save()
    messages.success(request, 'Package approved successfully!')
    return redirect('packages:admin_dashboard')