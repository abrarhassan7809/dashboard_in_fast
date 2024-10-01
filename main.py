import datetime
import os.path
from typing import List
import uvicorn
from fastapi import FastAPI, Request, status, Form, Depends, UploadFile, File
from authentication.oauth_token import create_token
from authentication.password_hashing import Hash
from database_config import db_models, db_creation
from database_config.db_creation import Base, engine
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from end_functions.db_functions import get_one_db_data, add_data_in_db
from verifications.email_and_pass_verification import email_checker, password_checker

app = FastAPI()
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
    return templates.TemplateResponse("pages/sign-up.html", {"request": request, "error": message})


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
            return templates.TemplateResponse("pages/sign-up.html", {"request": request, "error": message})
        else:
            if password != confirm_password:
                message = 'Password is not matched'
                return templates.TemplateResponse("pages/sign-up.html", {"request": request, "error": message})
            else:
                message = 'User Created Successfully'
                current_time = datetime.datetime.now()
                new_user = db_models.User(first_name=first_name, last_name=last_name, email=email,
                                          password=Hash.bcrypt(password),
                                          confirm_password=Hash.bcrypt(password),
                                          created_at=current_time, is_admin=False, user_status=False)

                db.add(new_user)
                db.commit()
                db.refresh(new_user)

                return templates.TemplateResponse("pages/sign-in.html", {"request": request, "success": message})

    return RedirectResponse(url=app.url_path_for('register_api'))


@app.get('/', status_code=status.HTTP_200_OK)
async def login_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        is_admin = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if not is_admin:
            current_time = datetime.datetime.now()
            new_admin = db_models.User(first_name="Admin", last_name="Admin", email="admin123@gmail.com",
                                       password=Hash.bcrypt("admin123"), confirm_password=Hash.bcrypt("admin123"),
                                       user_token="", created_at=current_time, is_admin=True, user_status=False)
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)

        return templates.TemplateResponse("pages/sign-in.html", {"request": request})

    return RedirectResponse(url=app.url_path_for("dashboard_api"), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/', status_code=status.HTTP_200_OK)
async def login_api(request: Request, email: str = Form(...), password: str = Form(...),
                    db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("dashboard_api"))

    user = db.query(db_models.User).filter(db_models.User.email == email).first()
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
    error = "User not exits!"
    return templates.TemplateResponse("pages/sign-in.html", {"request": request, "error": error})


# ========dashboard data=========
@app.get('/dashboard/', status_code=status.HTTP_200_OK)
async def dashboard_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/dashboard.html", {"request": request, "user_data": user_exist,
                                                                       "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('logout'), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/dashboard/', status_code=status.HTTP_200_OK)
async def dashboard_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/dashboard.html", {"request": request, "user_data": user_exist,
                                                                       "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('login_api'))


# ========user data=========
@app.get('/get_all_user/', status_code=status.HTTP_200_OK)
async def get_all_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).all()
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("pages/tables.html", {"request": request, 'user_data': user_exist,
                                                                "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('login_api'))


@app.get('/add_user/')
async def add_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        message = ''
        category_data = db.query(db_models.Category).all()
        return templates.TemplateResponse("pages/add-user.html", {"request": request, "error": message,
                                                                  "category_data": category_data})

    return RedirectResponse(url=app.url_path_for("login_api"))


@app.post('/add_user/')
async def add_user(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                   email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...),
                   db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if not is_token:
        return RedirectResponse(url=app.url_path_for("dashboard_api"))

    if email_checker(email):
        user = db.query(db_models.User).filter(db_models.User.email == email).first()
        if user:
            message = 'User already exist'
            return templates.TemplateResponse("pages/sign-up.html", {"request": request, "error": message})
        else:
            if password != confirm_password:
                message = 'Password is not matched'
                return templates.TemplateResponse("pages/sign-up.html", {"request": request, "error": message})
            else:
                message = 'User Created Successfully'
                category_data = db.query(db_models.Category).all()
                current_time = datetime.datetime.now()
                new_user = db_models.User(first_name=first_name, last_name=last_name, email=email,
                                          password=Hash.bcrypt(password),
                                          confirm_password=Hash.bcrypt(password), user_token="",
                                          created_at=current_time, is_admin=False, user_status=False)

                db.add(new_user)
                db.commit()
                db.refresh(new_user)

                return templates.TemplateResponse("pages/add-user.html", {"request": request, "success": message,
                                                                          "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('register_api'))


@app.get('/update_user/', status_code=status.HTTP_200_OK)
async def update_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/profile.html", {"request": request, "user_data": user_exist,
                                                                     "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('login_api'))


@app.post('/update_user/', status_code=status.HTTP_200_OK)
async def update_user(request: Request, first_name: str = Form(None), last_name: str = Form(None),
                      email: str = Form(None), password: str = Form(None), confirm_password: str = Form(None),
                      db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

        if user_exist:
            if password != confirm_password:
                print('password error')
                return

            if password is not None and confirm_password is not None:
                user_exist.password = Hash.bcrypt(password)
                user_exist.confirm_password = Hash.bcrypt(confirm_password)

            if first_name is not None and last_name is not None:
                user_exist.first_name = first_name
                user_exist.last_name = last_name

            if email is not None:
                user_exist.email = email

            db.commit()
            message = "Profile updated successfully"
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/profile.html", {"request": request, "user_data": user_exist,
                                                                     "success": message, "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('login_api'))


@app.delete('/delete_user/', status_code=status.HTTP_200_OK)
async def delete_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

        if user_exist:
            user_exist.delete(synchronize_session=False)
            db.commit()
            return RedirectResponse(url=app.url_path_for('login_api'))

    return RedirectResponse(url=app.url_path_for('login_api'))


# ========billing data=========
@app.get('/billing/', status_code=status.HTTP_200_OK)
async def billing_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/billing.html", {"request": request, "user_data": user_exist,
                                                                     "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('logout'), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/billing/', status_code=status.HTTP_200_OK)
async def billing_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/billing.html", {"request": request, "user_data": user_exist,
                                                                     "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('login_api'))


# ========notification data=========
@app.get('/notification/', status_code=status.HTTP_200_OK)
async def notification_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/notifications.html", {"request": request, "user_data": user_exist,
                                                                           "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('logout'), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/notification/', status_code=status.HTTP_200_OK)
async def notification_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/notifications.html", {"request": request, "user_data": user_exist,
                                                                           "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('login_api'))


# ========category data=========
@app.get('/category/', status_code=status.HTTP_200_OK)
async def category_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/category.html", {"request": request, "user_data": user_exist,
                                                                      "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('logout'), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/category/', status_code=status.HTTP_200_OK)
async def category_api(request: Request, category_name: str = Form(None), db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            print(category_name)
            db_data = db_models.Category(category_name=category_name, user_id=user_exist.id)
            await add_data_in_db(db, db_data)
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/category.html", {"request": request, "user_data": user_exist,
                                                                           "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('login_api'))


# ========product data=========
@app.get('/get_products/{category_name}/{data_id}/', status_code=status.HTTP_200_OK)
async def get_products_api(request: Request, category_name: str, data_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/get_products.html", {"request": request, "user_data": user_exist,
                                                                          "category_data": category_data,
                                                                          "category_name": category_name})

    return RedirectResponse(url=app.url_path_for('logout'), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/get_products/{category_name}/{data_id}/', status_code=status.HTTP_200_OK)
async def get_products_api(request: Request, category_name: str, data_id: int, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/get_products.html", {"request": request, "user_data": user_exist,
                                                                          "category_data": category_data,
                                                                          "category_name": category_name})

    return RedirectResponse(url=app.url_path_for('login_api'))


@app.get('/add_product/', status_code=status.HTTP_200_OK)
async def add_product(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            return templates.TemplateResponse("pages/add_product.html", {"request": request, "user_data": user_exist,
                                                                         "category_data": category_data})

    return RedirectResponse(url=app.url_path_for('logout'), status_code=status.HTTP_303_SEE_OTHER)


@app.post('/add_product/', status_code=status.HTTP_200_OK)
async def add_product(request: Request, product_code: str = Form(None), product_name: str = Form(None),
                           select_category: int = Form(None), quantity: int = Form(None), sale_price: int = Form(None),
                           purchase_price: int = Form(None), description: str = Form(None),
                           images: List[UploadFile] = File(None), db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            category_data = db.query(db_models.Category).all()
            if not os.path.exists("static/uploads"):
                os.makedirs("static/uploads")

            image_paths = []
            print(images)
            for img_file in images:
                if img_file.filename != "":  # Check if the file is uploaded
                    if img_file.content_type.startswith('image/'):  # Validate the file type
                        file_location = f"static/uploads/{img_file.filename}"
                        with open(file_location, "wb+") as file_object:
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
            return templates.TemplateResponse("pages/add_product.html", {"request": request, "user_data": user_exist,
                                                                      "category_data": category_data, "success": success})

    return RedirectResponse(url=app.url_path_for('login_api'), status_code=status.HTTP_303_SEE_OTHER)


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
