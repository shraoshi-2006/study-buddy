from crud import create_user, get_user

create_user(
    "Sakib",
    "sakib@gmail.com",
    "123456"
)

user = get_user("sakib@gmail.com")

print(user.name)
print(user.email)