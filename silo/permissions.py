from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet
        return obj.owner == request.user


class IsOwnerOrSuperUser(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user or request.user.is_superuser


class Silo_IsOwnerOrCanRead(permissions.BasePermission):
    """
    Custom permission to only allow access to silos if the user
    is the silo owner, if the silo has been shared with the user,
    or if the silo is public.
    """

    def has_object_permission(self, request, view, obj):

        permitted = [obj.owner == request.user]
        permitted.append(request.user.is_superuser)
        permitted.append(obj.public)
        permitted.append(request.user.id in obj.shared.values_list('id', flat=True))

        return any(permitted)


class Read_IsOwnerViewOrWrite(permissions.BasePermission):
    """
    Custom permission to only allow access to silos if the user
    is the silo owner, if the silo has been shared with the user,
    or if the silo is public.
    """

    def has_object_permission(self, request, view, obj):

        permitted = [obj.owner == request.user]
        permitted.append(request.user.is_superuser)

        if request.method in ['GET', 'HEAD']:
            permitted.append(obj.silos__public)
            permitted.append(request.user.id in obj.silos__shared.values_list('id', flat=True))
        return any(permitted)
