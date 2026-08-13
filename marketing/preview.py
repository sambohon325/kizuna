import os

import uvicorn


if __name__ == "__main__":
    os.environ.setdefault("KIZUNA_MARKETING_ADMIN_PASSWORD", "local-marketing-admin")
    os.environ.setdefault("KIZUNA_MARKETING_SESSION_SECRET", "local-preview-session-secret-change-in-production")
    os.environ.setdefault("KIZUNA_MARKETING_COOKIE_SECURE", "false")
    print("Kizuna marketing preview: http://127.0.0.1:8040")
    print("Local admin: http://127.0.0.1:8040/admin")
    print("Local preview password: local-marketing-admin")
    uvicorn.run("marketing.main:app", host="127.0.0.1", port=8040, reload=False)
