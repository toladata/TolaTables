from uuid import uuid4

from django.contrib.auth.models import User
from social_core.utils import slugify, module_member

from silo.models import TolaUser, Country, Organization

USER_FIELDS = ['username', 'email']


def get_or_create_user(strategy, details, backend, user=None, *args, **kwargs):
    if 'username' not in backend.setting('USER_FIELDS', USER_FIELDS):
        return
    storage = strategy.storage

    if not user:
        email_as_username = strategy.setting('USERNAME_IS_FULL_EMAIL', False)
        uuid_length = strategy.setting('UUID_LENGTH', 16)
        max_length = storage.user.username_max_length()
        do_slugify = strategy.setting('SLUGIFY_USERNAMES', False)
        do_clean = strategy.setting('CLEAN_USERNAMES', True)

        if do_clean:
            override_clean = strategy.setting('CLEAN_USERNAME_FUNCTION')
            if override_clean:
                clean_func = module_member(override_clean)
            else:
                clean_func = storage.user.clean_username
        else:
            clean_func = lambda val: val

        if do_slugify:
            override_slug = strategy.setting('SLUGIFY_FUNCTION')
            if override_slug:
                slug_func = module_member(override_slug)
            else:
                slug_func = slugify
        else:
            slug_func = lambda val: val

        if email_as_username and details.get('email'):
            username = details['email']
        elif details.get('username'):
            username = details['username']
        else:
            username = uuid4().hex

        short_username = (username[:max_length - uuid_length]
                          if max_length is not None
                          else username)
        final_username = slug_func(clean_func(username[:max_length]))

        if not final_username:
            username = short_username + uuid4().hex[:uuid_length]
            final_username = slug_func(clean_func(username[:max_length]))

        fields = dict((name, kwargs.get(name, details.get(name)))
                      for name in backend.setting('USER_FIELDS', USER_FIELDS))
        if not fields:
            return

        user, user_created = User.objects.get_or_create(
            fields, username=final_username)
        return {
            'is_new': user_created,
            'user': user
        }

    return {'is_new': False}


def user_to_tola(backend, user, response, *args, **kwargs):
    # Only import fields to Tables that are required
    if response.get('tola_user'):
        remote_user = response.get('tola_user')
        remote_org = response.get('organization')
        tola_user_fields = {
            'tola_user_uuid': remote_user['tola_user_uuid'],
            'name': remote_user['name'],
            'employee_number': remote_user['employee_number'],
            'title': remote_user['title'],
            'privacy_disclaimer_accepted':
                remote_user['privacy_disclaimer_accepted']
        }

        data_org = {
            'organization_uuid': remote_org['organization_uuid'],
            'name': remote_org['name'],
            'description': remote_org.get('description'),
            'organization_url': remote_org.get('organization_url'),
            'level_1_label': remote_org.get('level_1_label', ''),
            'level_2_label': remote_org.get('level_2_label', ''),
            'level_3_label': remote_org.get('level_3_label', ''),
            'level_4_label': remote_org.get('level_4_label', '')
        }

        organization, org_created = Organization.objects.update_or_create(
            data_org, organization_uuid=data_org['organization_uuid'])

        tola_user_fields['organization'] = organization

        TolaUser.objects.update_or_create(tola_user_fields, user=user)
    else:
        userprofile, created = TolaUser.objects.get_or_create(user=user)
        if created:
            default_country = Country.objects.first()
            default_organization = Organization.objects.first()
            userprofile.country = default_country
            userprofile.organization = default_organization
            userprofile.name = response.get('displayName')
            userprofile.email = response.get('emails["value"]')
            userprofile.save()
