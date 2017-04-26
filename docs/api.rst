API
=========

Endpoints
---------
 * "silo": "https://tables.toladata.io/api/silo/",
 * "public_tables": "https://tables.toladata.io/api/public_tables/",
 * "users": "https://tables.toladata.io/api/users/",
 * "read": "https://tables.toladata.io/api/read/",
 * "readtype": "https://tables.toladata.io/api/readtype/",
 * "tag": "https://tables.toladata.io/api/tag/"
 * "owners": "https://tables.toladata.io/api/owners"
 * "boards": "https://tables.toladata.io/api/boards"
 * "graphs": "https://tables.toladata.io/api/graphs"
 * "graphmodels": "https://tables.toladata.io/api/graphmodels"
 * "items": "https://tables.toladata.io/api/items"
 * "graphinputs": "https://tables.toladata.io/api/graphinputs"
 * "boardsilos": "https://tables.toladata.io/api/boardsilos"

 

Silo (Represents a Table)

Example
-------
::
    curl -H "Authorization: Token adkai39a9sdfj239m0afi2" https://tables.toladata.io/api/silo/{{siloid}}/`

GET /api/silo/

HTTP 200 OK
Allow: GET, POST, OPTIONS
Content-Type: application/json
Vary: Accept

::
    {
        "owner": {
            "url": "http://tables.toladata.io/api/users/2/",
            "password": "!kBeo6116YCeMonUVGpB2Q9ONRh387XLtPNy0u6CJ",
            "last_login": "2017-01-13T17:00:53Z",
            "is_superuser": false,
            "username": "glindf9003af87068415a",
            "first_name": "Greg",
            "last_name": "Lind",
            "email": "glind@mercycorps.org",
            "is_staff": false,
            "is_active": true,
            "date_joined": "2015-10-08T00:50:29Z",
            "groups": [],
            "user_permissions": []
        },
        "name": "NS Security Incident",
        "reads": [
            {
                "url": "http://tables.toladata.io/api/read/10/",
                "read_name": "NS Security Incident",
                "description": "",
                "read_url": "https://api.ona.io/api/v1/data/132211",
                "resource_id": null,
                "gsheet_id": null,
                "username": null,
                "password": null,
                "token": null,
                "file_data": null,
                "autopull_frequency": "daily",
                "autopush_frequency": null,
                "create_date": "2016-07-02T19:48:49Z",
                "edit_date": "2016-08-24T17:54:52Z",
                "owner": "http://tables.toladata.io/api/users/2/",
                "type": "http://tables.toladata.io/api/readtype/1/"
            },
            {
                "url": "http://tables.toladata.io/api/read/79/",
                "read_name": "NS Security Incident",
                "description": "Google Spreadsheet Export",
                "read_url": "https://docs.google.com/a/mercycorps.org/spreadsheets/d/1x7n0JViOqQB90W-G38QR5D2lHfJQWyZpkOUZfypWY0Y/",
                "resource_id": "1x7n0JViOqQB90W-G38QR5D2lHfJQWyZpkOUZfypWY0Y",
                "gsheet_id": null,
                "username": null,
                "password": null,
                "token": null,
                "file_data": null,
                "autopull_frequency": null,
                "autopush_frequency": null,
                "create_date": "2016-10-10T08:12:26Z",
                "edit_date": "2016-10-10T08:12:26Z",
                "owner": "http://tables.toladata.io/api/users/2/",
                "type": "http://tables.toladata.io/api/readtype/3/"
            }
        ],
        "description": null,
        "create_date": null,
        "id": 12,
        "data": "http://tables.toladata.io/api/silo/12/data/",
        "shared": [],
        "tags": [],
        "public": false
    },
