class Email(object):
    def __init__(self, subject, to_address, text_content, html_content=None, from_address=None):
        self.subject = subject
        self.to_address = to_address
        self.from_address = from_address
        self.text_content = text_content
        self.html_content = html_content

        if not from_address:
            # Get from email
            if hasattr(settings, 'WAGTAILADMIN_NOTIFICATION_FROM_EMAIL'):
                self.from_address = settings.WAGTAILADMIN_NOTIFICATION_FROM_EMAIL
            elif hasattr(settings, 'DEFAULT_FROM_EMAIL'):
                self.from_address = settings.DEFAULT_FROM_EMAIL
            else:
                self.from_address = 'webmaster@localhost'

    def send(self):
        rendered_text_template = render_to_string(self.text_template, dict(revision=revision, settings=settings))
        rendered_html_template = render_to_string(self.html_template, dict(revision=revision, settings=settings))

         # Send email
        send_mail(self.subject, self.text_content, self.from_address, self.to_address, html_message=self.html_content)
