from typing import Optional
from fastapi import Header, Request


async def get_current_user_id(
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> str:
    """
    Retrieves the current user ID from the request header.
    Defaults to a standard development user ID if not provided in header.
    """
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    # Query param fallback for simple testing/curl
    user_param = request.query_params.get("user_id")
    if user_param and user_param.strip():
        return user_param.strip()

    return "default_candidate_user_1"
