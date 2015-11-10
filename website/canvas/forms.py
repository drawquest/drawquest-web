from canvas import models, knobs
from canvas.exceptions import ServiceError


def validate_and_clean_comment(user, parent_comment=None, replied_comment=None,
                               reply_content=None, category=None, title=None):
    """
    Raises `ServiceError` if not valid.

    Returns a tuple containing model instances of the following (in this order):
        replied_comment
        parent_comment
        reply_content
        category
    """
    noun = 'thread'
    attribute = 'title'

    original_parent_comment = parent_comment

    if title:
        if len(title) > knobs.POST_TITLE_MAX_LENGTH:
            raise ServiceError("{0} is too long.".format(attribute))
    elif parent_comment is None:
        raise ServiceError("Your {0} needs a {1}.".format(noun, attribute))
    else:
        title = ''

    # Was this a reply, or a new comment?
    if replied_comment is not None:
        # This is a new comment.
        replied_comment = models.Comment.all_objects.get(id=replied_comment)

    try:
        parent_comment = models.Comment.all_objects.get(id=parent_comment)
    except models.Comment.DoesNotExist:
        parent_comment = None

    if parent_comment is not None and original_parent_comment is None:
        parent_comment = None

    reply_content = models.Content.all_objects.get_or_none(pk=reply_content)

    if parent_comment:
        if parent_comment.visibility == models.Visibility.DISABLED and not user.is_staff:
            raise ServiceError('Sorry, this thread has been disabled.')
        # Replies must be of the same category as the parent.
        _category = parent_comment.category
    else:
        _category = None
        if category is not None:
            _category = models.Category.objects.get_or_none(name=category)
            if not _category:
                raise ServiceError("Group not found.")

    return (replied_comment, parent_comment, reply_content, _category, title,)

