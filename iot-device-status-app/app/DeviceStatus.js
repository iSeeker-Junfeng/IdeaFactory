import React, { useEffect, useState } from 'react';
import { get_devices } from './sim_api';

const DeviceStatus = () => {
  const [devices, setDevices] = useState({});

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const data = await get_devices();
        setDevices(data);
      } catch (error) {
        console.error('Error fetching device status:', error);
      }
    };

    fetchDevices();
  }, []);

  return (
    <div>
      <h2>设备状态</h2>
      <ul>
        {Object.entries(devices).map(([id, info]) => (
          <li key={id}>
            <strong>{id}</strong>: {info.status} (最后在线时间: {info.last_seen})
          </li>
        ))}
      </ul>
    </div>
  );
};

export default DeviceStatus;
