from canvas.models import Visibility
from drawquest.apps.quest_comments.models import QuestComment


def top_comments(user):
    comments = QuestComment.by_author(user).filter(star_count__gt=0, visibility=Visibility.PUBLIC)
    comments = comments.order_by('-star_count')
    comments = comments[:8]

    if len(comments) < 4:
        return None

    return comments

