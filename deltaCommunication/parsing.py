"""
    {"3-bit": [], "Mars": [], "Milkyway": [], "Snickers": []}\r\n" "{"3-bit": [], "Mars":
"""

queue = []

var = {"3-bit": [{"xmax": 10, "xmin": 5, "ymax": 10, "ymin": 5, "middle": (20, 50), "middle_transformed": (-10, -10)},
       {"xmax": 10, "xmin": 5, "ymax": 10, "ymin": 5, "middle": (20, 50), "middle_transformed": (-100, -10)}],
       "Mars": [],
       "Milkyway": [{"xmax": 10, "xmin": 5, "ymax": 10, "ymin": 5, "middle": (20, 50), "middle_transformed": (80, -10)}],
       "Snickers": []}

# loop over every  chocolate bar
for index, (name, detections) in enumerate(var.items()):
    if detections:
        for detection in detections:
            x, y = detection['middle_transformed']
            if (x, y, index) not in queue:
                queue.append((x, y, index))

print(queue)
