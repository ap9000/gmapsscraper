import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, DatePicker, Space, Typography } from 'antd';
import { DollarOutlined, ApiOutlined, TrophyOutlined } from '@ant-design/icons';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { useAppStore } from '../../store/appStore';
import { costsAPI } from '../../services/api';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const Analytics = () => {
  const { costSummary, setCostSummary } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState(30);

  useEffect(() => {
    loadCostData();
  }, [period]);

  const loadCostData = async () => {
    try {
      setLoading(true);
      const response = await costsAPI.getSummary(period);
      if (response.data.success) {
        setCostSummary(response.data.summary);
      }
    } catch (error) {
      console.error('Error loading cost data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Mock data for charts - replace with real data
  const dailyCosts = [
    { date: '2024-01-01', cost: 12.50, calls: 150 },
    { date: '2024-01-02', cost: 18.75, calls: 225 },
    { date: '2024-01-03', cost: 9.25, calls: 111 },
    { date: '2024-01-04', cost: 21.30, calls: 256 },
    { date: '2024-01-05', cost: 15.80, calls: 190 },
  ];

  const apiUsage = [
    { api: 'ScrapingDog', calls: 1250, cost: 65.75 },
    { api: 'Hunter.io', calls: 45, cost: 2.20 },
    { api: 'Geocoding', calls: 320, cost: 0.00 },
  ];

  const totalCost = costSummary?.summary?.total_cost || 0;
  const totalCalls = costSummary?.summary?.total_calls || 0;
  const avgCostPerCall = totalCalls > 0 ? totalCost / totalCalls : 0;

  return (
    <div style={{ padding: '0' }}>
      <Title level={2}>Analytics & Costs</Title>
      
      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title={`Total Cost (${period} days)`}
              value={totalCost}
              precision={4}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="Total API Calls"
              value={totalCalls}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="Avg Cost per Call"
              value={avgCostPerCall}
              precision={6}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Controls */}
      <Row style={{ marginBottom: '24px' }}>
        <Col>
          <Space>
            <Button 
              type={period === 1 ? 'primary' : 'default'}
              onClick={() => setPeriod(1)}
            >
              Today
            </Button>
            <Button 
              type={period === 7 ? 'primary' : 'default'}
              onClick={() => setPeriod(7)}
            >
              Last 7 Days
            </Button>
            <Button 
              type={period === 30 ? 'primary' : 'default'}
              onClick={() => setPeriod(30)}
            >
              Last 30 Days
            </Button>
            <Button onClick={loadCostData} loading={loading}>
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[24, 24]}>
        {/* Daily Costs Chart */}
        <Col xs={24} lg={12}>
          <Card title="Daily Costs" size="small">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyCosts}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip formatter={(value, name) => [
                  name === 'cost' ? `$${value}` : value,
                  name === 'cost' ? 'Cost' : 'Calls'
                ]} />
                <Line 
                  type="monotone" 
                  dataKey="cost" 
                  stroke="#1890ff" 
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* API Usage Chart */}
        <Col xs={24} lg={12}>
          <Card title="API Usage Breakdown" size="small">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={apiUsage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="api" />
                <YAxis />
                <Tooltip formatter={(value, name) => [
                  name === 'cost' ? `$${value}` : value,
                  name === 'cost' ? 'Cost' : 'Calls'
                ]} />
                <Bar dataKey="calls" fill="#52c41a" />
                <Bar dataKey="cost" fill="#1890ff" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* Cost Efficiency */}
        <Col xs={24} lg={12}>
          <Card title="Cost Efficiency" size="small">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Best Day"
                  value="Jan 3"
                  valueStyle={{ color: '#52c41a' }}
                  suffix="$9.25"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Worst Day"
                  value="Jan 4"
                  valueStyle={{ color: '#ff4d4f' }}
                  suffix="$21.30"
                />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* Budget Status */}
        <Col xs={24} lg={12}>
          <Card title="Budget Status" size="small">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Monthly Limit"
                  value="$100.00"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Remaining"
                  value={100 - totalCost}
                  precision={2}
                  prefix="$"
                  valueStyle={{ 
                    color: (100 - totalCost) > 20 ? '#52c41a' : '#ff4d4f' 
                  }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Analytics;