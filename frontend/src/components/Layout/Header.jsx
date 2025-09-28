import React from 'react';
import { Layout, Button, Space, Badge, Typography, Switch } from 'antd';
import { 
  BulbOutlined, 
  BulbFilled, 
  WifiOutlined, 
  DisconnectOutlined 
} from '@ant-design/icons';
import { useAppStore } from '../../store/appStore';

const { Header: AntHeader } = Layout;
const { Text } = Typography;

const Header = () => {
  const { darkMode, toggleDarkMode, connected } = useAppStore();

  return (
    <AntHeader 
      style={{ 
        padding: '0 16px', 
        background: darkMode ? '#141414' : '#fff',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}
    >
      <div>
        <Text strong style={{ fontSize: '16px' }}>
          Google Maps Lead Generator
        </Text>
      </div>
      
      <Space>
        {/* Connection Status */}
        <Badge 
          status={connected ? 'success' : 'error'} 
          text={
            <Text type={connected ? 'success' : 'danger'}>
              {connected ? 'Connected' : 'Disconnected'}
            </Text>
          }
        />
        
        {connected ? <WifiOutlined /> : <DisconnectOutlined />}
        
        {/* Dark Mode Toggle */}
        <Switch
          checked={darkMode}
          onChange={toggleDarkMode}
          checkedChildren={<BulbFilled />}
          unCheckedChildren={<BulbOutlined />}
        />
      </Space>
    </AntHeader>
  );
};

export default Header;