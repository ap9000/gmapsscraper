import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Select,
  Button,
  Progress,
  Alert,
  Typography,
  Space,
  Divider,
  Row,
  Col,
  Table,
  Tag,
  message
} from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  ClearOutlined,
  ExportOutlined
} from '@ant-design/icons';
import { useAppStore } from '../../store/appStore';
import { searchAPI } from '../../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

const Search = () => {
  const [form] = Form.useForm();
  const [searching, setSearching] = useState(false);
  const {
    searchProgress,
    searchResults,
    setSearchResults,
    addToSearchHistory,
    setCurrentSearch
  } = useAppStore();

  const [results, setResults] = useState([]);
  const [exportLoading, setExportLoading] = useState(false);

  const handleSearch = async (values) => {
    try {
      setSearching(true);
      setResults([]);
      
      const searchData = {
        query: values.query,
        location: values.location || null,
        max_results: values.maxResults || 100,
        enrich: values.enrich !== false,
        export_format: values.exportFormat || null,
        filename: values.filename || null
      };

      setCurrentSearch(searchData);

      const response = await searchAPI.single(searchData);
      
      if (response.data.success) {
        message.success('Search started successfully!');
        
        // Add to search history
        addToSearchHistory({
          ...searchData,
          timestamp: new Date().toISOString(),
          jobId: response.data.job_id
        });
        
        // The WebSocket will handle progress updates
      } else {
        message.error(response.data.error || 'Search failed');
      }
    } catch (error) {
      console.error('Search error:', error);
      message.error('Failed to start search: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSearching(false);
    }
  };

  const handleClearForm = () => {
    form.resetFields();
    setResults([]);
  };

  const columns = [
    {
      title: 'Business Name',
      dataIndex: 'name',
      key: 'name',
      render: (name) => <Text strong>{name}</Text>
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email, record) => email ? (
        <Space direction="vertical" size="small">
          <Text copyable>{email}</Text>
          {record.confidence_score && (
            <Tag color={record.confidence_score > 0.7 ? 'green' : 'orange'}>
              {Math.round(record.confidence_score * 100)}% confidence
            </Tag>
          )}
        </Space>
      ) : <Text type="secondary">No email</Text>
    },
    {
      title: 'Phone',
      dataIndex: 'phone',
      key: 'phone',
      render: (phone) => phone ? <Text copyable>{phone}</Text> : <Text type="secondary">-</Text>
    },
    {
      title: 'Location',
      dataIndex: 'address',
      key: 'address',
      render: (address) => address ? (
        <Text style={{ maxWidth: 200 }} ellipsis={{ tooltip: true }}>
          {address}
        </Text>
      ) : <Text type="secondary">-</Text>
    },
    {
      title: 'Rating',
      dataIndex: 'rating',
      key: 'rating',
      render: (rating) => rating ? (
        <Space>
          <Text>{rating}</Text>
          <Text type="secondary">⭐</Text>
        </Space>
      ) : <Text type="secondary">-</Text>
    },
    {
      title: 'Website',
      dataIndex: 'website',
      key: 'website',
      render: (website) => website ? (
        <Button 
          type="link" 
          size="small" 
          href={website} 
          target="_blank"
          icon={<ExportOutlined />}
        >
          Visit
        </Button>
      ) : <Text type="secondary">-</Text>
    }
  ];

  const isSearching = searching || (searchProgress.jobId && searchProgress.status !== 'completed');

  return (
    <div style={{ padding: '0' }}>
      <Title level={2}>Single Search</Title>
      
      <Row gutter={[24, 24]}>
        {/* Search Form */}
        <Col xs={24} lg={8}>
          <Card title="Search Parameters" size="small">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSearch}
              initialValues={{
                maxResults: 100,
                enrich: true,
                exportFormat: null
              }}
            >
              <Form.Item
                name="query"
                label="Search Query"
                rules={[
                  { required: true, message: 'Please enter a search query' },
                  { min: 2, message: 'Query must be at least 2 characters' }
                ]}
              >
                <Input
                  placeholder="e.g., restaurants, law firms, dentists"
                  prefix={<SearchOutlined />}
                />
              </Form.Item>

              <Form.Item
                name="location"
                label="Location (Optional)"
                tooltip="Leave empty for global search. For pagination, use city format like 'New York, NY'"
              >
                <Input placeholder="e.g., New York, NY" />
              </Form.Item>

              <Form.Item
                name="maxResults"
                label="Maximum Results"
                rules={[
                  { type: 'number', min: 1, max: 200, message: 'Must be between 1 and 200' }
                ]}
              >
                <InputNumber
                  min={1}
                  max={200}
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item
                name="enrich"
                label="Email Enrichment"
                valuePropName="checked"
                tooltip="Find email addresses for discovered businesses"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                name="exportFormat"
                label="Export Format"
                tooltip="Automatically export results after completion"
              >
                <Select placeholder="No export" allowClear>
                  <Option value="csv">CSV</Option>
                  <Option value="json">JSON</Option>
                  <Option value="hubspot">HubSpot</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="filename"
                label="Custom Filename (Optional)"
                tooltip="Without extension"
              >
                <Input placeholder="e.g., my_leads" />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={isSearching}
                    icon={<SearchOutlined />}
                  >
                    {isSearching ? 'Searching...' : 'Start Search'}
                  </Button>
                  <Button
                    onClick={handleClearForm}
                    icon={<ClearOutlined />}
                  >
                    Clear
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        {/* Progress and Results */}
        <Col xs={24} lg={16}>
          {/* Search Progress */}
          {searchProgress.jobId && (
            <Card 
              title="Search Progress" 
              size="small" 
              style={{ marginBottom: '16px' }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>Job ID: {searchProgress.jobId}</Text>
                <Progress
                  percent={searchProgress.progress}
                  status={
                    searchProgress.status === 'failed' 
                      ? 'exception' 
                      : searchProgress.progress === 100 
                      ? 'success' 
                      : 'active'
                  }
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
                <Text type="secondary">
                  {searchProgress.details || `Status: ${searchProgress.status}`}
                </Text>
              </Space>
            </Card>
          )}

          {/* Results Table */}
          <Card 
            title="Search Results" 
            size="small"
            extra={
              results.length > 0 && (
                <Space>
                  <Text strong>{results.length} results</Text>
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    loading={exportLoading}
                  >
                    Export
                  </Button>
                </Space>
              )
            }
          >
            {isSearching && results.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Text type="secondary">
                  Search in progress... Results will appear here as they're found.
                </Text>
              </div>
            ) : (
              <Table
                dataSource={results}
                columns={columns}
                rowKey="id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) =>
                    `${range[0]}-${range[1]} of ${total} businesses`
                }}
                scroll={{ x: 800 }}
                size="small"
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Search;