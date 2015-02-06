from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

from wagtail.wagtailcore.models import PageRevision, GroupPagePermission
from wagtail.wagtailusers.models import UserProfile

# The following will check to see if we can import task from celery - 
# if not then we definitely haven't installed it
try:
    from celery.decorators import task
    NO_CELERY = False
except:
    NO_CELERY = True

   
# However, we could have installed celery for other projects. So we will also
# check if we have defined the BROKER_URL setting. If not then definitely we
# haven't configured it. 
if NO_CELERY or not hasattr(settings, 'BROKER_URL'):
    # So if we enter here we will define a different "task" decorator that
    # just returns the original function and sets its delay attribute to
    # point to the original function: This way, the send_notification
    # function will be actually called instead of the the 
    # send_notification.delay() 
    def task(f):
        f.delay=f
        return f

class Email(object):
    def __init__(self, register_hook_name, construct_hook_name=None):
        self.register_hook_name = register_hook_name
        self.construct_hook_name = construct_hook_name
        # _registered_menu_items will be populated on first access to the
        # registered_menu_items property. We can't populate it in __init__ because
        # we can't rely on all hooks modules to have been imported at the point that
        # we create the admin_menu and settings_menu instances
        self._registered_menu_items = None

def users_with_page_permission(page, permission_type, include_superusers=True):
    # Get user model
    User = get_user_model()

    # Find GroupPagePermission records of the given type that apply to this page or an ancestor
    ancestors_and_self = list(page.get_ancestors()) + [page]
    perm = GroupPagePermission.objects.filter(permission_type=permission_type, page__in=ancestors_and_self)
    q = Q(groups__page_permissions=perm)

    # Include superusers
    if include_superusers:
        q |= Q(is_superuser=True)

    return User.objects.filter(is_active=True).filter(q).distinct()


@task
def send_notification(page_revision_id, notification, excluded_user_id):
    # Get revision
    revision = PageRevision.objects.get(id=page_revision_id)
    
    # Get list of recipients
    if notification == 'submitted':
        # Get list of publishers
        recipients = users_with_page_permission(revision.page, 'publish')
    elif notification in ['rejected', 'approved']:
        # Get submitter
        recipients = [revision.user]
    else:
        return

    # Get list of email addresses
    email_addresses = [
        recipient.email for recipient in recipients
        if recipient.email and recipient.id != excluded_user_id and getattr(UserProfile.get_for_user(recipient), notification + '_notifications')
    ]

    # Return if there are no email addresses
    if not email_addresses:
        return

    # Get email subject and content
    text_template = 'wagtailadmin/notifications/text/' + notification + '.html'
    html_template = 'wagtailadmin/notifications/html/' + notification + '.html'

    rendered_text_template = render_to_string(text_template, dict(revision=revision, settings=settings)).split('\n')
    rendered_html_template = render_to_string(html_template, dict(revision=revision, settings=settings)).split('\n')
    
    email_subject = rendered_template[0]
    email_content = '\n'.join(rendered_template[1:])

    # Get from email
    if hasattr(settings, 'WAGTAILADMIN_NOTIFICATION_FROM_EMAIL'):
        from_email = settings.WAGTAILADMIN_NOTIFICATION_FROM_EMAIL
    elif hasattr(settings, 'DEFAULT_FROM_EMAIL'):
        from_email = settings.DEFAULT_FROM_EMAIL
    else:
        from_email = 'webmaster@localhost'

    # Send email
    send_mail(email_subject, email_content, from_email, email_addresses, html_message=None)


@task
def send_email_task(email_subject, email_content, email_addresses, from_email=None):
    if not from_email:
        if hasattr(settings, 'WAGTAILADMIN_NOTIFICATION_FROM_EMAIL'):
            from_email = settings.WAGTAILADMIN_NOTIFICATION_FROM_EMAIL
        elif hasattr(settings, 'DEFAULT_FROM_EMAIL'):
            from_email = settings.DEFAULT_FROM_EMAIL
        else:
            from_email = 'webmaster@localhost'

    send_mail(email_subject, email_content, from_email, email_addresses)
