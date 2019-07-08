# Item-Catalog
Create a bookstore application where users can add, edit, and delete book categories and books in the bookstore.
## Setup and run the project
### Prerequisites
* Python 2.7
* Vagrant
* VirtualBox

### How to Run
1. Install VirtualBox and Vagrant
2. Clone this repo
3. Unzip and place the Item Catalog folder in your Vagrant directory
4. Launch Vagrant
```
$ Vagrant up 
```
5. Login to Vagrant
```
$ Vagrant ssh
```
6. Change directory to `/vagrant`
```
$ Cd /vagrant
```
7. Initialize the database
```
$ Python database_setup.py
```
8. Populate the database with some initial data
```
$ Python categories.py
```
9. Launch application
```
$ Python project.py
```
10. Open the browser and go to http://localhost:5000

### JSON endpoints
#### Returns JSON of all categories

```
/home/JSON
```
#### Returns JSON of a specific book

```
/home/<int:categories_id>/book/<int:book_id>/JSON
```
#### Returns JSON of a category

```
/home/<int:category_id>/book/JSON
```
