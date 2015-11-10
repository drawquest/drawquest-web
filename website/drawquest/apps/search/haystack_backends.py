from django.conf import settings
from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend, ElasticsearchSearchEngine


# http://www.wellfireinteractive.com/blog/custom-haystack-elasticsearch-backend/
class ConfigurableElasticsearchBackend(ElasticsearchSearchBackend):
    DEFAULT_ANALYZER = "snowball"

    def __init__(self, connection_alias, **connection_options):
        super(ConfigurableElasticsearchBackend, self).__init__(connection_alias, **connection_options)

        user_settings = getattr(settings, 'ELASTICSEARCH_INDEX_SETTINGS', None)
        user_analyzer = getattr(settings, 'ELASTICSEARCH_DEFAULT_ANALYZER', None)

        if user_settings:
            setattr(self, 'DEFAULT_SETTINGS', user_settings)
        if user_analyzer:
            setattr(self, 'DEFAULT_ANALYZER', user_analyzer)

    def build_schema(self, fields):
        content_field_name, mapping = super(ConfigurableElasticsearchBackend, self).build_schema(fields)

        for field_name, field_class in fields.items():
            field_mapping = mapping[field_class.index_fieldname]

            if field_mapping['type'] == 'string' and field_class.indexed:
                if not hasattr(field_class, 'facet_for') and not field_class.field_type in('ngram', 'edge_ngram'):
                    field_mapping['analyzer'] = self.DEFAULT_ANALYZER
            mapping.update({field_class.index_fieldname: field_mapping})
        return (content_field_name, mapping)


class ConfigurableElasticsearchSearchEngine(ElasticsearchSearchEngine):
    backend = ConfigurableElasticsearchBackend

