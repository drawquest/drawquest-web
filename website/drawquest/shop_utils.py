
class ShopMixin(object):
    @classmethod
    def _add_owned_by_viewer_field(cls, items_cls, items, viewer):
        viewer_items = items_cls.for_user(viewer)

        for item in items:
            if hasattr(item, 'owned_by_viewer'):
                continue

            item.owned_by_viewer = item in viewer_items

    @classmethod
    def for_shop(cls, viewer=None, request=None):
        items = list(cls.visible_in_shop(request=request))

        if viewer is not None and viewer.is_authenticated():
            cls._add_owned_by_viewer_field(cls, items, viewer)

        return items

    def unlock_for_user(self, user):
        self.owners.add(user)

