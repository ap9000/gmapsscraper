import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Button, List, Typography, Space, Progress } from 'antd';
import {
  UserOutlined,
  MailOutlined,
  DollarOutlined,
  SearchOutlined,
  FileTextOutlined,
  BarChartOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../store/appStore';
import { statusAPI, costsAPI } from '../../services/api';

const { Title, Text } = Typography;

const Dashboard = () => {
  const navigate = useNavigate();
  const { 
    searchHistory, 
    searchProgress, 
    systemStatus, 
    setSystemStatus,
    costSummary,
    setCostSummary
  } = useAppStore();

  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalBusinesses: 0,
    emailsFound: 0,
    todayCost: 0.0,
    enrichmentRate: 0
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load system status and database stats
      const [systemRes, dbRes, costsRes] = await Promise.all([
        statusAPI.getSystem(),
        statusAPI.getDatabase(),
        costsAPI.getSummary(1, false) // Today's costs
      ]);

      setSystemStatus(systemRes.data.status);
      
      if (dbRes.data.success) {
        setStats(prev => ({
          ...prev,
          totalBusinesses: dbRes.data.database.total_businesses,
          emailsFound: dbRes.data.database.with_email_addresses,
          enrichmentRate: dbRes.data.database.enrichment_rate
        }));
      }

      if (costsRes.data.success) {
        setCostSummary(costsRes.data.summary);
        const todayCost = costsRes.data.summary?.summary?.total_cost || 0;
        setStats(prev => ({ ...prev, todayCost }));
      }

    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    {
      title: 'New Search',
      description: 'Start a single business search',
      icon: <SearchOutlined />,
      action: () => navigate('/search'),
      color: '#1890ff'
    },
    {
      title: 'Batch Upload',
      description: 'Upload CSV for bulk processing',
      icon: <FileTextOutlined />,
      action: () => navigate('/batch'),
      color: '#52c41a'
    },
    {
      title: 'View Analytics',
      description: 'Check costs and performance',
      icon: <BarChartOutlined />,
      action: () => navigate('/analytics'),
      color: '#722ed1'
    }
  ];

  const recentSearches = searchHistory.slice(0, 5);

  return (
    <div style={{ padding: '0' }}>
      <Title level={2}>Dashboard</Title>
      
      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="Total Businesses"
              value={stats.totalBusinesses}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="Emails Found"
              value={stats.emailsFound}
              prefix={<MailOutlined />}
              suffix={`/ ${stats.totalBusinesses}`}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="Today's Cost"
              value={stats.todayCost}
              precision={4}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="Enrichment Rate"
              value={stats.enrichmentRate}
              precision={1}
              suffix="%"
              valueStyle={{ 
                color: stats.enrichmentRate > 50 ? '#3f8600' : '#cf1322' 
              }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Current Search Progress */}
        {searchProgress.jobId && searchProgress.status !== 'completed' && (
          <Col xs={24} lg={12}>
            <Card title="Current Search Progress" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>Job: {searchProgress.jobId}</Text>
                <Progress 
                  percent={searchProgress.progress} 
                  status={searchProgress.status === 'failed' ? 'exception' : 'active'}
                />
                <Text type="secondary">{searchProgress.details}</Text>
              </Space>
            </Card>
          </Col>
        )}

        {/* Quick Actions */}
        <Col xs={24} lg={searchProgress.jobId ? 12 : 24}>
          <Card title="Quick Actions" size="small">
            <Row gutter={[16, 16]}>
              {quickActions.map((action, index) => (
                <Col xs={24} md={8} key={index}>
                  <Card 
                    hoverable 
                    size="small"
                    onClick={action.action}
                    style={{ 
                      textAlign: 'center',
                      borderColor: action.color,
                      cursor: 'pointer'
                    }}
                  >
                    <Space direction="vertical">
                      <div style={{ fontSize: '24px', color: action.color }}>
                        {action.icon}
                      </div>
                      <Title level={5} style={{ margin: 0 }}>
                        {action.title}
                      </Title>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {action.description}
                      </Text>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>

        {/* Recent Searches */}
        <Col xs={24} lg={12}>
          <Card 
            title="Recent Searches" 
            size="small"
            extra={
              <Button 
                type="link" 
                size="small" 
                onClick={() => navigate('/search')}
              >
                View All
              </Button>
            }
          >
            {recentSearches.length > 0 ? (
              <List
                size="small"
                dataSource={recentSearches}
                renderItem={(search, index) => (
                  <List.Item key={index}>
                    <List.Item.Meta
                      title={
                        <Text strong>
                          {search.query}
                        </Text>
                      }
                      description={
                        <Space>
                          <Text type="secondary">
                            {search.location || 'Global'}
                          </Text>
                          <Text type="secondary">•</Text>
                          <Text type="secondary">
                            {search.results || 0} results
                          </Text>
                        </Space>
                      }
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {search.timestamp ? new Date(search.timestamp).toLocaleDateString() : 'Unknown'}
                    </Text>
                  </List.Item>
                )}
              />
            ) : (
              <Text type="secondary">No searches yet</Text>
            )}
          </Card>
        </Col>

        {/* System Status */}
        <Col xs={24} lg={12}>
          <Card title="System Status" size="small">
            {systemStatus ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>
                  <Text strong>Proxies:</Text> {systemStatus.proxy_count} loaded
                </Text>
                <Text>
                  <Text strong>Platform:</Text> {systemStatus.system?.platform || 'Unknown'}
                </Text>
                <Text>
                  <Text strong>Version:</Text> {systemStatus.version}
                </Text>
                {systemStatus.system?.cpu_percent && (
                  <Text>
                    <Text strong>CPU:</Text> {systemStatus.system.cpu_percent}%
                  </Text>
                )}
                {systemStatus.system?.memory_percent && (
                  <Text>
                    <Text strong>Memory:</Text> {systemStatus.system.memory_percent}%
                  </Text>
                )}
              </Space>
            ) : (
              <Text type="secondary">Loading system status...</Text>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;