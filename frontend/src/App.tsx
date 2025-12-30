import React, { useState, useRef, useEffect } from 'react';
import { 
  Navbar, Container, Row, Col, Card, Button, Alert, 
  ListGroup, Form, Spinner
} from 'react-bootstrap';
import axios from 'axios';
import BlueprintCanvas from './BlueprintCanvas';
import type { Node, Edge } from '@xyflow/react';

// 自定义 Hook，用于将状态与 sessionStorage 同步
function useSessionStorageState<T>(key: string, defaultValue: T): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [state, setState] = useState<T>(() => {
    try {
      const storedValue = sessionStorage.getItem(key);
      return storedValue !== null ? JSON.parse(storedValue) : defaultValue;
    } catch (error) {
      console.error(`Error reading sessionStorage key “${key}”:`, error);
      return defaultValue;
    }
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(state));
    } catch (error) {
      console.error(`Error setting sessionStorage key “${key}”:`, error);
    }
  }, [key, state]);

  return [state, setState];
}

// 自定义文件上传组件
const FileUpload = ({ onFileSelect, isUploading, accept, title }: any) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File | null | undefined) => {
    if (file && (accept === '*' || file.type.includes(accept.replace('.', '')) || file.name.endsWith(accept))) {
      onFileSelect(file);
    } else if (file) {
      alert(`文件类型无效。请上传一个 ${accept} 类型的文件。`);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const onDragOver = (e: React.DragEvent) => e.preventDefault();
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    handleFileSelect(e.dataTransfer.files[0]);
  };
  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files?.[0]);
  };

  return (
    <div
      className="text-center p-4 border-2 border-dashed rounded bg-light"
      style={{ borderStyle: 'dashed', borderWidth: '2px', cursor: 'pointer' }}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      {isUploading ? <Spinner animation="border" size="sm" /> : <p className="text-muted m-0">{title}</p>}
      <Form.Control type="file" accept={accept} ref={fileInputRef} onChange={onFileChange} style={{ display: 'none' }} />
    </div>
  );
};

const App: React.FC = () => {
  const [loadingTemplate, setLoadingTemplate] = useState(false);
  const [uploadingZip, setUploadingZip] = useState(false);
  
  const [tasks, setTasks] = useSessionStorageState<any[]>('tasks', []);
  const [fileName, setFileName] = useSessionStorageState<string>('fileName', '');
  const [dataSources, setDataSources] = useSessionStorageState<any[]>('dataSources', []);
  const [zipName, setZipName] = useSessionStorageState<string>('zipName', '');

  const [blueprint, setBlueprint] = useState<{nodes: Node[], edges: Edge[]} | null>(null);
  const [generatingBlueprint, setGeneratingBlueprint] = useState(false);
  const [errorInfo, setErrorInfo] = useState<string | null>(null);

  // YAML 生成功能的状态
  const [yamlRequest, setYamlRequest] = useState<string>("创建一个包含“总结”和“发送邮件”两个步骤的工作流");
  const [isGeneratingYaml, setIsGeneratingYaml] = useState<boolean>(false);
  const [generatedYaml, setGeneratedYaml] = useState<string>("");

  const handleGenerateYaml = async () => {
    setIsGeneratingYaml(true);
    setGeneratedYaml("");
    setErrorInfo(null);

    const filesContext = `可用的文件列表:\n${dataSources.map((f, i) => `- 文件 #${i}: ${f.name}`).join('\n')}`;
    const tasksContext = `需要完成的任务列表:\n${tasks.map((t, i) => `- 任务 #${i}: ${t.task_name}`).join('\n')}`;
    const context = `${filesContext}\n\n${tasksContext}`;

    try {
      const response = await axios.post("/api/yaml/generate", {
        user_request: yamlRequest,
        context: context,
      });
      if (response.data && response.data.yaml) {
        setGeneratedYaml(response.data.yaml);
      }
    } catch (error: any) {
      setErrorInfo(error.response?.data?.detail || "YAML 生成失败");
    } finally {
      setIsGeneratingYaml(false);
    }
  };

  const handleUploadTemplate = async (file: File) => {
    setErrorInfo(null);
    const formData = new FormData();
    formData.append('file', file);
    setLoadingTemplate(true);
    setFileName(file.name);
    try {
      const response = await axios.post('/api/templates/parse', formData);
      if (response.data && response.data.tasks) {
        setTasks(response.data.tasks);
      }
    } catch (error: any) {
      setErrorInfo('模板解析失败');
      setFileName('');
      setTasks([]);
    } finally {
      setLoadingTemplate(false);
    }
  };

  const handleUploadZip = async (file: File) => {
    setErrorInfo(null);
    const formData = new FormData();
    formData.append('file', file);
    setUploadingZip(true);
    setZipName(file.name);
    try {
      const response = await axios.post('/api/files/upload/datasource', formData);
      if (Array.isArray(response.data)) {
        setDataSources(response.data);
      }
    } catch (error: any) {
      setErrorInfo('资料包解析失败');
      setZipName('');
      setDataSources([]);
    } finally {
      setUploadingZip(false);
    }
  };

  const generateBlueprint = async () => {
    setErrorInfo(null);
    if (tasks.length === 0 || dataSources.length === 0) return;
    setGeneratingBlueprint(true);
    try {
      const response = await axios.post('/api/blueprints/generate', {
        tasks: tasks,
        data_sources: dataSources
      });
      if (response.data.nodes && response.data.nodes.length > 0) {
        console.log("AI Response Data:", JSON.stringify(response.data, null, 2));
        setBlueprint({ nodes: response.data.nodes, edges: response.data.edges });
      } else if (response.data.error) {
        setErrorInfo('蓝图规划失败: ' + response.data.error);
      }
    } catch (error: any) {
      setErrorInfo('请求失败');
    } finally {
      setGeneratingBlueprint(false);
    }
  };
  
  const resetAll = () => {
    setTasks([]);
    setFileName('');
    setDataSources([]);
    setZipName('');
    setBlueprint(null);
    setErrorInfo(null);
    sessionStorage.clear();
  }

  const renderDashboard = () => (
    <Container className="py-4">
      <Row className="g-4">
        <Col md={5}>
          <Card className="mb-4">
            <Card.Header as="h5">1. 上传报告模板</Card.Header>
            <Card.Body><FileUpload onFileSelect={handleUploadTemplate} isUploading={loadingTemplate} accept=".docx" title="点击或拖拽 .docx 文件" /></Card.Body>
            {fileName && <Card.Footer className="text-muted">{fileName}</Card.Footer>}
          </Card>

          <Card className="mb-4">
            <Card.Header as="h5">2. 上传分析资料</Card.Header>
            <Card.Body><FileUpload onFileSelect={handleUploadZip} isUploading={uploadingZip} accept=".zip" title="点击或拖拽 .zip 文件" /></Card.Body>
            {zipName && <Card.Footer className="text-muted">{zipName}</Card.Footer>}
          </Card>
          
          <div className="d-grid">
            <Button variant="primary" size="lg" onClick={generateBlueprint} disabled={generatingBlueprint || tasks.length === 0 || dataSources.length === 0}>
              {generatingBlueprint ? <Spinner as="span" animation="border" size="sm" /> : '3. 开始全自动蓝图规划'}
            </Button>
          </div>
        </Col>

        <Col md={7}>
          <Card className="mb-4">
            <Card.Header as="h5">任务大纲预览</Card.Header>
            <Card.Body style={{ minHeight: '200px' }}>
              {tasks.length > 0 ? (
                <ListGroup variant="flush">
                  {tasks.map((task, index) => (
                    <ListGroup.Item key={index}><strong>{index + 1}. {task.task_name}</strong><p className="text-muted mb-0">{task.description}</p></ListGroup.Item>
                  ))}
                </ListGroup>
              ) : <div className="text-center text-muted pt-5"><p>请先上传报告模板以预览任务大纲</p></div>}
            </Card.Body>
          </Card>

          <Card>
            <Card.Header as="h5">DeepAgent YAML 生成器</Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>高级需求描述</Form.Label>
                <Form.Control as="textarea" rows={2} value={yamlRequest} onChange={(e) => setYamlRequest(e.target.value)} />
              </Form.Group>
              <Button variant="dark" onClick={handleGenerateYaml} disabled={isGeneratingYaml} className="w-100">
                {isGeneratingYaml ? <Spinner size="sm" /> : "✨ 使用 DeepAgents 生成 YAML"}
              </Button>
              {generatedYaml && (
                <Form.Group className="mt-4">
                  <Form.Label>生成的 YAML</Form.Label>
                  <pre className="bg-light p-3 rounded" style={{maxHeight: '400px', overflowY: 'auto'}}>
                    <code>{generatedYaml}</code>
                  </pre>
                </Form.Group>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );

  const renderBlueprintState = () => (
    <Container fluid className="py-4">
      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0">执行蓝图可视化</h5>
          <Button variant="outline-secondary" onClick={resetAll}>全部重置</Button>
        </Card.Header>
        <Card.Body>
          <div style={{ height: '75vh', border: '1px solid #dee2e6', borderRadius: '.25rem' }}>
            <BlueprintCanvas aiJsonData={blueprint} />
          </div>
        </Card.Body>
      </Card>
    </Container>
  );

  return (
    <>
      <Navbar bg="dark" variant="dark" expand="lg" className="mb-4">
        <Container><Navbar.Brand href="#">ReportFlow Studio</Navbar.Brand></Container>
      </Navbar>
      
      {errorInfo && (
        <Container>
          <Alert variant="danger" onClose={() => setErrorInfo(null)} dismissible>
            <Alert.Heading>发生错误</Alert.Heading>
            <p>{errorInfo}</p>
          </Alert>
        </Container>
      )}

      {!blueprint ? renderDashboard() : renderBlueprintState()}
    </>
  );
};

export default App;