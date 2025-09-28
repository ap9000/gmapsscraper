import React from 'react';
import { Row, Col, Card, Statistic, Tag, Space, Button, Typography } from 'antd';
import { ApiOutlined, DisconnectOutlined, ReloadOutlined } from '@ant-design/icons';
import { useAppStore } from '../../store/appStore';
import { useLogStore } from '../../store/logStore';
import { backendHealthService } from '../../services/backendHealth';
import LogViewer from './LogViewer';

const { Title } = Typography;

const Debug = () => {
  const { connected, backendLoading } = useAppStore();
  const { logs } = useLogStore();
  
  const handleManualHealthCheck = async () => {
    const isHealthy = await backendHealthService.checkHealth();
    console.log('Manual health check result:', isHealthy);
  };

  const getConnectionStatus = () => {
    if (backendLoading) return { status: 'Loading', color: 'processing', icon: <ReloadOutlined spin /> };
    if (connected) return { status: 'Connected', color: 'success', icon: <ApiOutlined /> };
    return { status: 'Disconnected', color: 'error', icon: <DisconnectOutlined /> };
  };

  const connectionInfo = getConnectionStatus();
  
  // Count logs by level
  const logCounts = logs.reduce((acc, log) => {
    acc[log.level] = (acc[log.level] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>Debug & Diagnostics</Title>
      
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Connection Status"
              value={connectionInfo.status}
              prefix={connectionInfo.icon}
              valueStyle={{ color: connectionInfo.color === 'success' ? '#3f8600' : connectionInfo.color === 'error' ? '#cf1322' : '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="Backend Loading"
              value={backendLoading ? 'Yes' : 'No'}
              valueStyle={{ color: backendLoading ? '#faad14' : '#3f8600' }}
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Logs"
              value={logs.length}
              suffix="entries"
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Button 
                type="primary" 
                icon={<ReloadOutlined />}
                onClick={handleManualHealthCheck}
                block
              >
                Test Connection
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col span={24}>
          <Card title="Log Summary">
            <Space wrap>
              {Object.entries(logCounts).map(([level, count]) => {
                const colors = {
                  error: 'red',
                  warn: 'orange', 
                  info: 'blue',
                  debug: 'purple',
                  success: 'green'
                };
                return (
                  <Tag key={level} color={colors[level] || 'default'}>
                    {level.toUpperCase()}: {count}
                  </Tag>
                );
              })}
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <LogViewer />
        </Col>
      </Row>
    </div>
  );
};

export default Debug;