import urllib2

from django.db import models, IntegrityError

from canvas import json
from canvas.models import BaseCanvasModel


class SuppressedEmail(BaseCanvasModel):
    email = models.CharField(max_length=255, unique=True)


def handle_SubscriptionConfirmation(notification):
    urllib2.urlopen(notification.get('SubscribeURL')).read()

def handle_UnsubscribeConfirmation(notification):
    handle_SubscriptionConfirmation(notification)

def handle_Notification(notification):
    message = json.loads(notification['Message'])

    notification_type = message.get('notificationType')

    if notification_type == 'Bounce':
        handle_bounce(message)
    elif notification_type == 'Complaint':
        handle_complaint(message)

# http://docs.aws.amazon.com/ses/latest/DeveloperGuide/notification-contents.html#bounce-types
def handle_bounce(message):
    details = message['bounce']
    permanent = details['bounceType'] == 'Permanent'
    sub_type = parse_sub_type(details['bounceSubType'])

    for recipient in details['bouncedRecipients']:
        email = recipient['emailAddress']

        bounce = Bounce.objects.create(
            email=email,
            permanent=permanent,
            sub_type=sub_type,
        )

        if bounce.should_suppress_emails():
            try:
                SuppressedEmail.objects.create(email=email)
            except IntegrityError:
                pass

def handle_complaint(message):
    details = message['complaint']

    for recipient in details['complainedRecipients']:
        email = recipient['emailAddress']
        
        complaint = Complaint.objects.create(
            email=email,
            feedback_type=message.get('complaintFeedbackType', ''),
        )

        if complaint.should_suppress_emails():
            try:
                SuppressedEmail.objects.create(email=email)
            except IntegrityError:
                pass


class Bounce(BaseCanvasModel):
    UNDETERMINED, GENERAL, NO_EMAIL, MAILBOX_FULL, MESSAGE_TOO_LARGE, CONTENT_REJECTED, ATTACHMENT_REJECTED, SUPPRESSED = range(0, 8)

    email = models.CharField(max_length=255, blank=False)
    permanent = models.BooleanField(blank=False)
    sub_type = models.SmallIntegerField(blank=False)

    def should_suppress_emails(self):
        return not (self.sub_type == Bounce.MAILBOX_FULL
                    or self.sub_type == Bounce.GENERAL and not self.permanent
                    or self.sub_type == Bounce.SUPPRESSED and not self.permanent)


class Complaint(BaseCanvasModel):
    email = models.CharField(max_length=255, blank=False)
    feedback_type = models.CharField(max_length=255, blank=True)

    def should_suppress_emails(self):
        return False


# http://docs.aws.amazon.com/ses/latest/DeveloperGuide/notification-contents.html
def parse_sub_type(sub_type_string):
    return {
        'Undetermined': 0,
        'General': 1,
        'NoEmail': 2,
        'MailboxFull': 3,
        'MessageToolarge': 4, # The "l" is lowercase according to the docs.
        'ContentRejected': 5,
        'AttachmentRejected': 6,
        'Suppressed': 7,
    }[sub_type_string]

