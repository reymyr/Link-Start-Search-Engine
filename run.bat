@ECHO OFF
CALL env\Scripts\activate
explorer "http://localhost:5000"
flask run