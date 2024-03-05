import uvicorn
from fastapi import FastAPI
from authentication import (login_api)
from database_config.db_creation import Base, engine

app = FastAPI()
Base.metadata.create_all(engine)

app.include_router(login_api.router)


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
