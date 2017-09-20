import cv2
import numpy as np
import tensorflow as tf

def visualize_gt_label(img_path, label_path):
    class_to_color = {"car": (255, 191, 0),
                      "cyclist": (0, 191, 255),
                      "pedestrian": (255, 0, 191)}

    img = cv2.imread(img_path, -1)

    with open(label_path) as label_file:
        for line in label_file:
            splitted_line = line.split(" ")
            bbox_class = splitted_line[0].lower().strip()
            if bbox_class not in ["car", "cyclist", "pedestrian"]:
                break
            x_left = int(float(splitted_line[4]))
            y_bottom = int(float(splitted_line[5]))
            x_right = int(float(splitted_line[6]))
            y_top = int(float(splitted_line[7]))

            cv2.rectangle(img, (x_left, y_top), (x_right, y_bottom), class_to_color[bbox_class], 2)

    img_with_bboxes = img
    return img_with_bboxes

def draw_bboxes(img, bboxes, class_labels, probs=None):
    class_label_to_string = {0: "car", 1: "pedestrian", 2: "cyclist"}
    class_to_color = {"car": (255, 191, 0),
                      "cyclist": (0, 191, 255),
                      "pedestrian": (255, 0, 191)}

    for bbox, class_label, prob in zip(bboxes, class_labels, probs):
        xmin, ymin, xmax, ymax = bbox_transform(bbox)

        h = ymax - ymin
        w = xmax - xmin

        class_string = class_label_to_string[class_label]

        cv2.rectangle(img, (int(xmin), int(ymax)), (int(xmax), int(ymin)),
                    class_to_color[class_string], 2)
        if probs is not None:
            cv2.rectangle(img, (int(xmin), int(ymin)), (int(xmax), int(ymin-12)),
                        class_to_color[class_string], -1)
            prob_string = "%.2f" % prob
            cv2.putText(img, prob_string, (int(xmin)+2, int(ymin)-2), 2, 0.4, (255,255,255), 0)

    img_with_bboxes = img
    return img_with_bboxes

# (taken from the official implementation)
def safe_exp(w, thresh):
    """
    safe exponential function for tensors
    """

    slope = np.exp(thresh)

    lin_bool = w > thresh
    lin_region = tf.to_float(lin_bool)

    lin_out = slope*(w - thresh + 1.)
    exp_out = tf.exp(tf.where(lin_bool, tf.zeros_like(w), w))

    out = lin_region*lin_out + (1.-lin_region)*exp_out

    return out

# (modified from the official implementation)
def bbox_transform(bbox):
    """
    convert a bbox of form [cx, cy, w, h] to [xmin, ymin, xmax, ymax]
    """

    cx, cy, w, h = bbox

    xmin = cx - w/2
    ymin = cy - h/2
    xmax = cx + w/2
    ymax = cy + h/2

    out_box = [xmin, ymin, xmax, ymax]

    return out_box

# (modified from the official implementation)
def bbox_transform_inv(bbox):
    """
    convert a bbox of form [xmin, ymin, xmax, ymax] to [cx, cy, w, h]
    """

    xmin, ymin, xmax, ymax = bbox

    w = xmax - xmin + 1.0
    h = ymax - ymin + 1.0
    cx  = xmin + w/2
    cy  = ymin + h/2

    out_box = [cx, cy, w, h]

    return out_box

# (taken from the official implementation)
def nms(boxes, probs, threshold):
    """
    Non-Maximum Supression

    args:
        boxes: array of [cx, cy, w, h]
        probs: array of probabilities
        threshold: two boxes are considered overlapping if their IOU is larger
                   than this threshold

    returns:
        keep: array of True or False
    """

    # TODO! how does this work?! Think I roughly understand now

    order = probs.argsort()[::-1] # (indices in descending order acc. to prob)
    keep = [True]*len(order)

    for i in range(len(order)-1):
        ovps = batch_IOU(boxes[order[i+1:]], boxes[order[i]])
        for j, ov in enumerate(ovps):
            if ov > threshold:
                keep[order[j+i+1]] = False

    return keep

# (modified from the official implementation)
def batch_IOU(boxes, box):
    """
    compute the Intersection-Over-Union of a batch of boxes with another box

    args:
        boxes: array of [cx, cy, width, height]
        box: a single box [cx, cy, width, height]

    returns:
        IOUs: array of a float number in range [0, 1]
    """

    intersect_xmax = np.minimum(boxes[:, 0] + 0.5*boxes[:, 2], box[0] + 0.5*box[2])
    intersect_xmin = np.maximum(boxes[:, 0] - 0.5*boxes[:, 2], box[0] - 0.5*box[2])
    intersect_ymax = np.minimum(boxes[:, 1] + 0.5*boxes[:, 3], box[1] + 0.5*box[3])
    intersect_ymin = np.maximum(boxes[:, 1] - 0.5*boxes[:, 3], box[1] - 0.5*box[3])

    intersect_w = np.maximum(0.0, intersect_xmax - intersect_xmin)
    intersect_h = np.maximum(0.0, intersect_ymax - intersect_ymin)
    intersection_area = intersect_w*intersect_h

    union_area = boxes[:, 2]*boxes[:, 3] + box[2]*box[3] - intersection_area

    IOUs = intersection_area/union_area

    return IOUs

# (modified from the official implementation)
def sparse_to_dense(indices, output_shape, values, default_value=0):
    """
    build a dense matrix from sparse representations

    args:
        indices: list of indices. if indices[i] = [k, l], then array[k,l] should be set to values[i]
        output_shape: shape of the dense matrix
        values: list of values. if indices[i] = [k, l], then array[k,l] should be set to values[i]
        default_value: values to set for indices not specified in indices

    returns:
        array: a dense numpy array with shape output_shape
    """

    array = np.ones(output_shape)*default_value
    for idx, value in zip(indices, values):
        array[tuple(idx)] = value

    return array

# (modified from utils/caffemodel2pkl.py in the official implementation)
def get_caffemodel_weights(prototxt_path, caffemodel_path):
    import caffe

    net = caffe.Net(prototxt_path, caffemodel_path, caffe.TEST)
    weights = {}
    no_of_layers = len(net.layers)
    for i in range(no_of_layers):
        layer_name = net._layer_names[i]
        layer = net.layers[i]
        layer_blobs = [o.data for o in layer.blobs]
        weights[layer_name] = layer_blobs

    return weights
