from aiogram import Router

from .start import router as start_router
from .clients import router as clients_router
from .companies import router as companies_router
from .search import router as search_router
from .stats import router as stats_router

router = Router()
router.include_router(start_router)
router.include_router(clients_router)
router.include_router(companies_router)
router.include_router(search_router)
router.include_router(stats_router)
