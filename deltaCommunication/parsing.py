# """
#     {"3-bit": [], "Mars": [], "Milkyway": [], "Snickers": []}\r\n" "{"3-bit": [], "Mars":
# """
#
# queue = []
#
# var = {"3-bit": [{"xmax": 10, "xmin": 5, "ymax": 10, "ymin": 5, "middle": (20, 50), "middle_transformed": (-10, -10)},
#        {"xmax": 10, "xmin": 5, "ymax": 10, "ymin": 5, "middle": (20, 50), "middle_transformed": (-100, -10)}],
#        "Mars": [],
#        "Milkyway": [{"xmax": 10, "xmin": 5, "ymax": 10, "ymin": 5, "middle": (20, 50), "middle_transformed": (80, -10)}],
#        "Snickers": []}
#
# # loop over every  chocolate bar
# for index, (name, detections) in enumerate(var.items()):
#     if detections:
#         for detection in detections:
#             x, y = detection['middle_transformed']
#             if (x, y, index) not in queue:
#                 queue.append((x, y, index))
#
# print(queue)


def create_commands(x, y):

    if x >= 0:
        x = str(x)
        missing = 4 - len(x)  # we want to achieve 4 digit format
        x = "+" + "0" * missing + x
    else:
        x = str(x)[1:]
        missing = 4 - len(x)
        x = "-" + "0" * missing + x

    if y >= 0:
        y = str(y)
        missing = 4 - len(y)  # we want to achieve 4 digit format
        y = "+" + "0" * missing + y
    else:
        y = str(y)[1:]
        missing = 4 - len(y)
        y = "-" + "0" * missing + y

    return x, y

print(create_commands(-4,3))