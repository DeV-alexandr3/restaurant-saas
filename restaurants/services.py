def get_current_membership(user):
    if not user.is_authenticated:
        return None

    return user.restaurant_memberships.filter(
        is_active=True
    ).first()