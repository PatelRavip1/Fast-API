from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from auth import *


configCredentials = dict(dotenv_values(".env"))
conf = ConnectionConfig(
    MAIL_USERNAME=configCredentials["EMAIL"],
    MAIL_PASSWORD=configCredentials["PASS"],
    MAIL_FROM=configCredentials["EMAIL"],
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True
)


def maketoken(instanceId: int):
    tokenData = {"id": instanceId}
    token = jwt.encode(tokenData, configCredentials["SECRET"])
    return token


def makeTokenForInvite(email, instanceId):
    payload = {
        'exp': datetime.utcnow() + timedelta(days=1, seconds=5),
        'iat': datetime.utcnow(),
        'email': email,
        'id': instanceId
    }
    return jwt.encode(
        payload,
        configCredentials["SECRET"],
        algorithm='HS256'
    )


async def sendEmail(emailMessage: str, email: list, instanceId: int):
    if emailMessage == "forget":
        token = maketoken(instanceId)
    elif emailMessage == "invite":
        token = makeTokenForInvite(email, instanceId)
    else:
        return
    template = f"""
        <!DOCTYPE html>
        <html>
        <head>
        </head>
        <body>
            <div style=" display: flex; align-items: center; justify-content: center; flex-direction: column;">
                <h3> Account Verification </h3>
                <br>
                <p>click on the link below to verify your account</p> 
                <form>
                 <input type="password" id="pass" name="pass"><br>
                 <input type="submit">
                </form>
                <a style="margin-top:1rem; padding: 1rem; border-radius: 0.5rem; font-size: 1rem; text-decoration: none; background: #0275d8; color: white;"
                 
                 href="file:///P:/newProject/templates/passwordChanged.html">
                                
                    Verify your email
                <a>
            </div>
        </body>
        </html>
    """
    template2 = f"""
        <!DOCTYPE html>
        <html>
        <head>
        </head>
        <body>
            <div style=" display: flex; align-items: center; justify-content: center; flex-direction: column;">
                <a style="margin-top:1rem; padding: 1rem; border-radius: 0.5rem; font-size: 1rem; text-decoration: none; background: #0275d8; color: white;"
                 href ="http://localhost:8000/AcceptUser/{token}">         
                <a>
            </div>
        </body>
        </html>
    """

    # href="http://localhost:8000/ResetPassword/-d '{body}'">

    # should take user to new page to let them enter new password
    if emailMessage == "forget":
        message1 = MessageSchema(
            subject="Account Verification Mail",
            recipients=email,
            body=template,
            subtype="html"
        )
    elif emailMessage == "invite":
        message1 = MessageSchema(
            subject="Account Verification Mail",
            recipients=email,
            body=template2,
            subtype="html"
        )
    else:
        return
    fm = FastMail(conf)
    await fm.send_message(message1)
    return token
