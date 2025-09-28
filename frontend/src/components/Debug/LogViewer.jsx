import React, { useState, useRef, useEffect } from 'react';
import { Card, Button, Typography, Tag, Space, Input, Switch } from 'antd';
import { DownloadOutlined, ClearOutlined, SearchOutlined } from '@ant-design/icons';
import { useLogStore } from '../../store/logStore';

const { Text, Title } = Typography;

const LogViewer = () => {
  const { logs, clearLogs, exportLogs } = useLogStore();
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef(null);

  // Auto scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter(log => 
    log.message.toLowerCase().includes(filter.toLowerCase()) ||
    log.source.toLowerCase().includes(filter.toLowerCase()) ||
    log.level.toLowerCase().includes(filter.toLowerCase())
  );

  const getLevelColor = (level) => {
    const colors = {
      error: 'red',
      warn: 'orange',
      info: 'blue',
      debug: 'purple',
      success: 'green'
    };
    return colors[level] || 'default';
  };

  const getLevelIcon = (level) => {
    const icons = {
      error: '❌',
      warn: '⚠️',
      info: 'ℹ️',
      debug: '🐛',
      success: '✅'
    };
    return icons[level] || '📝';
  };

  return (
    <Card 
      title={
        <Space>
          <Title level={4} style={{ margin: 0 }}>Application Logs</Title>
          <Tag color="blue">{filteredLogs.length} entries</Tag>
        </Space>
      }
      extra={
        <Space>
          <Input
            placeholder="Filter logs..."
            prefix={<SearchOutlined />}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          <Switch
            checked={autoScroll}
            onChange={setAutoScroll}
            checkedChildren="Auto Scroll"
            unCheckedChildren="Manual"
          />
          <Button 
            type="primary" 
            icon={<DownloadOutlined />}
            onClick={exportLogs}
          >
            Export
          </Button>
          <Button 
            danger 
            icon={<ClearOutlined />}
            onClick={clearLogs}
          >
            Clear
          </Button>
        </Space>
      }
      style={{ height: '600px' }}
    >
      <div 
        ref={logContainerRef}
        style={{
          height: '500px',
          overflowY: 'auto',
          fontFamily: 'monospace',
          fontSize: '12px',
          backgroundColor: '#1f1f1f',
          color: '#fff',
          padding: '12px',
          borderRadius: '6px'
        }}
      >
        {filteredLogs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: '#666' }}>
            {filter ? 'No logs match your filter' : 'No logs available'}
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div 
              key={log.id}
              style={{ 
                marginBottom: '4px',
                padding: '2px 0',
                borderLeft: `3px solid ${getLevelColor(log.level) === 'red' ? '#ff4d4f' : 
                  getLevelColor(log.level) === 'orange' ? '#faad14' :
                  getLevelColor(log.level) === 'blue' ? '#1890ff' :
                  getLevelColor(log.level) === 'purple' ? '#722ed1' :
                  getLevelColor(log.level) === 'green' ? '#52c41a' : '#666'}`,
                paddingLeft: '8px'
              }}
            >
              <Text style={{ color: '#888' }}>{log.timestamp}</Text>
              <Text style={{ margin: '0 8px' }}>
                {getLevelIcon(log.level)}
              </Text>
              <Tag 
                color={getLevelColor(log.level)} 
                size="small" 
                style={{ margin: '0 8px 0 0' }}
              >
                {log.level.toUpperCase()}
              </Tag>
              <Tag size="small" style={{ margin: '0 8px 0 0' }}>
                {log.source}
              </Tag>
              <Text style={{ color: '#fff' }}>{log.message}</Text>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};

export default LogViewer;