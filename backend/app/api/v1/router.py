from fastapi import APIRouter

from app.api.v1 import applications, assistant, audit, auth, organizations, sources, usage

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(applications.router)
api_router.include_router(sources.router)
api_router.include_router(assistant.router)
api_router.include_router(usage.router)
api_router.include_router(audit.router)
