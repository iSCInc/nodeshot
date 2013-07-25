import requests
import simplejson as json
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from social_auth.models import UserSocialAuth

if settings.NODESHOT['SETTINGS'].get('PROFILE_EMAIL_CONFIRMATION', True):
    from emailconfirmation.models import EmailAddress


def load_extra_data(backend, details, response, uid, user, social_user=None,
                    *args, **kwargs):
    """Load extra data from provider and store it on current UserSocialAuth
    extra_data field.
    """
    social_user = social_user or \
                  UserSocialAuth.get_social_auth(backend.name, uid)
    
    emailaddress = EmailAddress(**{
        'user': user,
        'email': user.email,
        'verified': True,
        'primary': True
    })
    emailaddress.save()
    
    if social_user:
        extra_data = backend.extra_data(user, uid, response, details)
        if kwargs.get('original_email') and not 'email' in extra_data:
            extra_data['email'] = kwargs.get('original_email')
        if extra_data and social_user.extra_data != extra_data:
            if social_user.extra_data:
                social_user.extra_data.update(extra_data)
            else:
                social_user.extra_data = extra_data
            social_user.save()
        
        if backend.name == 'facebook':
            response = json.loads(requests.get('https://graph.facebook.com/%s?access_token=%s' % (extra_data['id'], extra_data['access_token'])).content)
            
            try:
                user.city, user.country = response.get('hometown').get('name').split(', ')
            except AttributeError:
                raise ImproperlyConfigured('facebook must return hometown info in response, add this permission to your facebook app')
            
            try:
                user.birth_date = datetime.strptime(response.get('birthday'), '%m/%d/%Y').date()
            except AttributeError:
                raise ImproperlyConfigured('facebook must return birthday info in response, add this permission to your facebook app')
            
            user.save()
        
        return {'social_user': social_user}