from fastapi import HTTPException,  status, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import dotenv_values
import jwt
from models import Session, sessionPydantic

configCredentials = dict(dotenv_values(".env"))
pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class AuthHandler():
    def getPasswordHash(self, password):
        return pwdContext.hash(password)

    def verifyPassword(self, plainPassword, hashedPassword):
        return pwdContext.verify(plainPassword, hashedPassword)

    def getToken(self, auth: HTTPAuthorizationCredentials = Security(security)):
        return auth.credentials

    async def verifyToken(self, encodedJwt: str):  # for email of change password
        payload = jwt.decode(
            encodedJwt, configCredentials['SECRET'], algorithms=["HS256"])
        return payload.get('id')

    async def SessionOut(self, token):
        sessionUpdate = {"status": False,
                         "expiredAt": datetime.now(), "updatedAt": datetime.now()}
        session = await Session.get(accessToken=token)
        if session.status:
            await session.update_from_dict(sessionUpdate)
            await session.save()
            response = await sessionPydantic.from_tortoise_orm(session)

    async def decodeToken(self, token):
        try:
            payload = jwt.decode(
                token, configCredentials['SECRET'], algorithms=['HS256'])
            return payload['id']
        except jwt.ExpiredSignatureError:
            await self.SessionOut(token)
            raise HTTPException(
                status_code=401, detail='Signature has expired')
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail='Invalid token')

    async def authWrapper(self, auth: HTTPAuthorizationCredentials = Security(security)):
        return await self.decodeToken(auth.credentials)

    async def tokenGenerator(self, email: str, id1: int):
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'email': email,
            'id': id1
        }
        return jwt.encode(
            payload,
            configCredentials["SECRET"],
            algorithm='HS256'
        )
