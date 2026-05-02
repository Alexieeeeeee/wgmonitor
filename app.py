import subprocess
import re
from flask import Flask, render_template_string, request, jsonify
import os

app = Flask(__name__)

# 存储自定义peer名称的字典
custom_names = {}

def get_wireguard_status():
    """获取并解析wg命令输出"""
    try:
        # 执行wg命令获取输出
        result = subprocess.run(['wg'], shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return []

        output = result.stdout
        peers = []
        peer_data = {}

        # 解析输出
        lines = output.strip().split('\n')
        current_peer = None

        for line in lines:
            line = line.strip()

            # 检查是否是新的peer部分
            if line.startswith('peer:'):
                if current_peer is not None:
                    # 保存前一个peer的数据
                    peers.append(current_peer)

                # 开始新的peer
                current_peer = {
                    'public_key': line.split(' ', 1)[1].strip(),
                    'name': '',  # 可由用户自定义
                    'ip': '',
                    'endpoint': '',
                    'handshake': '',
                    'transfer': ''
                }

            elif current_peer is not None:
                # 解析peer的具体信息
                if line.startswith('allowed ips:'):
                    ip_match = re.search(r'allowed ips:\s*(.+)', line)
                    if ip_match:
                        current_peer['ip'] = ip_match.group(1).split('/')[0]  # 提取IP地址部分

                elif line.startswith('endpoint:'):
                    endpoint_match = re.search(r'endpoint:\s*(.+)', line)
                    if endpoint_match:
                        current_peer['endpoint'] = endpoint_match.group(1)

                elif line.startswith('latest handshake:'):
                    handshake_match = re.search(r'latest handshake:\s*(.+)', line)
                    if handshake_match:
                        current_peer['handshake'] = handshake_match.group(1)

                elif line.startswith('transfer:'):
                    transfer_match = re.search(r'transfer:\s*(.+)', line)
                    if transfer_match:
                        current_peer['transfer'] = transfer_match.group(1)

        # 添加最后一个peer
        if current_peer is not None:
            peers.append(current_peer)

        # 设置名称（优先使用自定义名称，否则使用默认格式）
        for i, peer in enumerate(peers):
            # 尝试从自定义名称中查找
            name_found = False
            for pub_key, custom_name in custom_names.items():
                if pub_key == peer['public_key']:
                    peer['name'] = custom_name
                    name_found = True
                    break

            # 如果没有找到自定义名称，则使用默认格式
            if not name_found:
                peer['name'] = f"Peer {i+1} ({peer['ip']})"

        return peers

    except Exception as e:
        print(f"Error getting WireGuard status: {e}")
        return []

@app.route('/')
def index():
    peers = get_wireguard_status()

    html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WireGuard Monitor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: white;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        h1 {
            color: #0080FF; /* 天蓝色 */
            text-align: center;
            margin-bottom: 30px;
        }
        .controls {
            text-align: center;
            margin-bottom: 20px;
        }
        .refresh-btn {
            background-color: #0080FF; /* 天蓝色 */
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        }
        .refresh-btn:hover {
            background-color: #0066CC; /* 深一点的天蓝色 */
        }
        .status-card {
            background-color: #E6F2FF; /* 浅天蓝色 */
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .peer-header {
            background-color: #0080FF; /* 天蓝色 */
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .rename-section {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .rename-input {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
            width: 150px;
        }
        .rename-btn {
            background-color: #0066CC;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
        }
        .peer-info {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 10px;
            margin-bottom: 10px;
        }
        .info-label {
            font-weight: bold;
            color: #0080FF; /* 天蓝色 */
        }
        .info-value {
            color: #333;
        }
        .no-peers {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        @media (max-width: 768px) {
            .peer-info {
                grid-template-columns: 1fr;
            }
            .rename-section {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WireGuard Monitor</h1>

        <div class="controls">
            <button class="refresh-btn" onclick="refreshData()">Refresh Data</button>
        </div>

        {% if peers %}
            {% for peer in peers %}
            <div class="status-card">
                <div class="peer-header">
                    <span class="peer-name" id="name-{{ loop.index }}">{{ peer.name }}</span>
                    <div class="rename-section">
                        <input type="text" class="rename-input" id="rename-input-{{ loop.index }}" value="{{ peer.name }}" placeholder="Custom name">
                        <button class="rename-btn" onclick="renamePeer('{{ peer.public_key }}', {{ loop.index }})">Rename</button>
                    </div>
                </div>
                <div class="peer-info">
                    <div class="info-label">IP Address:</div>
                    <div class="info-value">{{ peer.ip }}</div>

                    <div class="info-label">Endpoint:</div>
                    <div class="info-value">{{ peer.endpoint }}</div>

                    <div class="info-label">Latest Handshake:</div>
                    <div class="info-value">{{ peer.handshake }}</div>

                    <div class="info-label">Transfer:</div>
                    <div class="info-value">{{ peer.transfer }}</div>

                    <div class="info-label">Public Key:</div>
                    <div class="info-value" style="word-break: break-all; font-size: 0.9em;">{{ peer.public_key }}</div>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="status-card">
                <div class="no-peers">No WireGuard peers found or wg command failed</div>
            </div>
        {% endif %}
    </div>

    <script>
        function refreshData() {
            location.reload();
        }

        function renamePeer(publicKey, index) {
            const input = document.getElementById(`rename-input-${index}`);
            const newName = input.value.trim();

            if (!newName) {
                alert('Please enter a valid name');
                return;
            }

            fetch('/rename_peer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    public_key: publicKey,
                    new_name: newName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 更新显示名称
                    const nameSpan = document.getElementById(`name-${index}`);
                    nameSpan.textContent = newName;
                    alert('Peer renamed successfully!');
                } else {
                    alert('Failed to rename peer: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while renaming the peer');
            });
        }
    </script>
</body>
</html>
'''
    return render_template_string(html_template, peers=peers)

@app.route('/rename_peer', methods=['POST'])
def rename_peer():
    """处理重命名peer的请求"""
    global custom_names

    data = request.get_json()
    public_key = data.get('public_key')
    new_name = data.get('new_name')

    if not public_key or not new_name:
        return jsonify({'success': False, 'error': 'Missing public_key or new_name'})

    # 更新自定义名称字典
    custom_names[public_key] = new_name

    return jsonify({'success': True})

@app.route('/status')
def status():
    """提供JSON格式的状态数据用于AJAX请求"""
    peers = get_wireguard_status()
    return jsonify(peers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)