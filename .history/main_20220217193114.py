from asyncio.windows_events import NULL
from typing import Optional
from fastapi import Body, FastAPI, Depends, File, UploadFile, Request, Header
from pydantic import BaseModel, EmailStr
from models import *
from emails import *
from auth import *
from tortoise.contrib.fastapi import register_tortoise
from fastapi.staticfiles import StaticFiles
from PIL import Image
from fastapi.responses import HTMLResponse
import secrets

app = FastAPI()
# app.include_router(prefix="/new")

rex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

authHandler = AuthHandler()


class signUpData(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str
    organization: Optional[str]


@ app.post('/SignUp', tags=['Auth'], status_code=status.HTTP_201_CREATED)
async def userRegistration(user: signUpData):
    userInfo = dict(user)
    if userInfo["firstName"].isalpha() and userInfo["lastName"].isalpha():
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="First Name or Last Name is not valid",
        )
    password = authHandler.getPasswordHash(userInfo['password'])
    try:  # if same email is added then there will be error of unique constrain
        organization = await Organization.get(organizationName=userInfo['organization'])
        currentOrganization = await organizationPydantic.from_tortoise_orm(organization)
    except:
        organizationInfo = {"organizationName": userInfo['organization']}
        organizationObj = await Organization.create(**organizationInfo)
        currentOrganization = await organizationPydantic.from_tortoise_orm(organizationObj)

    userInfo.pop("password")
    userInfo.pop("organization")
    try:
        # user
        userObj = await User.create(**userInfo)
        newUser = await userPydantic.from_tortoise_orm(userObj)
        # password
        userCredInfo = {"userId_id": newUser.id, "password": password}
        userCred = await UserCredentials.create(**userCredInfo)
        await userCredentialsPydanticIn.from_tortoise_orm(userCred)
    except:
        userObj = await User.get(email=userInfo["email"])
        connectiobj = await OrganizationUserConnection.filter(userId_id=userObj.id)
        for i in connectiobj:
            if i.organizationId_id == currentOrganization.id:
                raise HTTPException(
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    detail="User already exists with this email in this organistion",
                )
        newUser = await userPydantic.from_tortoise_orm(userObj)
    # organizationuserconnection
    organizationuserconnectionInfo = {
        "organizationId_id": currentOrganization.id, "userId_id": newUser.id}
    organizationuserconnectionObj = await OrganizationUserConnection.create(
        **organizationuserconnectionInfo)
    await organizationUserConnectionPydanticIn.from_tortoise_orm(organizationuserconnectionObj)
    return {"status": "ok", "User": f"{newUser}", "Organization": f"{currentOrganization}"}


class loginData(BaseModel):
    email: EmailStr
    password: str


@ app.post('/login', tags=['Auth'])
async def userLogin(login: loginData):
    email = login.email
    password = login.password
    try:
        user = await User.get(email=email)
        usercredentials = await UserCredentials.get(userId_id=user.id)
        if user and authHandler.verifyPassword(password, usercredentials.password):
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = await Session.filter(userId_id=user.id)
    for i in session:
        sessionDict = dict(i)
        if sessionDict["status"]:
            return "already logged in"

    token = await authHandler.tokenGenerator(email, user.id)

    sessionObj = await Session.create(
        accessToken=token, status=True, userId=user)
    session = await sessionPydanticIn.from_tortoise_orm(sessionObj)
    return {'user': user, 'Session': session}


@ app.post('/SessionList', tags=['Users'],)
async def sessionList(accessToken=Depends(authHandler.getToken),
                      userId=Depends(authHandler.authWrapper)):
    try:
        session = await Session.get(accessToken=accessToken)
# will need session status as it say user logged out or not but authWrapper cant
        if session.status:
            user = await User.get(id=userId)
            sessionList = await Session.filter(userId_id=userId)
            return {'user': user, 'sessionList': sessionList}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Not authenticated to perform this action",
                                headers={"WWW-Authenticate": "Bearer"},)
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"},
        )


@ app.post('/whoAmI', tags=['Users'])
async def whoAmI(accessToken=Depends(authHandler.getToken),
                 userId=Depends(authHandler.authWrapper)):
    try:
        session = await Session.get(accessToken=accessToken)
        if session.status:
            user = await User.get(id=userId)
            return {'user': user}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Not authenticated to perform this action",
                                headers={"WWW-Authenticate": "Bearer"},)
    except:  # not valid token
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated to perform this action",
                            headers={"WWW-Authenticate": "Bearer"},)


@ app.post('/logout', tags=['Users'])
# Depends on getToken function because logut donot need to check if token is expired
async def userLogout(accessToken=Depends(authHandler.getToken)):
    sessionUpdate = {"status": False,
                     "expiredAt": datetime.now(), "updatedAt": datetime.now()}
    session = await Session.get(accessToken=accessToken)
    if session.status:
        await session.update_from_dict(sessionUpdate)
        await session.save()
        response = await sessionPydantic.from_tortoise_orm(session)
        return{'status': 'ok', 'data': response}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def userInOrg(organizationId: int, userId: int):
    conn = await OrganizationUserConnection.filter(userId_id=userId)
    isUserinOrg = False
    for i in conn:
        if i.organizationId_id == organizationId:
            isUserinOrg = True
        else:
            pass
    return isUserinOrg


@app.post('/inviteUser', tags=['Users'])
async def inviteUser(organizationId: int = Header(None),
                     userId=Depends(authHandler.authWrapper),
                     email: EmailStr = Body(None),
                     role=Body(None)):
    token = await sendEmail("invite", [email], userId)
    if token:
        if await userInOrg(organizationId, userId):
            inviteObj = await Invite.create(
                inviteToken=token, role=role, email=email, organizationId_id=organizationId)
            await invitePydanticIn.from_tortoise_orm(inviteObj)
            return token
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated to perform this action",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        return token


@app.get('/inviteUser/tokenValid/{token}', tags=['Users'])
async def sendSignUpPage(token: str):
    try:
        payload = jwt.decode(
            token,  configCredentials['SECRET'], algorithms=['HS256'])
        html = open("./templates/InviteUser.html", mode="r")
        return HTMLResponse(content=html.read(), status_code=200)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail='Signature has expired Please Contact Company User')
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail='Invalid token')


class acceptUserData(BaseModel):
    email: str
    password: str
    firstName: str
    lastName: str
    inviteStatus: str


@app.post('/acceptUser', tags=['Users'])
async def acceptUser(acceptUserData: acceptUserData):
    invite = await Invite.get(email=acceptUserData.email, inviteStatus="pending")
    # organization = await Organization.get(id=invite.organizationId_id)
    if acceptUserData.inviteStatus == 'Accepted':
        # firstName = acceptUserData.firstName
        # lastName = acceptUserData.lastName
        # email = acceptUserData.email
        # password = acceptUserData.password
        # organizationName = organization.organizationName
        # data = json.dumps({
        #     "firstName": firstName,
        #     "lastName": lastName,
        #     "email": email,
        #     "password": password,
        #     "organization": organizationName
        # })

        # return email
        # requests.request("POST", "http://127.0.0.1:8000/SignUp", headers={
        #     'accept': 'application/json',
        #     'Content-Type': 'application/json'
        # }, data=data)
        invite.inviteStatus = 'Accepted'
        await invite.save()
        return "ok Accepted"
    elif acceptUserData.inviteStatus == 'Rejected':
        invite.inviteStatus = 'Rejected'
        await invite.save()
        return "ok Rejected"
    else:
        return'not valid status'


@ app.post('/forgotPassword', tags=['Users'])
async def forgotPassword(email: EmailStr = Body(None)):
    user = await User.get(email=email)
    return maketoken(user.id)
    if user:
        return await sendForgotPasswordEmail([user.email], user)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid email",
            headers={"WWW-Authenticate": "Bearer"},
        )


class resetPasswordModel(BaseModel):
    newPassword: str
    confirmPassword: str


@ app.post('/ResetPassword', tags=['Users'], response_class=HTMLResponse)
async def resetPassword(resetPassword: resetPasswordModel, token: str = Header(None)):
    {"newPassword": "sa", "confirmPassword": "aa"}
    if resetPassword.newPassword == resetPassword.confirmPassword:
        # try:
        userId = await authHandler.verifyToken(token)
        user = await User.get(id=userId)
        userCredentials = await UserCredentials.get(userId_id=userId)
        update = {"password": authHandler.getPasswordHash(
            resetPassword.newPassword)}
        await userCredentials.update_from_dict(update)
        await userCredentials.save()
        # find statse code for changed password
        return f"Password changed for {str(user.email)}"
    else:
        return'password did not match'  # find proper exeption


@ app.post("/products", tags=["product"])
async def addNewProduct(product: productPydanticIn, organizationId: int = Header(1),
                        accessToken=Depends(authHandler.getToken),
                        userId=Depends(authHandler.authWrapper)):
    session = await Session.get(accessToken=accessToken)
    if await userInOrg(organizationId, userId) and session.status:
        product = product.dict(exclude_unset=True)
        if product['originalPrice'] > 0:  # dont devide by 0
            product["percentageDiscount"] = (
                (product["originalPrice"] - product['newPrice']) /
                product['originalPrice']) * 100
        productObj = await Product.create(**product, organizationId_id=organizationId)
        productObj = await productPydantic.from_tortoise_orm(productObj)
        return {"status": "ok", "data": productObj}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated to perform this action",
                            headers={"WWW-Authenticate": "Bearer"},)


@ app.get("/products", tags=["product"])
async def getProducts(organizationId: int = Header(1), accessToken=Depends(authHandler.getToken),
                      userId=Depends(authHandler.authWrapper)):
    session = await Session.get(accessToken=accessToken)
    if await userInOrg(organizationId, userId) and session.status:
        response = await Product.filter(organizationId_id=organizationId)
        return {"status": "ok ", "data": response}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated to perform this action",
                            headers={"WWW-Authenticate": "Bearer"},)


@ app.get("/products/{id}", tags=["product"])
async def specific_product(id: int, organizationId: int = Header(1),
                           accessToken=Depends(authHandler.getToken),
                           userId=Depends(authHandler.authWrapper)):
    session = await Session.get(accessToken=accessToken)
    if await userInOrg(organizationId, userId) and session.status:
        try:
            product = await Product.get(id=id)
            org = await product.organizationId
            if organizationId == org.id:
                response = await productPydantic.from_queryset_single(Product.get(id=id))
                print(type(response))
                return {"status": "ok",
                        "data":
                        {"product": response,
                         "organization": {
                             "organization": org.organizationName
                         }}}
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="This product does on belong to your organization",
                                    headers={"WWW-Authenticate": "Bearer"},)

        except:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No product with given id",
                                headers={"WWW-Authenticate": "Bearer"},)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No product with given id",
                            headers={"WWW-Authenticate": "Bearer"},)


@ app.put('/product/{id}', tags=["product"])
async def update_product(id: int, updateInfo: productPydanticIn,
                         organizationId: int = Header(1),
                         accessToken=Depends(authHandler.getToken),
                         userId=Depends(authHandler.authWrapper)):
    session = await Session.get(accessToken=accessToken)
    if await userInOrg(organizationId, userId) and session.status:
        try:
            product = await Product.get(id=id)
        except:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No product with given Id",
                                headers={"WWW-Authenticate": "Bearer"},)
        org = await product.organizationId
        if organizationId == org.id:
            updateInfo = updateInfo.dict(exclude_unset=True)
            updateInfo['updatedAt'] = datetime.now()
            if updateInfo["originalPrice"] > 0:
                updateInfo['percentageDiscount'] = (
                    (updateInfo['originalPrice']-updateInfo['newPrice'])
                    / updateInfo['originalPrice'])*100
                product = await product.update_from_dict(updateInfo)
                response = await productPydantic.from_tortoise_orm(product)
                return {'status': 'ok', 'data': response}
            else:
                raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                    detail="Product Price can not be zero ",
                                    headers={"WWW-Authenticate": "Bearer"},)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="This product does on belong to your organization",
                                headers={"WWW-Authenticate": "Bearer"},)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated to perform this action",
                            headers={"WWW-Authenticate": "Bearer"},)


@ app.post("/uploadfile/product/{id}", tags=["product"])
async def createUploadFile(id: int, organizationId: int = Header(1),
                           file: UploadFile = File(...),
                           accessToken=Depends(authHandler.getToken),
                           userId=Depends(authHandler.authWrapper)):
    session = await Session.get(accessToken=accessToken)
    if await userInOrg(organizationId, userId) and session.status:
        FILEPATH = "./static/images/"
        filename = file.filename
        extension = filename.split(".")[1]
        if extension not in ["jpg", "png"]:
            return {"status": "error", "detail": "file extension not allowed"}
        tokenName = secrets.token_hex(10)+"."+extension
        generatedName = FILEPATH + tokenName
        fileContent = await file.read()
        with open(generatedName, "wb") as file:
            file.write(fileContent)
        # pillow
        img = Image.open(generatedName)
        img = img.resize(size=(200, 200))
        img.save(generatedName)
        file.close()

        try:
            product = await Product.get(id=id)
        except:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No product with given Id",
                                headers={"WWW-Authenticate": "Bearer"},)
        org = await product.organizationId
        if organizationId == org.id:
            product.productImage = tokenName
            product.updatedAt = datetime.now()
            await product.save()
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="This product does on belong to your organizationn",
                                headers={"WWW-Authenticate": "Bearer"},)

        fileUrl = "localhost:8000" + generatedName[1:]
        return {"status": "ok", "filename": fileUrl}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated to perform this action",
                            headers={"WWW-Authenticate": "Bearer"},)


@ app.delete("/products/{id}", tags=["product"])
async def deleteProduct(id: int, organizationId: int = Header(1),
                        accessToken=Depends(authHandler.getToken),
                        userId=Depends(authHandler.authWrapper)):
    session = await Session.get(accessToken=accessToken)
    if await userInOrg(organizationId, userId) and session.status:
        try:
            product = await Product.get(id=id)
        except:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No product with given Id",
                                headers={"WWW-Authenticate": "Bearer"},)
        org = await product.organizationId
        if organizationId == org.id:
            await product.delete()
            return {"status": product}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="This product does on belong to your organization",
                                headers={"WWW-Authenticate": "Bearer"},)

    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated to perform this action",
                            headers={"WWW-Authenticate": "Bearer"},)


register_tortoise(
    app,
    db_url='sqlite://data/database.sqlite3',
    modules={'models': ['models']},
    generate_schemas=True,
    add_exception_handlers=True
)
app.mount("/static", StaticFiles(directory="static"), name="static")
