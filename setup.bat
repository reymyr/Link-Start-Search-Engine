@ECHO OFF
ECHO Setting up virtual environment...
CD src
py -m venv env
ECHO Installing requirements...
CALL env\Scripts\activate
pip install -r requirements.txt
ECHO Setup complete, running app...
CD ..
CALL run
