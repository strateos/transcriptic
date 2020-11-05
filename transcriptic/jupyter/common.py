try:
    import pandas as pd
except ImportError:
    raise ImportError(
        "Please run `pip install transcriptic[jupyter] if you "
        "would like to use Transcriptic objects."
    )


def _check_api(obj_type):
    from transcriptic import api

    if not api:
        raise RuntimeError(
            f"You have to be logged in to be able to create {obj_type} objects"
        )
    return api


class _BaseObject(object):
    """Base object which other objects inherit from"""

    # TODO: Inherit more stuff from here. Need to ensure web has unified fields for
    #  jupyter
    def __init__(self, obj_type, obj_id, attributes, connection=None):
        # If attributes and connection are explicitly provided, just return and not do
        # any smart parsing
        if attributes and connection:
            self.connection = connection
            self.attributes = attributes
        else:
            if not connection:
                self.connection = _check_api(obj_type)
            else:
                self.connection = connection
            (self.id, self.name) = self.load_object(obj_type, obj_id)
            if not attributes:
                self.attributes = self.connection._get_object(self.id, obj_type)
            else:
                self.attributes = attributes

    def load_object(self, obj_type, obj_id):
        """Find and match object by name"""
        # TODO: Remove the try/except statement and properly handle cases where objects
        #  are not found
        # TODO: Fix `datasets` route since that only returns non-analysis objects
        try:
            objects = getattr(self.connection, obj_type + "s")()
        except Exception:
            return obj_id, str(obj_id)
        matched_objects = []
        for obj in objects:
            # Special case here since we use both 'name' and 'title' for object names
            if "name" in obj:
                if obj_id == obj["name"] or obj_id == obj["id"]:
                    matched_objects.append((obj["id"], obj["name"]))
            if "title" in obj:
                if obj_id == obj["title"] or obj_id == obj["id"]:
                    matched_objects.append((obj["id"], obj["title"]))
        if len(matched_objects) == 0:
            raise TypeError(f"{obj_id} is not found in your {obj_type}s.")
        elif len(matched_objects) == 1:
            return matched_objects[0]
        else:
            print(
                f"More than 1 match found. Defaulting to the first match: "
                f"{matched_objects[0]}"
            )
            return matched_objects[0]
