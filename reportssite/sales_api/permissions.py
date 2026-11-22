from rest_framework.permissions import BasePermission


class IsCounterpartyEmployee(BasePermission):
    """
    Разрешает доступ только пользователям, привязанным к контрагенту.
    Сохраняет объект контрагента в request.counterparty.
    """
    message = 'Пользователь не привязан к контрагенту'

    def has_permission(self, request, view):

        # Проверяем, что пользователь авторизован и имеет профиль
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Для персонала вход свободый
        if request.user.is_staff:
            request.counterparty = None
            return True

        # select_related подтянет контрагента 
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.counterparty:
            return False

        # Сохраняем контрагента в request для удобного использования во View
        request.counterparty = profile.counterparty
        return True
