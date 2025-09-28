import React, { useState } from 'react';
import {
  Card,
  Upload,
  Button,
  Switch,
  Select,
  Progress,
  Alert,
  Typography,
  Space,
  Row,
  Col,
  Table,
  message
} from 'antd';
import { InboxOutlined, UploadOutlined } from '@ant-design/icons';
import { useAppStore } from '../../store/appStore';
import { batchAPI } from '../../services/api';

const { Title, Text } = Typography;
const { Dragger } = Upload;
const { Option } = Select;

const Batch = () => {
  const [uploading, setUploading] = useState(false);
  const [enrich, setEnrich] = useState(true);
  const [exportFormat, setExportFormat] = useState(null);
  const [fileList, setFileList] = useState([]);
  const { batchJobs, addBatchJob } = useAppStore();

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.csv',
    fileList,
    beforeUpload: (file) => {
      const isCSV = file.type === 'text/csv' || file.name.endsWith('.csv');
      if (!isCSV) {
        message.error('You can only upload CSV files!');
        return false;
      }
      
      setFileList([file]);
      return false; // Prevent auto upload
    },
    onRemove: () => {
      setFileList([]);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('Please select a CSV file first');
      return;
    }

    try {
      setUploading(true);
      
      const formData = new FormData();
      formData.append('file', fileList[0]);
      formData.append('enrich', enrich);
      if (exportFormat) {
        formData.append('export_format', exportFormat);
      }

      const response = await batchAPI.upload(formData);
      
      if (response.data.success) {
        message.success(`Batch processing started! ${response.data.searches_count} searches queued.`);
        
        // Add to batch jobs list
        addBatchJob({
          id: response.data.batch_id,
          filename: fileList[0].name,
          searches_count: response.data.searches_count,
          status: 'processing',
          timestamp: new Date().toISOString(),
          enrich,
          export_format: exportFormat
        });
        
        // Clear form
        setFileList([]);
      } else {
        message.error(response.data.error || 'Batch upload failed');
      }
    } catch (error) {
      console.error('Batch upload error:', error);
      message.error('Failed to upload batch: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const jobColumns = [
    {
      title: 'Batch ID',
      dataIndex: 'id',
      key: 'id',
      render: (id) => <Text code>{id}</Text>
    },
    {
      title: 'Filename',
      dataIndex: 'filename',
      key: 'filename'
    },
    {
      title: 'Searches',
      dataIndex: 'searches_count',
      key: 'searches_count'
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'completed' ? 'green' : 
                     status === 'failed' ? 'red' : 'blue';
        return <Text style={{ color }}>{status}</Text>;
      }
    },
    {
      title: 'Created',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp) => new Date(timestamp).toLocaleString()
    }
  ];

  return (
    <div style={{ padding: '0' }}>
      <Title level={2}>Batch Processing</Title>
      
      <Row gutter={[24, 24]}>
        {/* Upload Section */}
        <Col xs={24} lg={12}>
          <Card title="Upload CSV File" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Alert
                message="CSV Format Required"
                description="Your CSV should have columns: query, location, max_results. See sample file for reference."
                type="info"
                showIcon
              />
              
              <Dragger {...uploadProps}>
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">
                  Click or drag CSV file to this area to upload
                </p>
                <p className="ant-upload-hint">
                  Support for single CSV file upload. Maximum 1000 searches per batch.
                </p>
              </Dragger>

              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong>Email Enrichment: </Text>
                  <Switch 
                    checked={enrich} 
                    onChange={setEnrich}
                    checkedChildren="ON"
                    unCheckedChildren="OFF"
                  />
                </div>
                
                <div>
                  <Text strong>Export Format: </Text>
                  <Select
                    style={{ width: 120 }}
                    placeholder="None"
                    allowClear
                    value={exportFormat}
                    onChange={setExportFormat}
                  >
                    <Option value="csv">CSV</Option>
                    <Option value="json">JSON</Option>
                    <Option value="hubspot">HubSpot</Option>
                  </Select>
                </div>
              </Space>

              <Button
                type="primary"
                icon={<UploadOutlined />}
                onClick={handleUpload}
                loading={uploading}
                disabled={fileList.length === 0}
                size="large"
              >
                {uploading ? 'Processing...' : 'Start Batch Processing'}
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Batch Jobs History */}
        <Col xs={24} lg={12}>
          <Card title="Batch Jobs" size="small">
            <Table
              dataSource={batchJobs}
              columns={jobColumns}
              rowKey="id"
              pagination={{
                pageSize: 5,
                showSizeChanger: false
              }}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* Sample CSV Format */}
      <Row style={{ marginTop: '24px' }}>
        <Col xs={24}>
          <Card title="Sample CSV Format" size="small">
            <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
{`query,location,max_results
"Italian restaurants","New York, NY",50
"coffee shops","San Francisco, CA",100
"law firms","Chicago, IL",75
"dentists","Los Angeles, CA",25`}
            </pre>
            <Text type="secondary">
              • query: Business type to search for<br/>
              • location: City and state (optional but recommended for pagination)<br/>
              • max_results: Number of results to fetch (1-200)
            </Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Batch;