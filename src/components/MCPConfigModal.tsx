'use client';

import React, { useState } from 'react';
import { FaTimes, FaCopy, FaCheck } from 'react-icons/fa';

interface ProcessedProject {
  id: string;
  owner: string;
  repo: string;
  name: string;
  repo_type: string;
  submittedAt: number;
  language: string;
}

interface MCPConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProcessedProject;
}

export default function MCPConfigModal({ isOpen, onClose, project }: MCPConfigModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  // Generate the repository URL
  const repositoryUrl = `https://github.com/${project.owner}/${project.repo}`;
  
  // Generate MCP server name from repository name + "-doc"
  const mcpServerName = `${project.repo}-doc`;
  
  // Get the absolute path - try to determine the correct path automatically
  const getAbsolutePath = () => {
    // Try to detect common installation paths
    if (typeof window !== 'undefined') {
      // Client-side: we can't determine the actual path, show placeholder with guidance
      return process.env.NEXT_PUBLIC_AUTODOC_PATH || '<ABSOLUTE_PATH_TO_AUTODOC>';
    }
    // Fallback to environment variable or placeholder
    return process.env.NEXT_PUBLIC_AUTODOC_PATH || '<ABSOLUTE_PATH_TO_AUTODOC>';
  };
  
  const absolutePath = getAbsolutePath();
  // AutoDoc frontend runs on port 3000 by default (from README)
  const autodocServerUrl = process.env.NEXT_PUBLIC_AUTODOC_SERVER_URL || 'http://localhost:3000';

  const mcpConfig = {
    mcpServers: {
      [mcpServerName]: {
        command: "uv",
        args: [
          "run",
          "--with", "fastmcp>=2.8.0",
          "--with", "httpx>=0.28.0",
          "python",
          `${absolutePath}/mcp/mcp-server.py`
        ],
        env: {
          AUTODOC_SERVER_URL: autodocServerUrl,
          REPO_URL: repositoryUrl
        }
      }
    }
  };

  const configJson = JSON.stringify(mcpConfig, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(configJson);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = configJson;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg max-w-4xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[var(--border-color)]">
          <div>
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              MCP Configuration
            </h2>
            <p className="text-sm text-[var(--muted)] mt-1">
              Configuration for {project.name} • Server: <code className="bg-[var(--background)] px-1 rounded text-xs">{mcpServerName}</code>
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
          >
            <FaTimes className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Instructions */}
          <div className="p-6 border-b border-[var(--border-color)]">
            <h3 className="text-lg font-medium text-[var(--foreground)] mb-3">
              Setup Instructions
            </h3>
            <div className="space-y-3 text-sm text-[var(--muted)]">
              <p><strong>1. Copy the configuration below</strong> to your MCP client settings file:</p>
              <ul className="list-disc list-inside ml-4 space-y-1 text-xs">
                <li><strong>Claude Desktop:</strong> <code className="bg-[var(--background)] px-1 rounded">~/.claude/mcp.json</code> (macOS/Linux) or <code className="bg-[var(--background)] px-1 rounded">%APPDATA%\Claude\mcp.json</code> (Windows)</li>
                <li><strong>Cursor:</strong> Your MCP settings configuration</li>
              </ul>
              
              <p><strong>2. Replace the path placeholder</strong></p>
              <div className="ml-4 text-xs space-y-1">
                <p>Replace <code className="bg-[var(--background)] px-1 rounded">&lt;ABSOLUTE_PATH_TO_AUTODOC&gt;</code> with your AutoDoc installation path:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>Example:</strong> <code className="bg-[var(--background)] px-1 rounded">/home/user/projects/autodoc</code></li>
                  <li><strong>Example:</strong> <code className="bg-[var(--background)] px-1 rounded">C:\Users\YourName\projects\autodoc</code></li>
                </ul>
              </div>
                            
              <p><strong>3. Save and restart</strong> your MCP client</p>
              
              <div className="mt-3 p-2 bg-[var(--background)] rounded border text-xs">
                <p className="font-medium mb-1">💡 Pro Tip:</p>
                <p>The MCP server name <code className="bg-[var(--card-bg)] px-1 rounded">{mcpServerName}</code> is automatically generated from your repository name to avoid conflicts with other AutoDoc repositories.</p>
              </div>
            </div>
          </div>

          {/* Configuration */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)]">
              <h4 className="text-sm font-medium text-[var(--foreground)]">
                MCP Server Configuration
              </h4>
              <button
                onClick={handleCopy}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors ${
                  copied
                    ? 'bg-green-100 text-green-700 border border-green-200'
                    : 'bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary)]/90'
                }`}
              >
                {copied ? (
                  <>
                    <FaCheck className="h-3 w-3" />
                    Copied!
                  </>
                ) : (
                  <>
                    <FaCopy className="h-3 w-3" />
                    Copy to Clipboard
                  </>
                )}
              </button>
            </div>
            
            <div className="flex-1 overflow-auto p-4">
              <pre className="text-sm bg-[var(--background)] border border-[var(--border-color)] rounded p-4 overflow-auto">
                <code className="text-[var(--foreground)]">{configJson}</code>
              </pre>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[var(--border-color)] bg-[var(--background)]">
          <div className="flex justify-between items-center">
            <div className="text-sm text-[var(--muted)]">
              Repository: <span className="font-mono">{repositoryUrl}</span>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-md hover:bg-[var(--accent-primary)]/90 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 