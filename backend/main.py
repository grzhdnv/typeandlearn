from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello World"}


@app.get("/translation")
def read_translation():
    return {"message": "Translation endpoint"}


# POST: to create data.
# GET: to read data.
# PUT: to update data.
# DELETE: to delete data.
