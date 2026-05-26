from fastapi import APIRouter

router = APIRouter(tags=["Health Check"])

@router.get("/")
async def get_hello() -> str:
    """
    Endpoint raiz correspondente ao método getHello() do AppController.
    """
    return "Hello World!"