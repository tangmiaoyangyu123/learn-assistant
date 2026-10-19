"""把 FastAPI 的 /docs 和 /redoc 换成国内可访问的 CDN。

用法：
    from docs_helper import attach_docs
    app = FastAPI(docs_url=None, redoc_url=None)
    attach_docs(app)
"""

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html


def attach_docs(app: FastAPI) -> None:
    """给任意 FastAPI 应用挂上 /docs 和 /redoc（走 unpkg）。"""

    @app.get("/docs", include_in_schema=False)
    def _docs():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} · 文档",
            swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    def _redoc():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} · 文档",
            redoc_js_url="https://unpkg.com/redoc@2/bundles/redoc.standalone.js",
            with_google_fonts=False,
        )
