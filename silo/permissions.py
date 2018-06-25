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


class SiloIsOwnerOrCanRead(permissions.BasePermission):
    """
    Custom permission to only allow access to silos if the user
    is the silo owner, if the silo has been shared with the user,
    or if the silo is public.
    """

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_superuser:
            return True

        permitted = list()
        is_owner = obj.owner == request.user
        permitted.append(is_owner)
        permitted.append(request.user.is_superuser)
        permitted.append(obj.public)
        permitted.append(request.user.id in obj.shared.values_list('id',
                                                                   flat=True))
        if hasattr(obj.owner, 'tola_user'):
            permitted.append(obj.owner.tola_user.organization ==
                             request.user.tola_user.organization)

        return any(permitted)


class ReadIsOwnerViewOrWrite(permissions.BasePermission):
    """
    Custom permission to only allow access to silos if the user
    is the silo owner, if the silo has been shared with the user,
    or if the silo is public.
    """

    def has_object_permission(self, request, view, obj):
        is_owner = obj.owner == request.user
        permitted = list()
        permitted.append(is_owner)
        permitted.append(request.user.is_superuser)

        if request.method in permissions.SAFE_METHODS:
            silos_public = obj.silos.values_list('public', flat=True).all()
            silos_shared = obj.silos.filter(shared__id=request.user.id).exists()
            permitted.append(silos_public)
            permitted.append(silos_shared)
        return any(permitted)
