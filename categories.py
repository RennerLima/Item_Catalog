from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import User, Base, Book, Category

engine = create_engine('sqlite:///bookcatalog.db')

# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

# Bind the above engine do a session.
Session = sessionmaker(bind=engine)

# Create a Session Object.
session = Session()

# Create dummy user
user1 = User(
    name="admin",
    email="rennertft@gmail.com",
    picture='https://pbs.twimg.com/profile_images/2671170543/18d\
    ebd694829ed78203a5a36dd364160_400x400.png'
    )
session.add(user1)
session.commit()

# Category Science Fiction
category1 = Category(user_id=1, name="Science Fiction")

session.add(category1)
session.commit()

book1 = Book(
    user_id=1,
    name="Leviathan Awakes",
    description="Two hundred years after migrating into space, mankind is in turmoil. \
    When a reluctant ship's captain and washed-up detective \
    find themselves involved in the case of a missing girl, \
    what they discover brings our solar system to the brink of \
    civil war, and exposes the greatest conspiracy in human history.",
    price="$29.99",
    category=category1,
)

session.add(book1)
session.commit()

# Category History

category2 = Category(
    name="History"
    )

session.add(category2)
session.commit()

book1 = Book(
    user_id=1,
    name="1776",
    description="Americas beloved and distinguished historian presents,\
    in a book of breathtaking excitement, drama, and narrative force,\
    the stirring story of the year of our nations birth interweaving,\
    on both sides of the Atlantic the \
    actions and decisions that led Great Britain\
    to undertake a war against her rebellious colonial subjects and that\
    placed Americas survival in the hands of George Washington.",
    price="$21.99",
    category=category2
    )

session.add(book1)
session.commit()


print("Database has been populated!")
