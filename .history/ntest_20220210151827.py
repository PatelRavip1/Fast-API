# new = {"ads": "asdf", "addas": "asdf"}
# new.pop("ads")
# print(new)

import json
firstName = "asd"
lastName = "asd"
email = "asd"
password = "asd"
organizationName = "asd"
data = json.dumps({
    "firstName": firstName,
    "lastName": lastName,
    "email": email,
    "password": password,
    "organization": organizationName
})
print(str(data))
