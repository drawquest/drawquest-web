from haystack import indexes

from drawquest.apps.drawquest_auth.models import User


class UserIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.NgramField(document=True, model_attr='username')

    def get_model(self):
        return User

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)

    def get_updated_field(self):
        return 'date_joined'

