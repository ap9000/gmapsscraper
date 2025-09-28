import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Switch, InputNumber, Button, Typography, Space, Row, Col, Alert, Divider } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useAppStore } from '../../store/appStore';
import { statusAPI } from '../../services/api';

const { Title, Text } = Typography;

const Settings = () => {
  const [loading, setLoading] = useState(true);
  const { config, setConfig } = useAppStore();
  const [systemConfig, setSystemConfig] = useState(null);
  const [rateLimits, setRateLimits] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [configRes, limitsRes] = await Promise.all([
        statusAPI.getConfig(),
        statusAPI.getLimits()
      ]);

      if (configRes.data.success) {
        setSystemConfig(configRes.data.config);
        setConfig(configRes.data.config);
      }

      if (limitsRes.data.success) {
        setRateLimits(limitsRes.data);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatusIcon = ({ configured }) => (
    configured ? 
      <CheckCircleOutlined style={{ color: '#52c41a' }} /> : 
      <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
  );

  return (
    <div style={{ padding: '0' }}>
      <Title level={2}>Settings</Title>
      
      <Row gutter={[24, 24]}>
        {/* API Configuration Status */}
        <Col xs={24} lg={12}>
          <Card title="API Configuration Status" loading={loading} size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong>ScrapingDog API</Text>
                <Space>
                  <StatusIcon configured={systemConfig?.scrapingdog?.configured} />
                  <Text type={systemConfig?.scrapingdog?.configured ? 'success' : 'danger'}>
                    {systemConfig?.scrapingdog?.configured ? 'Configured' : 'Not Configured'}
                  </Text>
                </Space>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong>Hunter.io API</Text>
                <Space>
                  <StatusIcon configured={systemConfig?.hunter?.configured} />
                  <Text type={systemConfig?.hunter?.configured ? 'success' : 'danger'}>
                    {systemConfig?.hunter?.configured ? 'Configured' : 'Not Configured'}
                  </Text>
                  <Text type="secondary">
                    ({systemConfig?.hunter?.enabled ? 'Enabled' : 'Disabled'})
                  </Text>
                </Space>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong>HubSpot Integration</Text>
                <Space>
                  <StatusIcon configured={systemConfig?.hubspot?.configured} />
                  <Text type={systemConfig?.hubspot?.configured ? 'success' : 'danger'}>
                    {systemConfig?.hubspot?.configured ? 'Configured' : 'Not Configured'}
                  </Text>
                  <Text type="secondary">
                    ({systemConfig?.hubspot?.enabled ? 'Enabled' : 'Disabled'})
                  </Text>
                </Space>
              </div>
            </Space>
          </Card>
        </Col>

        {/* Rate Limits */}
        <Col xs={24} lg={12}>
          <Card title="Rate Limits" loading={loading} size="small">
            {rateLimits && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text strong>Daily Limit:</Text>
                  <Text>{rateLimits.limits?.daily_limit?.toLocaleString()}</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text strong>Weekly Limit:</Text>
                  <Text>{rateLimits.limits?.weekly_limit?.toLocaleString()}</Text>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text strong>Monthly Limit:</Text>
                  <Text>{rateLimits.limits?.monthly_limit?.toLocaleString()}</Text>
                </div>
                
                <Divider />
                
                {rateLimits.current_usage && (
                  <>
                    <Text strong>Current Usage:</Text>
                    <div style={{ paddingLeft: '16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>Today:</Text>
                        <Text>{rateLimits.current_usage.daily_used || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>This Week:</Text>
                        <Text>{rateLimits.current_usage.weekly_used || 0}</Text>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text>This Month:</Text>
                        <Text>{rateLimits.current_usage.monthly_used || 0}</Text>
                      </div>
                    </div>
                  </>
                )}
              </Space>
            )}
          </Card>
        </Col>

        {/* Enrichment Settings Display */}
        <Col xs={24}>
          <Card title="Enrichment Configuration" loading={loading} size="small">
            {systemConfig?.enrichment && (
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} md={6}>
                  <Space direction="vertical">
                    <Text strong>Scrapling</Text>
                    <Switch 
                      checked={systemConfig.enrichment.use_scrapling} 
                      disabled 
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Advanced web scraping
                    </Text>
                  </Space>
                </Col>
                
                <Col xs={24} sm={12} md={6}>
                  <Space direction="vertical">
                    <Text strong>Website Scraping</Text>
                    <Switch 
                      checked={systemConfig.enrichment.enable_website_scraping} 
                      disabled 
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Basic website crawling
                    </Text>
                  </Space>
                </Col>
                
                <Col xs={24} sm={12} md={6}>
                  <Space direction="vertical">
                    <Text strong>Hunter.io</Text>
                    <Switch 
                      checked={systemConfig.enrichment.enable_hunter} 
                      disabled 
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Paid email lookup
                    </Text>
                  </Space>
                </Col>
                
                <Col xs={24} sm={12} md={6}>
                  <Space direction="vertical">
                    <Text strong>Pattern Generation</Text>
                    <Switch 
                      checked={systemConfig.enrichment.enable_pattern_generation} 
                      disabled 
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Email pattern guessing
                    </Text>
                  </Space>
                </Col>
              </Row>
            )}
          </Card>
        </Col>

        {/* Configuration Instructions */}
        <Col xs={24}>
          <Card title="Configuration Instructions" size="small">
            <Alert
              message="Configuration is managed through config files"
              description={
                <div>
                  <p>To modify settings, edit the configuration file at: <code>config/config.yaml</code></p>
                  <p><strong>Required for basic functionality:</strong></p>
                  <ul>
                    <li>ScrapingDog API key for Google Maps access</li>
                  </ul>
                  <p><strong>Optional for enhanced features:</strong></p>
                  <ul>
                    <li>Hunter.io API key for premium email enrichment</li>
                    <li>HubSpot access token for CRM integration</li>
                  </ul>
                  <p>After making changes, restart the application for settings to take effect.</p>
                </div>
              }
              type="info"
              showIcon
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Settings;