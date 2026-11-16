from fastapi import HTTPException
class DomainError(ValueError):
    def __init__(self,code,detail):
        self.code=code
        super().__init__(detail)
def reject(code,detail):
    raise DomainError(code,detail)
def http_error(exc):
    return HTTPException(409 if exc.code in ("STALE_VERSION","SUPERSEDED") else 422,detail={"code":exc.code,"message":str(exc)})
