from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import *
from .widgets import MultipleFileInput,MultipleFileField
from django.utils import timezone

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class VendorRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)
    company_name = forms.CharField(max_length=100, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'company_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_vendor = True
        user.is_customer = False
        if commit:
            user.save()
        return user

class PackageForm(forms.ModelForm):
    additional_images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        label='Additional Images',
        help_text='Select multiple images (JPEG, PNG, etc.)'
    )
    
    # ... rest of your form class ...
    class Meta:
        model = TourPackage
        fields = ['title', 'destination', 'description', 'price', 'duration_days', 
                 'category', 'featured_image', 'expiry_date', 'max_persons', 
                 'inclusions', 'is_approved']
        widgets = {
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'min': timezone.now().strftime('%Y-%m-%d')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and not self.user.is_superuser:
            self.fields['is_approved'].disabled = True
            self.fields['is_approved'].initial = False
    
    def save(self, commit=True):
        package = super().save(commit=False)
        if self.user:
            package.vendor = self.user
            package.is_approved = self.user.is_superuser
        
        if commit:
            package.save()
            
            # Handle additional images
            if 'additional_images' in self.files:
                for image in self.files.getlist('additional_images'):
                    PackageImage.objects.create(package=package, image=image)
        
        return package
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['travel_date', 'persons', 'special_requests']
        widgets = {
            'travel_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'persons': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'special_requests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any special requests...'
            }),
        }
    
    def clean_travel_date(self):
        travel_date = self.cleaned_data.get('travel_date')
        if travel_date < timezone.now().date():
            raise forms.ValidationError("Travel date must be in the future.")
        return travel_date
    
    def clean_persons(self):
        persons = self.cleaned_data.get('persons')
        if persons < 1:
            raise forms.ValidationError("Number of persons must be at least 1.")
        return persons

class UserProfileUpdateForm(UserChangeForm):
    password = None
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Your address...'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 
                 'profile_picture', 'bio']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Tell us about yourself...'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Your address...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the password help text
        self.fields['username'].help_text = None
class UserLoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })