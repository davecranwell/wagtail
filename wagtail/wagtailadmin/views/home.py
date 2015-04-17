from django.shortcuts import render
from django.conf import settings

from wagtail.wagtailcore import hooks
from wagtail.wagtailcore.models import PageRevision, UserPagePermissionsProxy
from wagtail.utils.compat import render_to_string

from wagtail.wagtailadmin.site_summary import SiteSummaryPanel


# Panels for the homepage

class UpgradeNotificationPanel(object):
    name = 'upgrade_notification'
    order = 100

    def __init__(self, request):
        self.request = request

    def render(self):
        if self.request.user.is_superuser and getattr(settings, "WAGTAIL_ENABLE_TRACKING", True):
            return render_to_string('wagtailadmin/home/upgrade_notification.html', {}, request=self.request)
        else:
            return ""

class PagesForModerationPanel(object):
    name = 'pages_for_moderation'
    order = 200

    def __init__(self, request):
        self.request = request
        user_perms = UserPagePermissionsProxy(request.user)
        self.page_revisions_for_moderation = user_perms.revisions_for_moderation().select_related('page', 'user').order_by('-created_at')

    def render(self):
        return render_to_string('wagtailadmin/home/pages_for_moderation.html', {
            'page_revisions_for_moderation': self.page_revisions_for_moderation,
        }, request=self.request)


class RecentEditsPanel(object):
    name = 'recent_edits'
    order = 300

    def __init__(self, request):
        self.request = request
        # Last n edited pages
        self.last_edits = PageRevision.objects.raw(
            """
            select wp.* FROM
                wagtailcore_pagerevision wp JOIN (
                    SELECT max(created_at) as max_created_at, page_id FROM wagtailcore_pagerevision group by page_id
                ) as max_rev on max_rev.max_created_at = wp.created_at and wp.user_id = %s order by wp.created_at desc
            """, [request.user.id])[:5]

    def render(self):
        return render_to_string('wagtailadmin/home/recent_edits.html', {
            'last_edits': self.last_edits,
        }, request=self.request)


def home(request):

    panels = [
        SiteSummaryPanel(request),
        UpgradeNotificationPanel(request),
        PagesForModerationPanel(request),
        RecentEditsPanel(request),
    ]

    for fn in hooks.get_hooks('construct_homepage_panels'):
        fn(request, panels)

    return render(request, "wagtailadmin/home.html", {
        'site_name': settings.WAGTAIL_SITE_NAME,
        'panels': sorted(panels, key=lambda p: p.order),
        'user': request.user
    })


def error_test(request):
    raise Exception("This is a test of the emergency broadcast system.")
