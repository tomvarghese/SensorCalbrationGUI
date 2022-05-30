How to generate the exe on a different machine?

either 
1- use the normal python and run pyinstaller SensorCalibration.spec

not sure why the terminal not seeing the link to pyinstaller, 
but if u use the other method
python -m PyInstaller SensorCalibration.spec
(Case sensitive) 

2- do the same as 1 but from virtual env (sth like venv) (prefered to get only used modules packaged)
virtual env is made by 
a. pip install virtualenv
b. virtualenv <venv name>
c. <venv name>\Scrtips\activate.bat
d. python -m pip install -r requirements.txt
e. python -m PyInstaller SensorCalibration.spec