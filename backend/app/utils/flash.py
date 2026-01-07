from fastapi.responses import RedirectResponse

def flash_redirect(
    url: str,
    message: str,
    category: str = "success",
    status_code: int = 303
):
    response = RedirectResponse(url=url, status_code=status_code)

    response.set_cookie(
        key=f"flash_{category}",
        value=message,
        max_age=5,
        path="/"
    )

    return response