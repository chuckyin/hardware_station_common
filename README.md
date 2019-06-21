# Hardware Station Common

![Logo](https://github.com/chuckyin/htc/blob/master/logo/Logo.png)\
Open-source framework focused on hardware automation station fast bring-up at component vendor: open, object-orientated and lightweight

## Overview
Hardware_station_common, as the name indicates, collects common attributes of hardware test stations in common such as, the graphic user interface, the logging function and scaffolding of the test station.
(1) Open: open to vendor to maintain the code base reduce the sustain support efforts and save the cost. \
(2) Object-orientated: Any component attributes/properties/methods will be strictly restricted \
(3) Lightweight: To make the framework maintainable, pylint will be strongly recommended to run code quality before implementation.

In the htc, the OOP principle is applied to every physical and virtual component. Fixture, DUT, station, the test_log, GUI.

## Nomenclature:
### DUT
Device under Test. 

### Equipment
The third party, usually off-shelf standard instruments to be used in station to interact DUT. Examples: Agilent Power Supply, NI-DAQ, Industry cameras. 

### Fixture
The customized hardware to bind DUT/Equipment/PC, with basic functions such as loading/unoading/scan DUT, power cycle equipment, etc. 

### Station
Station = DUT + Fixture + Equipment

## Installation:
OpenExec can be run by external python; however, setting up a virtual environment to maintain a clean environment is recommended. If the dependencies are not installed yet, please install the dependencies:
```sh
pip install hardware_station_common
```

## Usage:

``` sh
import hardware_station_common
```


## Escalation/Suggestion/
[mailto:chuckyeyin@gmail.com](mailto:chuckyeyin@gmail.com)

