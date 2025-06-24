import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import './App.css'; // 引入全局样式
import DeviceStatus from './DeviceStatus';
import DeviceDetail from './DeviceDetail';

const App = () => {
  const [devices, setDevices] = React.useState([
    { id: 1, name: '设备 1', status: true },
    { id: 2, name: '设备 2', status: false },
    { id: 3, name: '设备 3', status: true },
    { id: 4, name: '设备 4', status: false },
    { id: 5, name: '设备 5', status: true }
  ]);

  const [currentTime, setCurrentTime] = React.useState(Date.now());

  React.useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const refreshStatus = () => {
    const updatedDevices = devices.map(device => ({
      ...device,
      status: Math.random() > 0.5
    }));
    setDevices(updatedDevices);
  };

  return (
    <Router>
      <div className="container">
        <h1 className="title">物联网设备状态</h1>
        <button
          onClick={refreshStatus}
          className="refresh-button"
        >
          刷新状态
        </button>
        <Routes>
          <Route path="/" element={
            <div className="device-list">
              {devices.map(device => (
                <Link to={`/device/${device.id}`} key={device.id}>
                  <DeviceStatus device={device} currentTime={currentTime} />
                </Link>
              ))}
            </div>
          } />
          <Route path="/device/:id" element={<DeviceDetail devices={devices.find(d => d.id === parseInt(window.location.pathname.split('/').pop(), 10))} />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;