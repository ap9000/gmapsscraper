import React from 'react';
import { Layout, Menu, Typography } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  SearchOutlined,
  FileTextOutlined,
  BarChartOutlined,
  SettingOutlined,
  BugOutlined,
} from '@ant-design/icons';

const { Sider } = Layout;
const { Title } = Typography;

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/search',
      icon: <SearchOutlined />,
      label: 'Search',
    },
    {
      key: '/batch',
      icon: <FileTextOutlined />,
      label: 'Batch Processing',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Analytics',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
    {
      key: '/debug',
      icon: <BugOutlined />,
      label: 'Debug',
    },
  ];

  const handleMenuClick = (e) => {
    navigate(e.key);
  };

  return (
    <Sider width={240} className="site-layout-background">
      <div style={{ padding: '16px', textAlign: 'center' }}>
        <Title level={4} style={{ color: '#1890ff', margin: 0 }}>
          GMaps Lead Gen
        </Title>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
        style={{ borderRight: 0 }}
      />
    </Sider>
  );
};

export default Sidebar;