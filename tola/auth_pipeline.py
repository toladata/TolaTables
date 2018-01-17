from silo.models import TolaUser, Country, Organization


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
        del remote_org['url']
        del remote_org['industry']  # ignore for now
        del remote_org['sector']  # ignore for now
        organization, org_created = Organization.objects.update_or_create(
                remote_org, organization_uuid=remote_org['organization_uuid'])

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
