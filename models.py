from email.policy import default
from tortoise import Model, fields
from datetime import datetime, timedelta
from tortoise.contrib.pydantic import pydantic_model_creator


class User(Model):
    id = fields.IntField(pk=True, index=True)
    firstName = fields.CharField(max_length=20)
    lastName = fields.CharField(max_length=20)
    email = fields.CharField(max_length=100, unique=True)
    joinDate = fields.DatetimeField(default=datetime.now())


userPydantic = pydantic_model_creator(User, name="User")
userPydanticIn = pydantic_model_creator(
    User, name="UserIn", exclude=("id", "joinDate",))


class UserCredentials(Model):
    id = fields.IntField(pk=True, index=True)
    userId = fields.ForeignKeyField(
        'models.User', related_name='usercredentials')
    password = fields.CharField(max_length=100)


userCredentialsPydantic = pydantic_model_creator(
    UserCredentials, name="UserCredentials")
userCredentialsPydanticIn = pydantic_model_creator(
    UserCredentials, name="UserCredentialsIn", exclude_readonly=True,
    exclude=("id", "userId"))


class OrganizationUserConnection(Model):
    id = fields.IntField(pk=True, index=True)
    organizationId = fields.ForeignKeyField(
        'models.Organization', related_name='organizationUserConnection')
    userId = fields.ForeignKeyField(
        'models.User', related_name='organizationUserConnection')
    role = fields.CharField(max_length=50, default="Admin")
    isOwner = fields.BooleanField(default=True)


organizationUserConnectionPydantic = pydantic_model_creator(
    OrganizationUserConnection, name="OrganizationUserConnection")
organizationUserConnectionPydanticIn = pydantic_model_creator(
    OrganizationUserConnection, name="OrganizationUserConnectionIn", exclude_readonly=True,
    exclude=("id", "isOwner"))


class Session(Model):
    id = fields.IntField(pk=True, index=True)
    accessToken = fields.CharField(max_length=500)
    userId = fields.ForeignKeyField(
        'models.User', related_name='session')
    createdAt = fields.DatetimeField(default=datetime.now())
    expiredAt = fields.DatetimeField(default=datetime.now())
    updatedAt = fields.DatetimeField(default=datetime.now())
    expireAt = fields.DatetimeField(
        default=datetime.now()+timedelta(days=1))
    status = fields.BooleanField(default=True)


sessionPydantic = pydantic_model_creator(Session, name="Session")
sessionPydanticIn = pydantic_model_creator(
    Session, name="Session", exclude_readonly=True,
    exclude=("id", "createdAt", "expiredAt", "updatedAt", "expireAt", "status"))


class Organization(Model):
    id = fields.IntField(pk=True, index=True)
    organizationName = fields.CharField(max_length=20, unique=True)
    createdAt = fields.DatetimeField(default=datetime.now())
    updatedAt = fields.DatetimeField(default=datetime.now())


organizationPydantic = pydantic_model_creator(
    Organization, name="Organization")
organizationPydanticIn = pydantic_model_creator(
    Organization, name="OrganizationIn", exclude_readonly=True,
    exclude=("id", "createdAt", "updatedAt"))


class Product(Model):
    id = fields.IntField(pk=True, index=True)
    name = fields.CharField(max_length=100)
    organizationId = fields.ForeignKeyField(
        'models.Organization', related_name='product')
    originalPrice = fields.DecimalField(max_digits=12, decimal_places=2)
    newPrice = fields.DecimalField(max_digits=12, decimal_places=2)
    percentageDiscount = fields.IntField(default=0)
    categoryName = fields.CharField(max_length=20, index=True)
    description = fields.CharField(max_length=1000)
    productImage = fields.CharField(max_length=200, default="Default.jpg")
    createdAt = fields.DatetimeField(default=datetime.now)
    updatedAt = fields.DatetimeField(default=datetime.now)


productPydantic = pydantic_model_creator(Product, name="Product")
productPydanticIn = pydantic_model_creator(
    Product, name="ProductIn", exclude=('id', 'percentageDiscount', 'productImage', 'createdAt', 'updatedAt', 'organizationId',))


class Invite(Model):
    id = fields.IntField(pk=True, index=True)
    email = fields.CharField(max_length=100)
    inviteToken = fields.CharField(max_length=500)
    organizationId = fields.ForeignKeyField(
        'models.Organization', related_name='invite')
    inviteStatus = fields.CharField(max_length=50, default='pending')
    expireAt = fields.DatetimeField(default=datetime.now()+timedelta(days=1))


invitePydantic = pydantic_model_creator(Invite, name="Invite")
invitePydanticIn = pydantic_model_creator(
    Invite, name="InviteIn", exclude=('id'))
