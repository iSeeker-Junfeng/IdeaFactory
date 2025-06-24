import React from 'react';
import './App.css'; // 引入全局样式

const DeviceDetail = ({ devices }) => {
  const { id, name, status } = devices;
  const currentTime = Date.now();

  return (
    <div className="device-detail">
      <h2>{name} 详情</h2>
      <p>设备 ID: <strong>{id}</strong></p>
      <p>状态: <span className={status ? 'status-online' : 'status-offline'}>{status ? '在线' : '离线'}</span></p>
      <p>最后更新: {new Date(currentTime).toLocaleString()}</p>
      <a href="/" className="back-button">
        返回
      </a>
    </div>
  );
};

export default DeviceDetail;