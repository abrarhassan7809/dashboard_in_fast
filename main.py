import datetime
import uvicorn
from fastapi import FastAPI, Request, status, HTTPException, Form, Depends
from authentication.oauth_token import create_token
from authentication.password_hashing import Hash
from database_config import db_models, db_creation
from database_config.db_creation import Base, engine
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from verifications.email_and_pass_verification import email_checker, password_checker

app = FastAPI()
Base.metadata.create_all(engine)

templates = Jinja2Templates(directory='templates')
app.mount("/static", StaticFiles(directory="static"), name="static")


# =========register and login===========
@app.get("/logout/")
async def logout(request: Request):
    response = RedirectResponse(url=app.url_path_for("login_api"))
    response.delete_cookie('token')
    request.cookies.pop('token')
    # response.delete_cookie("remember_me")
    # request.cookies.pop('remember_me')
    # response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


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
        if password_checker(password):
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
                    current_time = datetime.datetime.now()
                    new_user = db_models.User(first_name=first_name, last_name=last_name, email=email,
                                              password=Hash.bcrypt(password),
                                              confirm_password=Hash.bcrypt(password), user_token=None,
                                              created_at=current_time, is_admin=False, user_status=False)

                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)

                    return templates.TemplateResponse("pages/sign-in.html", {"request": request, "success": message})

    return RedirectResponse(url=app.url_path_for('register_api'))


@app.get('/', status_code=status.HTTP_200_OK)
async def login_api(request: Request):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("dashboard_api"))

    return templates.TemplateResponse("pages/sign-in.html", {"request": request})


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

                    # if remember_me:
                    #     response.set_cookie(key="remember_me", value="true")

                    return response

    return templates.TemplateResponse("pages/sign-in.html", {"request": request})


# ========user data=========
@app.get('/add_user/')
async def add_user(request: Request):
    is_token = request.cookies.get('token')
    if is_token:
        message = ''
        return templates.TemplateResponse("pages/add-user.html", {"request": request, "error": message})

    return RedirectResponse(url=app.url_path_for("login_api"))


@app.post('/add_user/')
async def add_user(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                       email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...),
                       db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        return RedirectResponse(url=app.url_path_for("dashboard_api"))

    if email_checker(email):
        if password_checker(password):
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
                    current_time = datetime.datetime.now()
                    new_user = db_models.User(first_name=first_name, last_name=last_name, email=email,
                                              password=Hash.bcrypt(password),
                                              confirm_password=Hash.bcrypt(password), user_token="",
                                              created_at=current_time, is_admin=False, user_status=False)

                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)

                    return templates.TemplateResponse("pages/sign-in.html", {"request": request, "success": message})

    return RedirectResponse(url=app.url_path_for('register_api'))


@app.get('/get_all_user/', status_code=status.HTTP_200_OK)
async def get_all_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).all()
        for data in user_exist:
            print(data.email)
        return templates.TemplateResponse("pages/tables.html", {"request": request, 'user_data': user_exist})

    return RedirectResponse(url=app.url_path_for('login_api'))


@app.get('/update_user/', status_code=status.HTTP_200_OK)
async def update_user(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()

        if user_exist:
            return templates.TemplateResponse("pages/profile.html", {"request": request, "user_data": user_exist})

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
            return templates.TemplateResponse("pages/profile.html", {"request": request, "user_data": user_exist,
                                                                     "success": message})

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


# ========dashboard data=========
@app.get('/dashboard/', status_code=status.HTTP_200_OK)
async def dashboard_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            return templates.TemplateResponse("pages/dashboard.html", {"request": request, "user_data": user_exist})

    return RedirectResponse(url=app.url_path_for('login_api'))


@app.post('/dashboard/', status_code=status.HTTP_200_OK)
async def dashboard_api(request: Request, db: Session = Depends(db_creation.get_db)):
    is_token = request.cookies.get('token')
    if is_token:
        user_exist = db.query(db_models.User).filter(db_models.User.user_token == is_token).first()
        if user_exist:
            return templates.TemplateResponse("pages/dashboard.html", {"request": request, "user_data": user_exist})

    return RedirectResponse(url=app.url_path_for('login_api'))


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
