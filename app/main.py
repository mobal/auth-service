import uvicorn
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()


@app.get('/')
async def hello():
    return 'hello, world!'


handler = Mangum(app)

if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
