# Streaming OAK-D prediction and TCP communication with robot Delta
Stream OAK-D camera prediction while running a custom Yolov5 model
This repository is used is used for autonomous sorting of choclate bars by delta type robot

# Installation
```python3 -m pip install -r requirements.txt```

# Run
```python3 app.py```

# See result
Video: [your_ip:8090](http://localhost:8090)

Prediction: [localhost:8070](http://localhost:8070)

Warped video [your_ip:8080](http://localhost:8080)

# Run automatic sort (need app.py running first)
```python3 communication/deltaCommunication.py```

# Run sorting without vision system, hardcoded pickup location
```python3 communication/deltaCommunicationNoVS.py```
