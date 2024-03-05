import datetime
from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from authentication.oauth_token import create_access_token
from authentication.password_hashing import Hash
from authentication.get_oauth_user import get_current_user
from database_config import db_schemas, db_creation, db_models
from verifications.email_and_pass_verification import email_checker, password_checker

router = APIRouter(tags=['Authentication'])


@router.post('/user_register/', status_code=status.HTTP_200_OK)
async def user_register(request: db_schemas.Register, db: Session = Depends(db_creation.get_db)):
    if email_checker(request.email):
        if password_checker(request.password):
            user = db.query(db_models.Register).filter(db_models.Register.email == request.email).first()
            if user:
                return HTTPException(status_code=status.HTTP_226_IM_USED,
                                     detail='User already exist')
            else:
                if request.password != request.confirm_password:
                    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                         detail='Confirm password not matched')
                else:
                    current_time = datetime.datetime.now()
                    new_user = db_models.Register(first_name=request.first_name, last_name=request.last_name,
                                                  email=request.email, password=Hash.bcrypt(request.password),
                                                  confirm_password=Hash.bcrypt(request.password),
                                                  created_at=current_time, is_admin=False)

                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)

                    return HTTPException(status_code=status.HTTP_200_OK, detail='Successfully Account Created')

        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Password is mixture of number and alphabets and special character")

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email must be contain 'test@gmail.com'")


@router.post('/login/', response_model=db_schemas.Token, status_code=status.HTTP_200_OK)
async def user_login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(db_creation.get_db)):
    user = db.query(db_models.Register).filter(db_models.Register.email == request.username).first()

    if not email_checker(request.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Invalid Email and Password')

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Invalid Email and Password')

    if not Hash.verify(request.password, user.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Invalid Email and Password')

    access_token = create_access_token(data={"sub": user.email})

    return {'access_token': f'{access_token}', 'token_type': 'bearer'}


@router.get('/get_all_users/', status_code=status.HTTP_200_OK)
async def get_all_user(db: Session = Depends(db_creation.get_db),
                       current_user: db_schemas.Register = Depends(get_current_user)):
    user_exist = db.query(db_models.Register).filter(db_models.Register.email == current_user.email).first()
    if user_exist:
        all_users = db.query(db_models.Register).all()

        return all_users

    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Something went wrong')


@router.get('/get_user/', response_model=db_schemas.GetUser, status_code=status.HTTP_200_OK)
async def get_user(db: Session = Depends(db_creation.get_db),
                   current_user: db_schemas.Register = Depends(get_current_user)):
    user_exist = db.query(db_models.Register).filter(db_models.Register.email == current_user.email).first()

    if user_exist:
        return user_exist

    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Something went wrong')


@router.patch('/update_user/', status_code=status.HTTP_200_OK)
async def update_user(request: db_schemas.UpdateUser, db: Session = Depends(db_creation.get_db),
                      current_user: db_schemas.Register = Depends(get_current_user)):
    user_exist = db.query(db_models.Register).filter(db_models.Register.email == current_user.email)
    is_user = user_exist.first()

    if is_user:
        if request.password != request.confirm_password:
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Password must be same')

        if request.password is not None:
            request.password = Hash.bcrypt(request.password)

        if request.confirm_password is not None:
            request.confirm_password = Hash.bcrypt(request.confirm_password)

        user_exist.update(request.dict(exclude_unset=True))
        db.commit()

        return HTTPException(status_code=status.HTTP_200_OK, detail=f'Successfully updated')

    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'User not found')


@router.delete('/delete_user/{email}', status_code=status.HTTP_200_OK)
async def delete_user(email: str, db: Session = Depends(db_creation.get_db),
                      current_user: db_schemas.Register = Depends(get_current_user)):
    if not email_checker(email):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid Email')

    if email == current_user.email:
        user_exist = db.query(db_models.Register).filter(db_models.Register.email == email)
        user_exist.delete(synchronize_session=False)
        db.commit()

        return HTTPException(status_code=status.HTTP_200_OK, detail=f'Successfully Account Deleted')

    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'User not found')
