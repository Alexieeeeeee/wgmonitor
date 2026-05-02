import subprocess
import re
from flask import Flask, render_template_string, request, jsonify
import os
import json

app = Flask(__name__)

# 存储自定义peer名称的字典
CUSTOM_NAMES_FILE = 'custom_names.json'

def load_custom_names():
    """从文件加载自定义名称"""
    if os.path.exists(CUSTOM_NAMES_FILE):
        try:
            with open(CUSTOM_NAMES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading custom names: {e}")
            return {}
    return {}

def save_custom_names(names):
    """保存自定义名称到文件"""
    try:
        with open(CUSTOM_NAMES_FILE, 'w') as f:
            json.dump(names, f)
    except Exception as e:
        print(f"Error saving custom names: {e}")

# 初始化时加载自定义名称
custom_names = load_custom_names()

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
        .view-toggle {
            background-color: #0080FF; /* 天蓝色 */
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        }
        .view-toggle:hover {
            background-color: #0066CC; /* 深一点的天蓝色 */
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
        .sort-btn {
            background-color: #00AA44; /* 绿色 */
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 5px;
        }
        .sort-btn:hover {
            background-color: #008833; /* 深一点的绿色 */
        }
        .sort-btn.active {
            background-color: #FF6600; /* 橙色表示激活状态 */
            font-weight: bold;
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

        /* 表格样式 */
        .list-view {
            display: block; /* 默认显示列表视图 */
        }
        .card-view {
            display: none; /* 默认隐藏卡片视图 */
        }
        .peer-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .peer-table th, .peer-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .peer-table th {
            background-color: #0080FF; /* 天蓝色 */
            color: white;
        }
        .peer-table tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .peer-table tr:hover {
            background-color: #E6F2FF; /* 浅天蓝色 */
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
            .peer-table, .peer-table thead, .peer-table tbody, .peer-table th, .peer-table td, .peer-table tr {
                display: block;
            }
            .peer-table thead tr {
                position: absolute;
                top: -9999px;
                left: -9999px;
            }
            .peer-table tr {
                border: 1px solid #ccc;
                margin-bottom: 10px;
                padding: 10px;
                border-radius: 5px;
            }
            .peer-table td {
                border: none;
                position: relative;
                padding-left: 50%;
            }
            .peer-table td:before {
                content: attr(data-label);
                position: absolute;
                left: 6px;
                width: 45%;
                padding-right: 10px;
                white-space: nowrap;
                font-weight: bold;
                color: #0080FF; /* 天蓝色 */
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WireGuard Monitor</h1>

        <div class="controls">
            <button class="view-toggle" onclick="switchView('card')">Card View</button>
            <button class="view-toggle" onclick="switchView('list')">List View</button>
            <button class="refresh-btn" onclick="refreshData()">Refresh Data</button>
            <span style="margin-left: 20px;">Sort by:</span>
            <button class="sort-btn" onclick="sortData('default')" id="sort-default">Default</button>
            <button class="sort-btn" onclick="sortData('ip')" id="sort-ip">IP Address</button>
            <button class="sort-btn" onclick="sortData('name')" id="sort-name">Name</button>
            <button class="sort-btn" onclick="sortData('traffic')" id="sort-traffic">Total Traffic</button>
        </div>

        <!-- 卡片视图 -->
        <div id="card-view" class="card-view">
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

        <!-- 列表视图 -->
        <div id="list-view" class="list-view">
            {% if peers %}
                <table class="peer-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>IP Address</th>
                            <th>Transfer</th>
                            <th>Latest Handshake</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for peer in peers %}
                        <tr>
                            <td>{{ peer.name }}</td>
                            <td>{{ peer.ip }}</td>
                            <td>{{ peer.transfer }}</td>
                            <td>{{ peer.handshake }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="status-card">
                    <div class="no-peers">No WireGuard peers found or wg command failed</div>
                </div>
            {% endif %}
        </div>
    </div>

    <script>
        function switchView(view) {
            const cardView = document.getElementById('card-view');
            const listView = document.getElementById('list-view');

            if (view === 'list') {
                cardView.style.display = 'none';
                listView.style.display = 'block';
            } else {
                cardView.style.display = 'block';
                listView.style.display = 'none';
            }
        }

        function refreshData() {
            location.reload();
        }

        function parseTraffic(trafficStr) {
            // 解析流量字符串，转换为MB用于排序
            if (!trafficStr || trafficStr === '') return 0;
            
            // 处理两种格式："2.85 MiB received, 13.08 MiB sent" 或 "2.73 MiB received + 12.56 MiB sent"
            let parts = [];
            if (trafficStr.includes(' + ')) {
                parts = trafficStr.split(' + ');
            } else if (trafficStr.includes(', ')) {
                // 提取那些以逗号分隔的数值
                const matches = trafficStr.match(/([0-9.]+)\s*(MiB|KiB|GiB|TiB|B|MB|KB|GB|TB)/gi);
                if (matches) {
                    parts = matches;
                }
            }
            
            let totalBytes = 0;
            
            for (const part of parts) {
                const match = part.trim().match(/([0-9.]+)\s*([KMGT]?i?B)/i);
                if (match) {
                    let value = parseFloat(match[1]);
                    const unit = match[2].toUpperCase();
                    
                    switch (unit) {
                        case 'B':
                            totalBytes += value;
                            break;
                        case 'KB':
                        case 'KIB':
                            totalBytes += value * 1024;
                            break;
                        case 'MB':
                        case 'MIB':
                            totalBytes += value * 1024 * 1024;
                            break;
                        case 'GB':
                        case 'GIB':
                            totalBytes += value * 1024 * 1024 * 1024;
                            break;
                        case 'TB':
                        case 'TIB':
                            totalBytes += value * 1024 * 1024 * 1024 * 1024;
                            break;
                    }
                }
            }
            
            // 转换为MB返回
            return totalBytes / (1024 * 1024);
        }

        function sortData(sortType) {
            // 保存排序选择到 localStorage
            localStorage.setItem('wgmonitor-sort', sortType);
            
            // 更新按钮状态
            document.querySelectorAll('.sort-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            document.getElementById(`sort-${sortType}`).classList.add('active');

            // 获取当前视图中的所有行数据
            const isListView = document.getElementById('list-view').style.display !== 'none';
            
            if (isListView) {
                sortListView(sortType);
            } else {
                sortCardView(sortType);
            }
        }

        function sortListView(sortType) {
            const table = document.querySelector('.peer-table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            rows.sort((a, b) => {
                const aCells = a.querySelectorAll('td');
                const bCells = b.querySelectorAll('td');

                switch (sortType) {
                    case 'ip':
                        const aIP = aCells[1].textContent;
                        const bIP = bCells[1].textContent;
                        return aIP.localeCompare(bIP, undefined, {numeric: true});
                        
                    case 'name':
                        const aName = aCells[0].textContent.toLowerCase();
                        const bName = bCells[0].textContent.toLowerCase();
                        return aName.localeCompare(bName);
                        
                    case 'traffic':
                        const aTraffic = parseTraffic(aCells[2].textContent);
                        const bTraffic = parseTraffic(bCells[2].textContent);
                        return bTraffic - aTraffic; // 降序排列，流量大的在前
                        
                    default:
                        return 0; // 默认顺序
                }
            });

            // 重新添加排序后的行
            rows.forEach(row => tbody.appendChild(row));
        }

        function sortCardView(sortType) {
            const container = document.getElementById('card-view');
            const cards = Array.from(container.querySelectorAll('.status-card'));

            cards.sort((a, b) => {
                switch (sortType) {
                    case 'ip':
                        const aIP = a.querySelector('.peer-info .info-value:nth-child(2)').textContent;
                        const bIP = b.querySelector('.peer-info .info-value:nth-child(2)').textContent;
                        return aIP.localeCompare(bIP, undefined, {numeric: true});
                        
                    case 'name':
                        const aName = a.querySelector('.peer-name').textContent.toLowerCase();
                        const bName = b.querySelector('.peer-name').textContent.toLowerCase();
                        return aName.localeCompare(bName);
                        
                    case 'traffic':
                        const aTrafficText = a.querySelector('.peer-info .info-value:nth-child(6)').textContent;
                        const bTrafficText = b.querySelector('.peer-info .info-value:nth-child(6)').textContent;
                        const aTraffic = parseTraffic(aTrafficText);
                        const bTraffic = parseTraffic(bTrafficText);
                        return bTraffic - aTraffic; // 降序排列，流量大的在前
                        
                    default:
                        return 0; // 默认顺序
                }
            });

            // 重新添加排序后的卡片
            cards.forEach(card => container.appendChild(card));
        }

        // 页面加载时恢复保存的排序选择并应用
        document.addEventListener('DOMContentLoaded', function() {
            const savedSort = localStorage.getItem('wgmonitor-sort') || 'default';
            sortData(savedSort);
        });

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
                    // 同时更新列表视图中的名称
                    const tableRows = document.querySelectorAll('.peer-table tbody tr');
                    if(tableRows[index-1]) {
                        const nameCell = tableRows[index-1].querySelector('td:first-child');
                        nameCell.textContent = newName;
                    }
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

    # 保存到文件以实现持久化存储
    save_custom_names(custom_names)

    return jsonify({'success': True})

@app.route('/status')
def status():
    """提供JSON格式的状态数据用于AJAX请求"""
    peers = get_wireguard_status()
    return jsonify(peers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=True)
