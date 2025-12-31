import React, { memo, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import dagre from 'dagre';
import { Card } from 'react-bootstrap';
import '@xyflow/react/dist/style.css';

// --- 1. 自动布局函数 (The Layout Engine) ---
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 100, ranksep: 100 });

  const nodeWidth = 220;
  const nodeHeight = 80;

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
    return node;
  });

  return { nodes: layoutedNodes, edges };
};


// --- 2. 自定义节点组件 (Custom Rendering) ---
const FileNode = memo(({ data }: { data: any }) => (
  <Card bg="light" border="primary" style={{ width: 220 }}>
    <Card.Body className="p-2">
      <Card.Title as="div" className="fw-bold small mb-1">{data.label}</Card.Title>
      {data.pages && <Card.Text className="text-muted small">页码: {data.pages.join(', ')}</Card.Text>}
    </Card.Body>
    <Handle type="source" position={Position.Right} />
  </Card>
));

const TargetNode = memo(({ data }: { data: any }) => (
  <Card bg="success" text="white" style={{ width: 220 }}>
    <Card.Body className="p-2">
      <Card.Title as="div" className="fw-bold small mb-0">{data.label}</Card.Title>
    </Card.Body>
    <Handle type="target" position={Position.Left} />
  </Card>
));

// 映射节点类型到组件
const nodeTypes = {
  input: FileNode,  // 将 'input' 类型映射到 FileNode
  output: TargetNode, // 将 'output' 类型映射到 TargetNode
  // agent: AgentNode, // 如果 AI 返回 agent 类型，可以取消注释
};

// --- 3. 核心画布组件 ---
interface BlueprintCanvasProps {
  aiJsonData: { nodes: Node[]; edges: Edge[] } | null;
}

const BlueprintCanvas: React.FC<BlueprintCanvasProps> = ({ aiJsonData }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const showNoEdgesMessage = !aiJsonData || !aiJsonData.edges || aiJsonData.edges.length === 0;

  useEffect(() => {
    if (aiJsonData && aiJsonData.nodes) {
      if (showNoEdgesMessage) {
        setNodes([]);
        setEdges([]);
        return;
      }

      // 格式化 Edges，为每条边添加唯一 ID (如果后端没提供)
      const formattedEdges = aiJsonData.edges.map((edge, index) => ({
        ...edge,
        id: edge.id || `e-${edge.source}-${edge.target}-${index}`,
      }));

      // 运行布局算法
      const { nodes: layoutedNodes, edges: finalEdges } = getLayoutedElements(
        [...aiJsonData.nodes], // 使用副本以避免直接修改 prop
        formattedEdges
      );
      
      setNodes(layoutedNodes);
      setEdges(finalEdges);
    }
  }, [aiJsonData, setNodes, setEdges, showNoEdgesMessage]);

  if (showNoEdgesMessage) {
    return (
      <div className="d-flex justify-content-center align-items-center h-100 bg-light rounded text-muted">
        <p className="lead text-center p-4">
          布局失败：AI未能生成有效的节点连接关系 (Edges 数组为空)，请检查或优化您的提示词。
        </p>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default BlueprintCanvas;
