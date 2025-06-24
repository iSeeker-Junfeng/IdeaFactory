from flask import Flask, jsonify

app = Flask(__name__)

# 模拟设备状态数据
device_status = {
    "device1": {"status": "online", "last_seen": "2023-10-01T12:00:00Z"},
    "device2": {"status": "offline", "last_seen": "2023-09-30T15:30:00Z"}
}

@app.route('/api/devices', methods=['GET'])
def get_devices():
    return jsonify(device_status)

@app.route('/api/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    device = device_status.get(device_id)
    if device:
        print(jsonify(device))
        return jsonify(device)
    else:
        return jsonify({"error": "Device not found"}), 404

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
