"use client";

import React, { useEffect, useState, useMemo } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  Handle, 
  Position, 
  MarkerType,
  Node,
  Edge
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NebulaAPI } from '@/lib/api';
import { Loader2 } from 'lucide-react';

// Custom Node for displaying document parts
const CustomNode = ({ data }: { data: any }) => {
  return (
    <div className="px-4 py-2 shadow-lg rounded-md bg-surface border-2 border-primary-500 min-w-[200px]">
      <Handle type="target" position={Position.Top} className="w-2 h-2 bg-primary-500" />
      <div className="font-bold text-sm text-white">{data.label}</div>
      {data.content && (
        <div className="text-xs text-gray-400 mt-1 max-w-[250px] truncate">
          {data.content}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-primary-500" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

// Recursive function to parse tree.json into nodes and edges
const parseTreeToGraph = (treeNode: any, parentId: string | null = null, depth = 0, index = 0, siblings = 1): { nodes: Node[], edges: Edge[] } => {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  
  const nodeId = treeNode.id || `node-${depth}-${index}`;
  
  // Calculate a basic layout position
  const x = (index - siblings / 2) * 300;
  const y = depth * 150;

  nodes.push({
    id: nodeId,
    type: 'custom',
    position: { x, y },
    data: { 
      label: treeNode.title || treeNode.type || 'Document Node',
      content: treeNode.content || null
    },
  });

  if (parentId) {
    edges.push({
      id: `e-${parentId}-${nodeId}`,
      source: parentId,
      target: nodeId,
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#8b5cf6', strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#8b5cf6',
      },
    });
  }

  if (treeNode.children && Array.isArray(treeNode.children)) {
    treeNode.children.forEach((child: any, i: number) => {
      const childResult = parseTreeToGraph(child, nodeId, depth + 1, i, treeNode.children.length);
      nodes.push(...childResult.nodes);
      edges.push(...childResult.edges);
    });
  }

  return { nodes, edges };
};

export default function DocumentGraph({ notebookId, documentId }: { notebookId: string, documentId: string }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTree = async () => {
      try {
        setLoading(true);
        const treeData = await NebulaAPI.getDocumentTree(notebookId, documentId);
        
        if (treeData) {
          // If it's a list (some pageindex implementations return lists of trees), wrap it in a root
          let root = treeData;
          if (Array.isArray(treeData)) {
            root = { id: 'root', title: 'Document Root', children: treeData };
          }
          const graph = parseTreeToGraph(root);
          setNodes(graph.nodes);
          setEdges(graph.edges);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load graph");
      } finally {
        setLoading(false);
      }
    };

    fetchTree();
  }, [notebookId, documentId]);

  if (loading) {
    return (
      <div className="w-full h-[600px] flex items-center justify-center bg-background">
        <Loader2 className="w-10 h-10 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-[600px] flex flex-col items-center justify-center bg-background text-red-400">
        <p>{error}</p>
        <p className="text-sm text-gray-500 mt-2">Note: The document may still be processing or failed to index.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-[600px] bg-background rounded-xl overflow-hidden border border-white/10">
      <ReactFlow 
        nodes={nodes} 
        edges={edges} 
        nodeTypes={nodeTypes}
        fitView
        className="bg-black/20"
      >
        <Background color="#ffffff" gap={20} size={1} className="opacity-10" />
        <Controls className="bg-surface border-white/10 fill-white" />
      </ReactFlow>
    </div>
  );
}
