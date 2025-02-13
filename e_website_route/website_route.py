from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

e_router = APIRouter(prefix="/e_website", tags=["e_website"])

templates = Jinja2Templates(directory='templates')
e_router.mount("/static", StaticFiles(directory="static"), name="static")


@e_router.get('/home/')
async def home(request: Request):
    return templates.TemplateResponse("e_website/home_page.html", context={"request": request, "active_page": "home"})


@e_router.get('/about/')
async def about(request: Request):
    return templates.TemplateResponse("e_website/about_page.html", context={"request": request, "active_page": "about"})


@e_router.get('/selected_category/')
async def selected_category(request: Request):
    return templates.TemplateResponse("e_website/category_page.html", context={"request": request,
                                                                               "active_page": "category"})
