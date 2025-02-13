from fastapi import FastAPI, Request, status, Form, Depends, UploadFile, File
from user_auth.oauth_token import create_token
from user_auth.password_hashing import Hash
from database_config import db_models, db_creation
from database_config.db_creation import Base, engine
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
from end_functions.db_functions import get_one_db_data, add_data_in_db, get_all_db_data_with, get_all_db_data
from verifications.email_and_pass_verification import email_checker
from e_website_route.website_route import e_router
import datetime
import os.path
from typing import List
import uvicorn

app = FastAPI()
app.include_router(e_router)
Base.metadata.create_all(engine)

templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")


# =========register and login===========
@app.get("/logout/")
async def logout(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        is_user = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if is_user:
            is_user.user_token = None
            is_user.user_status = False
            db.commit()

        response = RedirectResponse(url=app.url_path_for("login_api"), status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie('token')
        request.cookies.pop('token')
        return response

    else:
        return RedirectResponse(url=app.url_path_for("login_api"), status_code=status.HTTP_303_SEE_OTHER)


@app.get('/register/')
async def register_api(request: Request):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("dashboard_api"))

    message = ''
    return templates.TemplateResponse("register/sign-up.html", {"request": request, "error": message})


@app.post('/register/')
async def register_api(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                       email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...),
                       db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("dashboard_api"))

    if email_checker(email):
        user = await get_one_db_data(db, db_models.User, db_models.User.email, email)
        if user:
            message = 'User already exist'
            return templates.TemplateResponse("register/sign-up.html", {"request": request, "error": message})
        else:
            if password != confirm_password:
                message = 'Password is not matched'
                return templates.TemplateResponse("register/sign-up.html", {"request": request, "error": message})
            else:
                message = 'User Created Successfully'
                current_time = datetime.datetime.now()
                new_user = db_models.User(first_name=first_name, last_name=last_name, email=email,
                                          password=Hash.argon2(password), confirm_password=Hash.argon2(password),
                                          created_at=current_time, is_admin=False, user_status=False)

                db.add(new_user)
                db.commit()
                db.refresh(new_user)

                return templates.TemplateResponse("register/sign-in.html", {"request": request, "success": message})

    return RedirectResponse(url=app.url_path_for('register_api'))


@app.get('/', status_code=status.HTTP_200_OK)
async def login_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if not is_admin:
            admin_exist = db.query(db_models.User).filter(db_models.User.email == 'admin123@gmail.com').first()
            if not admin_exist:
                current_time = datetime.datetime.now()
                new_admin = db_models.User(first_name="Admin", last_name="Admin", email="admin123@gmail.com",
                                           password=Hash.argon2("admin123"), confirm_password=Hash.argon2("admin123"),
                                           user_token="", created_at=current_time, is_admin=True, user_status=False)
                db.add(new_admin)
                db.commit()
                db.refresh(new_admin)

        return templates.TemplateResponse("register/sign-in.html", {"request": request})

    return RedirectResponse(url=app.url_path_for("dashboard_api"), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/', status_code=status.HTTP_200_OK)
async def login_api(request: Request, email: str = Form(...), password: str = Form(...),
                    db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("dashboard_api"))

    user = db.query(db_models.User).filter(db_models.User.email == email).first()
    error = "User not exits!"
    if user:
        if email_checker(email):
            if Hash.verify(password, user.password):
                if user:
                    user.user_token = create_token()
                    user.user_status = True
                    db.commit()

                    updated_token = db.query(db_models.User).filter(db_models.User.email == email).first()
                    response = RedirectResponse(url=app.url_path_for("dashboard_api"))
                    response.set_cookie(key="token", value=updated_token.user_token)

                    return response

            error = "Invalid credentials!"
    return templates.TemplateResponse("register/sign-in.html", {"request": request, "error": error})


# ========dashboard data=========
@app.get('/dashboard/', status_code=status.HTTP_200_OK)
async def dashboard_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('logout'))

    is_admin = await get_one_db_data(db, db_models.User, db_models.User.user_token, is_token)
    if is_admin:
        category_data = await get_all_db_data(db, db_models.Category)
        product_data = await get_all_db_data(db, db_models.Products)
        all_user_data = await get_all_db_data(db, db_models.User)
        return templates.TemplateResponse("pages/dashboard.html", {"request": request, "user_data": is_admin,
                                                                   "category_data": category_data,
                                                                   "product_data": product_data,
                                                                   "all_user_data": all_user_data,
                                                                   "active_page": "dashboard"})


@app.post('/dashboard/', status_code=status.HTTP_200_OK)
async def dashboard_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = await get_one_db_data(db, db_models.User, db_models.User.user_token, is_token)
    if is_admin:
        category_data = await get_all_db_data(db, db_models.Category)
        product_data = await get_all_db_data(db, db_models.Products)
        all_user_data = await get_all_db_data(db, db_models.User)
        return templates.TemplateResponse("pages/dashboard.html", {"request": request, "user_data": is_admin,
                                                                   "category_data": category_data,
                                                                   "product_data": product_data,
                                                                   "all_user_data": all_user_data,
                                                                   "active_page": "dashboard"})


# ========user data=========
@app.get('/get_all_user/', status_code=status.HTTP_200_OK)
async def get_all_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).all()
    category_data = db.query(db_models.Category).all()
    return templates.TemplateResponse("user/users.html", {"request": request, 'user_data': user_exist,
                                                            "category_data": category_data, "active_page": "users"})


@app.get('/add_user/')
async def add_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    message = ''
    category_data = db.query(db_models.Category).all()
    return templates.TemplateResponse("user/add-user.html", {"request": request, "error": message,
                                                             "category_data": category_data,
                                                             "active_page": "adduser"})


@app.post('/add_user/')
async def add_user(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                   email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...),
                   db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    if email_checker(email):
        user = db.query(db_models.User).filter(db_models.User.email == email).first()
        if user:
            message = 'User already exist'
            return templates.TemplateResponse("register/sign-up.html", {"request": request, "error": message})
        else:
            if password != confirm_password:
                message = 'Password is not matched'
                return templates.TemplateResponse("register/sign-up.html", {"request": request, "error": message})
            else:
                message = 'User Created Successfully'
                category_data = db.query(db_models.Category).all()
                current_time = datetime.datetime.now()
                new_user = db_models.User(first_name=first_name, last_name=last_name, email=email,
                                          password=Hash.argon2(password),
                                          confirm_password=Hash.argon2(password), user_token="",
                                          created_at=current_time, is_admin=False, user_status=False)

                db.add(new_user)
                db.commit()
                db.refresh(new_user)

                return templates.TemplateResponse("user/add-user.html", {"request": request, "success": message,
                                                                         "category_data": category_data,
                                                                         "active_page": "adduser"})

    return RedirectResponse(url=app.url_path_for('register_api'))


@app.get('/update_user/{user_id}/', status_code=status.HTTP_200_OK)
async def update_user(request: Request, user_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

    if is_admin:
        user_exist = db.query(db_models.User).filter(db_models.User.id == user_id).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("user/profile.html", {"request": request, "user_data": user_exist,
                                                                    "category_data": category_data,
                                                                    "active_page": "profile"})


@app.post('/update_user/{user_id}/', status_code=status.HTTP_200_OK)
async def update_user(request: Request, user_id: int,  first_name: str = Form(None), last_name: str = Form(None),
                      email: str = Form(None), password: str = Form(None), confirm_password: str = Form(None),
                      db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))
    is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

    if is_admin.is_admin:
        user_exist = db.query(db_models.User).filter(db_models.User.id == user_id).first()
        if user_exist:
            if password != confirm_password:
                print('password error')
                return

            if password is not None and confirm_password is not None:
                user_exist.password = Hash.argon2(password)
                user_exist.confirm_password = Hash.argon2(confirm_password)

            if first_name is not None and last_name is not None:
                user_exist.first_name = first_name
                user_exist.last_name = last_name

            if email is not None:
                user_exist.email = email

            db.commit()
            message = "Profile updated successfully"
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("user/profile.html", {"request": request, "user_data": user_exist,
                                                                    "success": message, "category_data": category_data,
                                                                    "active_page": "profile"})
        else:
            message = "user not exist"
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("user/profile.html", {"request": request, "user_data": user_exist,
                                                                    "success": message, "category_data": category_data,
                                                                    "active_page": "profile"})


@app.get('/delete_user/{item_id}/', status_code=status.HTTP_200_OK)
async def delete_user(request: Request, item_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = await get_one_db_data(db, db_models.User, db_models.User.user_token, is_token)
    if user_exist:
        data_exist = db.query(db_models.User).filter(db_models.User.id == item_id)
        if data_exist:
            data_exist.delete(synchronize_session=False)
            db.commit()
        return RedirectResponse(url=app.url_path_for('get_all_user'), status_code=status.HTTP_303_SEE_OTHER)


# ========category data=========
@app.get('/category/', status_code=status.HTTP_200_OK)
async def category_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("category/category.html", {"request": request, "user_data": user_exist,
                                                                     "category_data": category_data,
                                                                     "active_page": "category"})


@app.get('/add_category/', status_code=status.HTTP_200_OK)
async def add_category_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        return templates.TemplateResponse("category/add_category.html", {"request": request, "user_data": user_exist,
                                                                         "active_page": "category"})


@app.post('/add_category/', status_code=status.HTTP_200_OK)
async def add_category_api(request: Request, category_name: str = Form(...), image: UploadFile = Form(...),
                           db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        file_path = ""
        if not os.path.exists("static/uploads"):
            os.makedirs("static/uploads")

        if image.filename != "":
            file_path = f"static/uploads/{image.filename}"
            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())
        else:
            print(f"File {image.filename} is not an image")

        db_data = db_models.Category(category_name=category_name, img_path=file_path, user_id=user_exist.id)
        await add_data_in_db(db, db_data)
        success = "Category added successfully"
        return templates.TemplateResponse("category/add_category.html", {"request": request, "user_data": user_exist,
                                                                      "success": success, "active_page": "category"})


@app.get('/update_category/{item_id}/', status_code=status.HTTP_200_OK)
async def update_category(request: Request, item_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = await get_one_db_data(db, db_models.Category, db_models.Category.id, item_id)
        return templates.TemplateResponse("category/update_category.html", {"request": request, "user_data": user_exist,
                                                                            "category_data": category_data,
                                                                            "active_page": "category"})


@app.post('/update_category/{item_id}/', status_code=status.HTTP_200_OK)
async def update_category(request: Request, item_id: int, category_name: str = Form(None), image: UploadFile = Form(None),
                          db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).filter(db_models.Category.id == item_id).first()
        if category_data:
            if category_name is not None:
                category_data.category_name = category_name
            if image.filename != "":
                category_data.img_path = image.filename

        db.commit()
        message = "Category updated successfully"
        return templates.TemplateResponse("category/update_category.html", {"request": request, "user_data": user_exist,
                                                                            "success": message,
                                                                            "category_data": category_data,
                                                                            "active_page": "category"})


@app.get('/delete_category/{item_id}/', status_code=status.HTTP_200_OK)
async def delete_category(request: Request, item_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = await get_one_db_data(db, db_models.User, db_models.User.user_token, is_token)
    if user_exist:
        data_exist = db.query(db_models.Category).filter(db_models.Category.id == item_id)
        if data_exist:
            data_exist.delete(synchronize_session=False)
            db.commit()
        return RedirectResponse(url=app.url_path_for('category_api'), status_code=status.HTTP_303_SEE_OTHER)


# ========product data=========
@app.get('/products/', status_code=status.HTTP_200_OK)
async def products_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        product_data = await get_all_db_data(db, db_models.Products)
        return templates.TemplateResponse("product/products.html", {"request": request, "user_data": user_exist,
                                                                    "product_data": product_data,
                                                                    "active_page": "products"})


@app.get('/get_products/{category_name}/{data_id}/', status_code=status.HTTP_200_OK)
async def get_products_api(request: Request, category_name: str, data_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        product_data = await get_all_db_data_with(db, db_models.Products, db_models.Products.category_id, data_id)
        return templates.TemplateResponse("product/get_products.html", {"request": request, "user_data": user_exist,
                                                                        "category_data": category_data,
                                                                        "category_name": category_name,
                                                                        "product_data": product_data,
                                                                        "active_page": "products"})


@app.post('/get_products/{category_name}/{data_id}/', status_code=status.HTTP_200_OK)
async def get_products_api(request: Request, category_name: str, data_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        product_data = await get_all_db_data_with(db, db_models.Products, db_models.Products.category_id, data_id)
        return templates.TemplateResponse("product/get_products.html", {"request": request, "user_data": user_exist,
                                                                        "category_data": category_data,
                                                                        "category_name": category_name,
                                                                        "product_data": product_data,
                                                                        "active_page": "products"})


@app.get('/delete_product/{category_name}/{item_id}/', status_code=status.HTTP_200_OK)
async def delete_category_product(request: Request, category_name: str, item_id: int,
                                  db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = await get_one_db_data(db, db_models.User, db_models.User.user_token, is_token)
    if user_exist:
        category_id = None
        data_exist = db.query(db_models.Products).filter(db_models.Products.id == item_id)
        if data_exist:
            category_data = data_exist.first()
            category_id = category_data.category_id
            data_exist.delete(synchronize_session=False)
            db.commit()
        return RedirectResponse(url=app.url_path_for('get_products_api', category_name=category_name,
                                                     data_id=category_id), status_code=status.HTTP_303_SEE_OTHER)


@app.get('/add_product/', status_code=status.HTTP_200_OK)
async def add_product(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("product/add_product.html", {"request": request, "user_data": user_exist,
                                                                       "category_data": category_data,
                                                                       "active_page": "products"})


@app.post('/add_product/', status_code=status.HTTP_200_OK)
async def add_product(request: Request, product_code: str = Form(None), product_name: str = Form(None),
                           select_category: int = Form(None), quantity: int = Form(None), sale_price: int = Form(None),
                           purchase_price: int = Form(None), description: str = Form(None),
                           images: List[UploadFile] = File(None), db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        if not os.path.exists("static/uploads"):
            os.makedirs("static/uploads")

        image_paths = []
        for img_file in images:
            if img_file.filename != "":
                if img_file.content_type.startswith('image/'):
                    file_location = f"static/uploads/{img_file.filename}"
                    with open(file_location, "wb") as file_object:
                        file_object.write(img_file.file.read())
                    image_paths.append(file_location)
                else:
                    print(f"File {img_file.filename} is not an image")

        product_image1 = image_paths[0] if len(image_paths) > 0 else None
        product_image2 = image_paths[1] if len(image_paths) > 1 else None
        product_image3 = image_paths[2] if len(image_paths) > 2 else None

        db_data = db_models.Products(product_code=product_code, product_name=product_name, sale_price=sale_price,
                                     product_description=description, product_image1=product_image1,
                                     product_image2=product_image2, product_image3=product_image3,
                                     product_quantity=quantity, purchase_price=purchase_price,
                                     category_id=select_category, user_id=user_exist.id)

        db.add(db_data)
        db.commit()
        db.refresh(db_data)

        success = "Product added successfully!"
        return templates.TemplateResponse("product/add_product.html", {"request": request, "user_data": user_exist,
                                                                       "category_data": category_data,
                                                                       "success": success, "active_page": "products"})


@app.get('/update_product/{item_id}/', status_code=status.HTTP_200_OK)
async def update_product(request: Request, item_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = await get_all_db_data(db, db_models.Category)
        product_data = await get_one_db_data(db, db_models.Products, db_models.Products.id, item_id)
        selected_category = await get_one_db_data(db, db_models.Category, db_models.Category.id,
                                                  product_data.category_id)
        return templates.TemplateResponse("product/update_product.html", {"request": request,
                                                                          "user_data": user_exist,
                                                                          "selected_category": selected_category,
                                                                          "category_data": category_data,
                                                                          "product_data": product_data,
                                                                          "active_page": "products"})


@app.post('/update_product/{item_id}/', status_code=status.HTTP_200_OK)
async def update_product(request: Request, item_id: int, product_code: str = Form(None), product_name: str = Form(None),
                   select_category: int = Form(None), quantity: int = Form(None), sale_price: int = Form(None),
                   purchase_price: int = Form(None), description: str = Form(None),
                   images: List[UploadFile] = File(None), db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        product_data = db.query(db_models.Products).filter(db_models.Products.id == item_id).first()
        if product_data:
            if product_code is not None:
                product_data.product_code = product_code
            if product_name is not None:
                product_data.product_name = product_name
            if select_category is not None:
                product_data.category_id = select_category
            if quantity is not None:
                product_data.product_quantity = quantity
            if purchase_price is not None:
                product_data.purchase_price = purchase_price
            if sale_price is not None:
                product_data.sale_price = sale_price
            if description is not None:
                product_data.product_description = description

            image_paths = []
            if images:
                if not os.path.exists("static/uploads"):
                    os.makedirs("static/uploads")

                for img_file in images:
                    if img_file.filename != "":
                        if img_file.content_type.startswith('image/'):
                            file_location = f"static/uploads/{img_file.filename}"
                            with open(file_location, "wb") as file_object:
                                file_object.write(img_file.file.read())
                            image_paths.append(file_location)
                        else:
                            print(f"File {img_file.filename} is not an image")

                if len(image_paths) > 0:
                    product_data.product_image1 = image_paths[0]
                if len(image_paths) > 1:
                    product_data.product_image2 = image_paths[1]
                if len(image_paths) > 2:
                    product_data.product_image3 = image_paths[2]

            db.commit()
            message = "Product updated successfully"
            updated_product = await get_one_db_data(db, db_models.Products, db_models.Products.id, item_id)
            category_data = await get_all_db_data(db, db_models.Category)
            selected_category = await get_one_db_data(db, db_models.Category, db_models.Category.id, product_data.category_id)
            return templates.TemplateResponse("product/update_product.html", {"request": request,
                                                                              "user_data": user_exist,
                                                                              "selected_category": selected_category,
                                                                              "category_data": category_data,
                                                                              "product_data": updated_product,
                                                                              "success": message,
                                                                              "active_page": "products"})


@app.get('/delete_product/{item_id}/', status_code=status.HTTP_200_OK)
async def delete_product(request: Request, item_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = await get_one_db_data(db, db_models.User, db_models.User.user_token, is_token)
    if user_exist:
        data_exist = db.query(db_models.Products).filter(db_models.Products.id == item_id)
        if data_exist:
            data_exist.delete(synchronize_session=False)
            db.commit()
        return RedirectResponse(url=app.url_path_for('products_api'), status_code=status.HTTP_303_SEE_OTHER)


# ========billing data=========
@app.get('/billing/', status_code=status.HTTP_200_OK)
async def billing_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("pages/billing.html", {"request": request, "user_data": user_exist,
                                                                 "category_data": category_data,
                                                                 "active_page": "billing"})


@app.post('/billing/', status_code=status.HTTP_200_OK)
async def billing_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("pages/billing.html", {"request": request, "user_data": user_exist,
                                                                 "category_data": category_data,
                                                                 "active_page": "billing"})


@app.get('/delete_bill/{item_id}/', status_code=status.HTTP_200_OK)
async def delete_bill(request: Request, item_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = await get_one_db_data(db, db_models.User, db_models.User.user_token, is_token)
    if user_exist:
        data_exist = db.query(db_models.Products).filter(db_models.Products.id == item_id)
        if data_exist:
            data_exist.delete(synchronize_session=False)
            db.commit()
        return RedirectResponse(url=app.url_path_for('category_api'), status_code=status.HTTP_303_SEE_OTHER)


# ========notification data=========
@app.get('/notification/', status_code=status.HTTP_200_OK)
async def notification_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("pages/notifications.html", {"request": request, "user_data": user_exist,
                                                                       "category_data": category_data,
                                                                       "active_page": "notification"})


@app.post('/notification/', status_code=status.HTTP_200_OK)
async def notification_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for('login_api'))

    user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
    if user_exist:
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("pages/notifications.html", {"request": request, "user_data": user_exist,
                                                                       "category_data": category_data,
                                                                       "active_page": "notification"})


# ========daily sales data=========
@app.get('/daily_sales/', status_code=status.HTTP_200_OK)
async def daily_sales(request: Request, db: Session = Depends(db_creation.get_db)):
    return 'daily sales'


@app.post('/daily_sales/', status_code=status.HTTP_200_OK)
async def daily_sales(request: Request, db: Session = Depends(db_creation.get_db)):
    return 'daily sales'


# ========completed tasks data=========
@app.get('/completed_task/', status_code=status.HTTP_200_OK)
async def completed_task(request: Request, db: Session = Depends(db_creation.get_db)):
    return 'completed task'


@app.post('/completed_task/', status_code=status.HTTP_200_OK)
async def completed_task(request: Request, db: Session = Depends(db_creation.get_db)):
    return 'completed task'


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
