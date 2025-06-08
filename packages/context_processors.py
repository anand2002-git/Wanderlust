from django.conf import settings

def user_profile(request):
    if request.user.is_authenticated:
        return {
            'user_profile_picture': request.user.profile_picture.url if request.user.profile_picture else settings.STATIC_URL + 'images/default_profile.png'
        }
    return {}