from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles
from database_config import db_creation, db_models
from end_functions.db_functions import get_all_db_data, get_all_db_data_with

e_router = APIRouter(prefix="/e_website", tags=["e_website"])

templates = Jinja2Templates(directory='templates')
e_router.mount("/static", StaticFiles(directory="static"), name="static")


@e_router.get('/home/')
async def home(request: Request, db: Session = Depends(db_creation.get_db)):
    category_data = await get_all_db_data(db, db_models.Category)
    product_data = await get_all_db_data(db, db_models.Products)

    return templates.TemplateResponse("e_website/home_page.html", context={"request": request,
                                                                           "category_data": category_data,
                                                                           "product_data": product_data,
                                                                           "active_page": "home"})


@e_router.get('/about/')
async def about(request: Request, db: Session = Depends(db_creation.get_db)):
    category_data = await get_all_db_data(db, db_models.Category)
    product_data = await get_all_db_data(db, db_models.Products)

    return templates.TemplateResponse("e_website/about_page.html", context={"request": request, "active_page": "about",
                                                                            "category_data": category_data,
                                                                            "product_data": product_data})


@e_router.get('/selected_category/{category_id}/')
async def selected_category(request: Request, category_id: int, db: Session = Depends(db_creation.get_db)):
    category_data = await get_all_db_data(db, db_models.Category)
    product_data = await get_all_db_data_with(db, db_models.Products, db_models.Products.category_id, category_id)

    return templates.TemplateResponse("e_website/category_page.html", context={"request": request,
                                                                               "category_data": category_data,
                                                                               "product_data": product_data,
                                                                               "active_page": "category"})
