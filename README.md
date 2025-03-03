# Installation
1. VM + environment 
```
python3 -m venv 2donet
cd 2donet/bin
source activate
pip install django 
```

2. Run server:
        `python manage.py runsever` start a server on  127.0.0.1:8000
   If this port is occupied try
   `pythyon manage.py runserver 127.0.0.1:8001` or anything else between  127.0.0.1:1024 and 127.0.0.1:9999
4. Admin access on 127.0.0.1:8000/admin

    db.sqlite3
    login:
        `admin`
    password:
        `12345678`

# Using
#### Django
#### SQLite
#### Materialize