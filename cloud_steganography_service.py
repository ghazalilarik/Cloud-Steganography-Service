from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
from cryptography.fernet import Fernet
import base64
import random
import string
import io

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'
SECRET_KEY = Fernet.generate_key()
cipher_suite = Fernet(SECRET_KEY)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Hide secret data inside an image
def hide_data_in_image(image_path, secret_data):
    image = cv2.imread(image_path)
    data = cipher_suite.encrypt(secret_data.encode())

    # Convert data to binary
    binary_data = ''.join(format(byte, '08b') for byte in data)
    binary_index = 0

    for row in image:
        for pixel in row:
            for i in range(3):
                if binary_index < len(binary_data):
                    # Modify LSB of each color channel to hide data
                    pixel[i] = int(format(pixel[i], '08b')[:-1] + binary_data[binary_index], 2)
                    binary_index += 1
                else:
                    break

    # Save the modified image
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'encoded_' + ''.join(random.choices(string.ascii_lowercase, k=8)) + '.png')
    cv2.imwrite(output_path, image)
    return output_path

# Retrieve secret data from an image
def retrieve_data_from_image(image_path):
    image = cv2.imread(image_path)
    binary_data = ""

    for row in image:
        for pixel in row:
            for i in range(3):
                binary_data += format(pixel[i], '08b')[-1]

    # Convert binary data to bytes
    all_bytes = [binary_data[i:i+8] for i in range(0, len(binary_data), 8)]
    secret_data_bytes = bytearray()

    for byte in all_bytes:
        secret_data_bytes.append(int(byte, 2))

    try:
        # Decrypt data
        decrypted_data = cipher_suite.decrypt(bytes(secret_data_bytes))
        return decrypted_data.decode()
    except Exception as e:
        return "No valid hidden data found or decryption failed."

# Endpoint to hide data
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'data' not in request.form:
        return jsonify({"error": "Missing file or data"}), 400
    
    file = request.files['file']
    secret_data = request.form['data']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    encoded_image_path = hide_data_in_image(file_path, secret_data)
    
    return send_file(encoded_image_path, mimetype='image/png')

# Endpoint to retrieve data
@app.route('/retrieve', methods=['POST'])
def retrieve_data():
    if 'file' not in request.files:
        return jsonify({"error": "Missing file"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    hidden_data = retrieve_data_from_image(file_path)
    return jsonify({"hidden_data": hidden_data})

if __name__ == "__main__":
    app.run(debug=True)
